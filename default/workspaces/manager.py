"""Explicit rootless SSH workspaces. No host credentials or engine socket mounts."""
import argparse
import base64
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import shlex
import subprocess
import sys
import tempfile
import time
import uuid

IMAGE = "localhost/omarchy-workspace:v1"
MEMORY = 4 * 1024**3
PIDS = 512
CPUS = 2
LABEL = "org.omarchy.workspace.id"
IMAGE_LABEL = "org.omarchy.workspace.version"
NAME = re.compile(r"[a-z0-9][a-z0-9-]{0,47}\Z")


def fail(message):
  raise RuntimeError(message)


def run(args, capture=False, check=True, **kwargs):
  return subprocess.run([str(a) for a in args], check=check, text=True,
             stdout=subprocess.PIPE if capture else None, **kwargs)


def output(args):
  return run(args, capture=True).stdout.strip()


def private_json(path, data):
  fd, temporary = tempfile.mkstemp(prefix=".state-", dir=path.parent)
  try:
    with os.fdopen(fd, "w") as stream:
      json.dump(data, stream, indent=2)
      stream.write("\n")
    os.replace(temporary, path)
  finally:
    if os.path.exists(temporary):
      os.unlink(temporary)


def state_root():
  root = Path(os.environ.get("XDG_DATA_HOME") or str(Path.home()/".local/share")) / "omarchy/workspaces"
  if not root.is_absolute() or any(c in str(root) for c in (":", "\n", "\r")):
    fail("XDG_DATA_HOME must be an absolute path without colons or line breaks")
  root.mkdir(parents=True, exist_ok=True, mode=0o700)
  if root.is_symlink() or root.stat().st_uid != os.getuid():
    fail("Workspace state must be a real directory owned by this user")
  root.chmod(0o700)
  return root.resolve()


def source_path(value, root, mount=False):
  source = Path(value).expanduser().resolve(strict=True)
  home = Path.home().resolve()
  forbidden = [Path("/"), home, root]
  if source in forbidden or source in root.parents or root in source.parents:
    fail("Select one project, not a host home, state directory, or filesystem root")
  sensitive = [(home/p).resolve() for p in (".ssh", ".pi", ".codex", ".config", ".aws", ".azure", ".gnupg", ".kube", ".local/share/keyrings", ".local/share/containers")]
  sensitive += [Path(p) for p in ("/etc", "/proc", "/sys", "/dev", "/run", "/var/lib/containers")]
  sensitive += [Path(os.environ[key]).expanduser().resolve() for key in ("CODEX_HOME", "PI_CODING_AGENT_DIR", "PI_AUTH_FILE", "XDG_CONFIG_HOME") if os.environ.get(key)]
  if any(source == p or p in source.parents or source in p.parents for p in sensitive):
    fail("Credential and system directories cannot be workspace sources")
  if not source.is_dir() or any(c in str(source) for c in (":", "\n", "\r")):
    fail("Source must be a directory with no colon or line breaks in its path")
  if mount:
    active = Path(os.environ["OMARCHY_PATH"]).resolve()
    if source == active or source in active.parents or active in source.parents:
      fail("Do not mount the active Omarchy source tree read-write; use the default clone")
  return source


def load(root, name, require_files=True):
  directory = root/name
  if directory.is_symlink() or not directory.is_dir():
    fail(f"Workspace not found: {name}")
  path = directory/"workspace.json"
  if path.is_symlink() or not path.is_file() or path.stat().st_uid != os.getuid() or path.stat().st_mode & 0o077:
    fail("Workspace metadata must be private and owned by this user")
  if require_files:
    for filename in ("identity", "identity.pub"):
      key = directory/filename
      if key.is_symlink() or not key.is_file() or key.stat().st_uid != os.getuid():
        fail("Workspace SSH identity must consist of user-owned regular files")
    if (directory/"identity").stat().st_mode & 0o077:
      fail("Workspace private key permissions are unsafe")
  connections = ("known_hosts", "ssh_config", "operation.lock") if require_files else ("operation.lock",)
  for filename in connections:
    connection = directory/filename
    if connection.is_symlink() or (connection.exists() and not connection.is_file()):
      fail("Workspace connection files must be regular files, not symlinks")
  data = json.loads(path.read_text())
  if data.get("version") != 1 or data.get("name") != name or not isinstance(data.get("id"), str) or not re.fullmatch(r"[a-f0-9]{32}", data["id"]):
    fail("Invalid workspace identity")
  if data.get("mode") not in ("clone", "mount"):
    fail("Invalid workspace mode")
  expected = directory/"repo" if data["mode"] == "clone" else Path(data["source"])
  if data.get("directory") != str(expected):
    fail("Workspace directory does not match its recorded mode")
  if require_files and (expected.is_symlink() or not expected.is_dir()):
    fail("Workspace directory changed or is unavailable")
  if require_files and data["mode"] == "mount":
    if source_path(data["source"], root, mount=True) != expected:
      fail("Workspace mount path changed")
  return directory, data


def identifiers(data):
  return "omarchy-workspace-"+data["id"], "omarchy-workspace-"+data["id"]+"-home"


def rootless():
  if os.getuid() == 0 or os.getgid() == 0:
    fail("Run workspace commands as an unprivileged user, not under sudo")
  info = json.loads(output(["podman", "info", "--format", "json"]))
  host = info.get("host", info.get("Host", {}))
  security = host.get("security", host.get("Security", {}))
  if security.get("rootless", security.get("Rootless")) is not True:
    fail("Rootless Podman is required")
  if str(host.get("cgroupVersion", host.get("CgroupVersion"))) != "v2":
    fail("Cgroup v2 is required for resource limits")


def inspect(container):
  return json.loads(output(["podman", "inspect", container]))[0]


def exists(kind, name):
  return run(["podman", kind, "exists", name], capture=True, check=False).returncode == 0


def owned(container, data):
  if container.get("Config", {}).get("Labels", {}).get(LABEL) != data["id"]:
    fail("Container identity does not match the workspace; refusing to reuse or stop it")


def audit(container, data, directory):
  owned(container, data)
  config = container.get("Config", {})
  host = container.get("HostConfig", {})
  _, volume = identifiers(data)
  if container.get("Image") != data.get("image_id"):
    fail("Container image drift")
  if config.get("User") != f"{os.getuid()}:{os.getgid()}":
    fail("Container must run as this user's unprivileged UID/GID")
  if host.get("Privileged") or not host.get("ReadonlyRootfs"):
    fail("Container root must be read-only and unprivileged")
  # Podman expands ALL into individual capabilities and reports keep-id as
  # private. Validate both the normalized settings and its creation arguments.
  created = config.get("CreateCommand", [])
  if "--env-host=false" not in created or "--http-proxy=false" not in created:
    fail("Automatic host environment and proxy forwarding must be disabled")
  if host.get("CapAdd") or not host.get("CapDrop") or "--cap-drop=ALL" not in created:
    fail("Container capabilities must all be dropped")
  if not any(s in ("no-new-privileges", "no-new-privileges=true") for s in host.get("SecurityOpt", [])):
    fail("Container must prohibit new privileges")
  if host.get("Devices") or host.get("PidMode", "private") not in ("", "private") or host.get("IpcMode", "private") not in ("", "private", "shareable") or host.get("UTSMode", "private") not in ("", "private") or host.get("CgroupMode") == "host":
    fail("Host devices and shared host/container namespaces are prohibited")
  if host.get("UsernsMode") not in ("private", "keep-id") or "--userns=keep-id" not in created:
    fail("Container must use keep-id user namespaces")
  if "--cgroups=enabled" not in created or "--cgroupns=private" not in created:
    fail("Resource accounting and private cgroup namespaces must be explicit")
  if host.get("Memory") != MEMORY or host.get("PidsLimit") != PIDS:
    fail("Container memory or process limit drift")
  cpu = host.get("NanoCpus", 0) / 1e9
  if not cpu and host.get("CpuPeriod"):
    cpu = host.get("CpuQuota", 0) / host["CpuPeriod"]
  if cpu != CPUS or host.get("MemorySwap") != MEMORY:
    fail("Container CPU or swap limit drift")
  if host.get("NetworkMode") != "pasta" or "--network=pasta:--no-map-gw" not in created:
    fail("Workspace must use its private pasta network with gateway mapping disabled")
  expected = {
    "/workspace": ("bind", str(Path(data["directory"]).resolve()), True),
    "/home/workspace": ("volume", volume, True),
    "/etc/omarchy-workspace/authorized_keys": ("bind", str(directory/"identity.pub"), False),
  }
  found = set()
  for mount in container.get("Mounts", []):
    target = mount.get("Destination")
    if target in ("/tmp", "/run") and mount.get("Type") == "tmpfs":
      continue
    if target not in expected or target in found:
      fail(f"Unexpected container mount: {target}")
    kind, source, writable = expected[target]
    actual = mount.get("Name") if kind == "volume" else mount.get("Source")
    if mount.get("Type") != kind or actual != source or mount.get("RW") is not writable:
      fail(f"Container mount drift: {target}")
    found.add(target)
  if found != set(expected):
    fail("Container is missing an expected mount")
  for target in ("/tmp", "/run"):
    if target not in host.get("Tmpfs", {}):
      fail(f"Ephemeral tmpfs missing: {target}")
  bindings = host.get("PortBindings", {})
  if set(bindings) != {"2222/tcp"} or not bindings["2222/tcp"]:
    fail("Only the workspace SSH port may be published")
  if any(item.get("HostIp") != "127.0.0.1" for item in bindings["2222/tcp"]):
    fail("SSH port must bind only to host loopback")
  environment = dict(e.split("=", 1) for e in config.get("Env", []) if "=" in e)
  if environment.get("HOME") != "/home/workspace" or environment.get("CODEX_HOME") != "/home/workspace/.codex":
    fail("Container home and Codex state must be workspace-local")
  if any(k in environment for k in ("SSH_AUTH_SOCK", "OPENAI_API_KEY", "CODEX_API_KEY", "DISPLAY", "WAYLAND_DISPLAY")):
    fail("Host credentials, SSH agents, and desktop sockets must not be injected")


def ssh_quote(path):
  value = str(path)
  if "\n" in value or "\r" in value:
    fail("SSH configuration paths must not contain line breaks")
  return '"'+value.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%")+'"'


def connect_files(directory, data, container):
  binding = output(["podman", "port", container, "2222/tcp"])
  match = re.fullmatch(r"127\.0\.0\.1:([0-9]+)", binding)
  if not match or not 0 < int(match[1]) < 65536:
    fail("Expected one loopback-only SSH endpoint")
  public = None
  for _ in range(40):
    result = run(["podman", "exec", container, "cat", "/home/workspace/.omarchy-sshd/host_ed25519.pub"], capture=True, check=False, stderr=subprocess.DEVNULL)
    if result.returncode == 0:
      public = result.stdout.strip().split()
      break
    time.sleep(.25)
  if not public or len(public) not in (2, 3) or public[0] != "ssh-ed25519":
    fail("Container SSH host key did not become ready")
  try:
    decoded = base64.b64decode(public[1], validate=True)
  except ValueError:
    fail("Invalid SSH host key")
  if len(decoded) != 51 or decoded[:19] != b"\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20":
    fail("Expected an Ed25519 host key")
  alias = "omarchy-workspace-"+data["id"]
  line = f"{alias} {public[0]} {public[1]}\n"
  known = directory/"known_hosts"
  if known.is_symlink():
    fail("SSH known-hosts file cannot be a symlink")
  if known.exists() and known.read_text() != line:
    fail("SSH host key changed. Refusing to overwrite the pinned key")
  known.write_text(line)
  known.chmod(0o600)
  configuration = f"""Host {alias}
  HostName 127.0.0.1
  Port {match[1]}
  User workspace
  IdentityFile {ssh_quote(directory/'identity')}
  IdentitiesOnly yes
  IdentityAgent none
  ForwardAgent no
  UserKnownHostsFile {ssh_quote(known)}
  GlobalKnownHostsFile /dev/null
  HostKeyAlias {alias}
  StrictHostKeyChecking yes
  HostKeyAlgorithms ssh-ed25519
  PasswordAuthentication no
  KbdInteractiveAuthentication no
  ConnectTimeout 10
  ServerAliveInterval 30
"""
  (directory/"ssh_config").write_text(configuration)
  (directory/"ssh_config").chmod(0o600)
  for _ in range(30):
    ready = run(["ssh", "-F", directory/"ssh_config", "-o", "BatchMode=yes", "-o", "ConnectTimeout=2", "-o", "ConnectionAttempts=1", alias, "true"], capture=True, check=False, stderr=subprocess.DEVNULL)
    if ready.returncode == 0:
      return alias
    time.sleep(.3)
  fail("Workspace SSH authentication did not become ready; inspect its Podman logs")


def start(directory, data):
  rootless()
  container, volume = identifiers(data)
  if exists("container", container):
    current = inspect(container)
    audit(current, data, directory)
    if not current.get("State", {}).get("Running"):
      run(["podman", "start", container])
  else:
    image = data.get("image_id") or IMAGE
    if not exists("image", image):
      if data.get("image_id"):
        fail("Pinned workspace image is missing. Recover that image, or preserve changes and create a new workspace; rebuilding the tag does not upgrade this workspace")
      fail("Workspace image is missing. Explicitly run: omarchy workspace build")
    image_info = json.loads(output(["podman", "image", "inspect", image]))[0]
    labels = image_info.get("Labels") or image_info.get("Config", {}).get("Labels", {})
    if labels.get(IMAGE_LABEL) != "1" or labels.get("org.omarchy.workspace.uid") != str(os.getuid()) or labels.get("org.omarchy.workspace.gid") != str(os.getgid()):
      fail("Workspace image version or user identity mismatch; rebuild the dedicated workspace image")
    data["image_id"] = image_info["Id"]
    private_json(directory/"workspace.json", data)
    if exists("volume", volume):
      labels = json.loads(output(["podman", "volume", "inspect", volume]))[0].get("Labels", {})
      if labels.get(LABEL) != data["id"]:
        fail("Workspace home volume identity mismatch")
    else:
      run(["podman", "volume", "create", "--label", f"{LABEL}={data['id']}", volume])
    uid, gid = os.getuid(), os.getgid()
    run(["podman", "run", "--detach", "--pull=never", "--name", container,
      "--label", f"{LABEL}={data['id']}", "--userns=keep-id", "--user", f"{uid}:{gid}",
      "--cap-drop=ALL", "--security-opt=no-new-privileges", "--read-only",
      "--cgroups=enabled", "--cgroupns=private", "--pid=private", "--ipc=private", "--uts=private",
      "--memory=4g", "--memory-swap=4g", "--pids-limit=512", "--cpus=2",
      "--network=pasta:--no-map-gw", "--http-proxy=false", "--env-host=false",
      "--publish", "127.0.0.1::2222",
      "--tmpfs", f"/tmp:rw,nosuid,nodev,size=1g,mode=1777",
      "--tmpfs", "/run:rw,nosuid,nodev,size=64m,mode=1777",
      "--volume", f"{data['directory']}:/workspace:rw,rprivate",
      "--volume", f"{volume}:/home/workspace:U,rw",
      "--volume", f"{directory/'identity.pub'}:/etc/omarchy-workspace/authorized_keys:ro,rprivate",
      "--env", "HOME=/home/workspace", "--env", "CODEX_HOME=/home/workspace/.codex",
      "--workdir=/workspace", data["image_id"]])
    try:
      audit(inspect(container), data, directory)
    except RuntimeError:
      run(["podman", "stop", "--time", "10", container], check=False)
      raise
  return connect_files(directory, data, container)


def editor_settings(directory, alias):
  for path in (directory/"vscode-data", directory/"vscode-data/User", directory/"vscode-extensions", directory/"vscode-shared", directory/"vscode-agent-plugins", directory/"vscode-agents-data", directory/"vscode-agents-extensions"):
    if path.is_symlink():
      fail("VS Code state directories cannot be symlinks")
  user = directory/"vscode-data/User"
  user.mkdir(parents=True, exist_ok=True)
  path = user/"settings.json"
  if path.is_symlink():
    fail("VS Code settings cannot be a symlink")
  settings = json.loads(path.read_text()) if path.exists() else {}
  critical = {
    "remote.SSH.configFile": str(directory/"ssh_config"),
    "remote.SSH.defaultExtensions": ["openai.chatgpt"],
    "remote.extensionKind": {"openai.chatgpt": ["workspace"]},
    "remote.SSH.remotePlatform": {alias: "linux"},
    "remote.SSH.serverInstallPath": {alias: "/home/workspace/.vscode-server"},
    "extensions.ignoreRecommendations": True,
  }
  for key, value in critical.items():
    if key in settings and settings[key] != value:
      fail(f"Isolation setting changed: {key}; review the workspace's private VS Code settings")
    settings[key] = value
  settings.setdefault("window.title", f"${{dirty}}{directory.name} — ${{rootName}} — ${{appName}}")
  private_json(path, settings)
  return ["code", "--user-data-dir", str(directory/"vscode-data"),
      "--extensions-dir", str(directory/"vscode-extensions"),
      "--shared-data-dir", str(directory/"vscode-shared"),
      "--agent-plugins-dir", str(directory/"vscode-agent-plugins"),
      "--agents-user-data-dir", str(directory/"vscode-agents-data"),
      "--agents-extensions-dir", str(directory/"vscode-agents-extensions"), "--sync", "off"]


def main():
  parser = argparse.ArgumentParser(prog="omarchy workspace", description=__doc__)
  sub = parser.add_subparsers(dest="operation", required=True)
  create = sub.add_parser("create")
  create.add_argument("name")
  create.add_argument("directory")
  create.add_argument("--mount", action="store_true", help="write directly to the supplied host directory instead of cloning")
  for operation in ("start", "code", "stop", "doctor"):
    sub.add_parser(operation).add_argument("name")
  sub.add_parser("list")
  sub.add_parser("build")
  args = parser.parse_args()
  os.umask(0o077)
  if os.getuid() == 0 or os.getgid() == 0:
    fail("Run as your unprivileged desktop user, not under sudo")
  if hasattr(args, "name") and not NAME.fullmatch(args.name):
    fail("Workspace names must be 1–48 lowercase letters, digits, or hyphens, beginning with a letter or digit")
  if args.operation == "build":
    rootless()
    context = Path(os.environ["OMARCHY_PATH"])/"containers/workspace"
    run(["podman", "build", "--http-proxy=false", "--tls-verify=true", "--pull=missing", "--tag", IMAGE,
      "--build-arg", f"WORKSPACE_UID={os.getuid()}", "--build-arg", f"WORKSPACE_GID={os.getgid()}", str(context)])
    return
  root = state_root()
  if args.operation == "list":
    for directory in sorted(root.iterdir()):
      if NAME.fullmatch(directory.name) and (directory/"workspace.json").is_file():
        _, data = load(root, directory.name, require_files=False)
        print(f"{data['name']}\t{data['mode']}\t{data['directory']}")
    return
  if args.operation == "create":
    source = source_path(args.directory, root, mount=args.mount)
    with (root/".create.lock").open("a") as lock:
      fcntl.flock(lock, fcntl.LOCK_EX)
      destination = root/args.name
      if destination.exists() or destination.is_symlink():
        fail("Workspace already exists; use another name for independent sessions")
      stage = Path(tempfile.mkdtemp(prefix=".create-", dir=root))
      try:
        mode = "mount" if args.mount else "clone"
        if args.mount:
          if (source/".git").is_file():
            fail("Direct mounts of linked Git worktrees are unsupported; use the default clone")
          print("WARNING: the container can modify every file in the supplied directory, including ignored files")
        else:
          env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_") and key != "SSH_AUTH_SOCK"}
          env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null", GIT_TERMINAL_PROMPT="0")
          top = run(["git", "-C", source, "rev-parse", "--show-toplevel"], capture=True, env=env).stdout.strip()
          if Path(top).resolve() != source:
            fail("Clone mode requires a Git repository root; use --mount explicitly for other directories")
          run(["git", "-c", "core.hooksPath=/dev/null", "clone", "--no-local", "--no-hardlinks", "--", source, stage/"repo"], env=env)
          run(["git", "-C", stage/"repo", "remote", "remove", "origin"], env=env)
          print("Created an independent Git clone. Uncommitted source changes were not copied; source remote removed")
        run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "omarchy-workspace", "-f", stage/"identity"])
        (stage/"identity.pub").chmod(0o644)
        data = dict(version=1, id=uuid.uuid4().hex, name=args.name, mode=mode, source=str(source),
              directory=str(source if args.mount else destination/"repo"))
        private_json(stage/"workspace.json", data)
        os.rename(stage, destination)
      finally:
        if stage.exists():
          shutil.rmtree(stage)
    print(f"Created {args.name}. No image was built or container started")
    return
  directory, data = load(root, args.name, require_files=args.operation != "stop")
  with (directory/"operation.lock").open("a") as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    container, _ = identifiers(data)
    if args.operation == "stop":
      rootless()
      if exists("container", container):
        owned(inspect(container), data)
        run(["podman", "stop", "--time", "10", container])
      print("Stopped. Repository, home volume, SSH identity, and VS Code state were retained")
    elif args.operation == "doctor":
      rootless()
      audit(inspect(container), data, directory)
      print("Runtime isolation checks passed. Verify Codex runs remotely with Developer: Show Running Extensions")
    elif args.operation == "code":
      if not os.environ.get("WAYLAND_DISPLAY") and not os.environ.get("DISPLAY"):
        fail("No graphical display in this shell. Run workspace code from a desktop terminal; use workspace start for SSH-only access")
      alias = "omarchy-workspace-"+data["id"]
      command = editor_settings(directory, alias)
      start(directory, data)
      run(command+["--install-extension", "ms-vscode-remote.remote-ssh"])
      run(command+["--new-window", "--folder-uri", f"vscode-remote://ssh-remote+{alias}/workspace"])
    else:
      alias = start(directory, data)
      print(f"Started {args.name}. SSH: {shlex.join(['ssh', '-F', str(directory/'ssh_config'), alias])}")


if __name__ == "__main__":
  try:
    main()
  except (RuntimeError, OSError, ValueError, TypeError, KeyError, subprocess.CalledProcessError) as error:
    print(f"omarchy workspace: {error}", file=sys.stderr)
    sys.exit(1)
