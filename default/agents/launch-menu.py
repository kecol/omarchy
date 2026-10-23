"""Interactive project/agent selection; all execution remains in existing backends."""
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
import os
from pathlib import Path
import shlex
import stat
import subprocess
import sys
import tempfile

ROOT = Path(os.environ["OMARCHY_PATH"])


def module(name, path):
  spec = importlib.util.spec_from_file_location(name, path)
  result = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(result)
  return result


ui = module("workspace_menu_ui", ROOT/"default/workspaces/menu.py")
workspaces = module("workspace_paths", ROOT/"default/workspaces/manager.py")


def execute(args, capture=False, **kwargs):
  return subprocess.run(args, check=True, text=True, stdout=subprocess.PIPE if capture else None, **kwargs)


def value(args):
  return execute(args, capture=True).stdout.removesuffix("\n")


def recent_file():
  base = Path(os.environ.get("XDG_STATE_HOME") or str(Path.home()/".local/state"))
  if not base.is_absolute():
    raise RuntimeError("XDG_STATE_HOME must be an absolute path")
  return base/"omarchy/agent-menu/recent-projects.json"


def recent_projects():
  path = recent_file()
  if path.parent.is_symlink():
    raise RuntimeError("Agent menu state must not be a symlink")
  if not path.exists() and not path.is_symlink():
    return []
  fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
  with os.fdopen(fd) as stream:
    info = os.fstat(stream.fileno())
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
      raise RuntimeError("Recent project state must be a private, user-owned regular file")
    text = stream.read(65537)
  if len(text) > 65536:
    raise RuntimeError("Recent project state is too large")
  paths = json.loads(text)
  if not isinstance(paths, list) or len(paths) > 10 or any(not isinstance(p, str) or not Path(p).is_absolute() or not p.isprintable() for p in paths):
    raise RuntimeError("Invalid recent project state")
  return [p for p in paths if Path(p).is_dir()]


def remember(source):
  path = recent_file()
  previous = recent_projects()
  path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
  if path.parent.is_symlink() or path.parent.stat().st_uid != os.getuid() or path.parent.stat().st_mode & 0o077:
    raise RuntimeError("Agent menu state directory must be private and owned by this user")
  records = [str(source), *[p for p in previous if p != str(source)]][:10]
  fd, temporary = tempfile.mkstemp(prefix=".recent-", dir=path.parent)
  try:
    with os.fdopen(fd, "w") as stream:
      json.dump(records, stream)
      stream.write("\n")
    os.replace(temporary, path)
  finally:
    if os.path.exists(temporary):
      os.unlink(temporary)


def checked_source(raw, mode, access):
  if os.getuid() == 0:
    raise RuntimeError("Run the agent menu as your unprivileged desktop user, not under sudo")
  if not raw or not str(raw).isprintable():
    raise RuntimeError("Select one project directory without control characters")
  if mode not in ("host", "container") or access not in ("host", "clone", "mount") or (mode == "host") != (access == "host"):
    raise RuntimeError("Invalid execution target or file access")
  source = workspaces.source_path(raw, workspaces.state_root(create=False), mount=access == "mount")
  menu_state = recent_file().parent.resolve()
  control_state = menu_state.parent/"agents"
  if any(source == p or p in source.parents or source in p.parents for p in (menu_state, control_state)):
    raise RuntimeError("Agent state directories cannot be project sources")
  return source


def workspace_project(name):
  if not workspaces.NAME.fullmatch(name):
    raise RuntimeError("Invalid workspace name")
  records = json.loads(value(["omarchy-workspace-list", "--json"]))["workspaces"]
  record = next((r for r in records if r["name"] == name), None)
  if record is None or record["mode"] not in ("clone", "mount"):
    raise RuntimeError("Workspace project is unavailable")
  directory = Path(record["directory"])
  if not str(directory).isprintable() or directory.is_symlink() or not directory.is_dir():
    raise RuntimeError("Workspace project directory is unavailable or unsafe")
  if record["mode"] == "mount":
    checked_source(record["source"], "container", "mount")
  return record


def agent_choices():
  # Use the existing default-agent menu as the catalog, not another agent list.
  script = '''
const fs = require("fs"), path = require("path");
const root = process.env.OMARCHY_PATH;
const model = require(path.join(root,"shell/plugins/menu/MenuModel.js"));
const entries = model.parseMenuJsonc(fs.readFileSync(path.join(root,"default/omarchy/omarchy-menu.jsonc"),"utf8"));
console.log(JSON.stringify(entries.filter(e => /^setup\\.default\\.agent\\.[a-z0-9-]+$/.test(e.id)).map(e => ({name:e.id.split(".").pop(),label:e.label}))));
'''
  records = json.loads(value(["node", "-e", script]))
  default = value(["omarchy-default-agent"])
  def available(record):
    return {**record, "host": ready(record["name"], "host"), "container": ready(record["name"], "container")}
  with ThreadPoolExecutor(max_workers=4) as pool:
    records = list(pool.map(available, records))
  return sorted(records, key=lambda record: record["name"] != default), default


def ready(agent, mode):
  try:
    return subprocess.run([str(ROOT/"bin/omarchy-agent"), "--check", "--agent", agent, "--"+mode],
      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=8).returncode == 0
  except subprocess.TimeoutExpired:
    return False


def input_value(prompt):
  result = subprocess.run(["omarchy-menu-input", prompt, "--width", "760"], text=True, stdout=subprocess.PIPE)
  if result.returncode == 1:
    raise ui.Cancelled()
  if result.returncode != 0:
    raise RuntimeError("The agent input prompt could not open")
  return result.stdout.removesuffix("\n")


def launch(*args):
  worker = ROOT/"default/agents/launch-menu.py"
  execute(["omarchy-launch-floating-terminal-with-presentation", shlex.join(["python3", "-B", str(worker), *args])])


def open_menu():
  choices = [("Browse Project", "Select a local project directory", None),
    ("Workspace Files", "Reuse a named workspace's project files; no editor/container is started", "@workspace")]
  choices += [(Path(p).name, p, p) for p in recent_projects()]
  selected = ui.choose("Start Agent: project", choices)
  if selected is None:
    result = subprocess.run(["omarchy-file-select", "--directory", "--title", "Select agent project"], text=True, stdout=subprocess.PIPE)
    if result.returncode == 1:
      raise ui.Cancelled()
    if result.returncode != 0:
      raise RuntimeError("The project directory chooser could not open")
    selected = result.stdout.removesuffix("\n")
  workspace_name = ""
  if selected == "@workspace":
    projects = json.loads(value(["omarchy-workspace-list", "--json"]))["workspaces"]
    if not projects:
      raise RuntimeError("No workspaces exist. Browse a source project and create an isolated clone instead")
    workspace_name = ui.choose("Workspace project files", [(r["name"], ui.display(f"{r['mode']} | {r['directory']}"), r["name"]) for r in projects])
    record = workspace_project(workspace_name)
    source = Path(record["directory"])
  else:
    source = checked_source(selected, "host", "host")
  records, default = agent_choices()
  choices = []
  for record in records:
    description = "; ".join(["Host installed" if record["host"] else "Host unavailable", "Container configured" if record["container"] else "No usable container definition"])
    choices.append((record["label"]+(" (default)" if record["name"] == default else ""), description, record))
  if not choices:
    raise RuntimeError("No agents are declared in the default-agent catalog")
  record = ui.choose("Agent for this launch", choices)
  default_mode = value(["omarchy-agent-mode"])
  if default_mode not in ("host", "container"):
    raise RuntimeError("The saved execution default is invalid")
  modes = [("Container", "Project mount only; persistent home shared by this agent's projects", "container"),
    ("Host", "WARNING: runs as your desktop user; the project directory is NOT confinement", "host")]
  modes.sort(key=lambda option: option[2] != default_mode)
  mode = ui.choose("Execution for this launch (default: "+default_mode+")", modes)
  if not record[mode]:
    raise RuntimeError("This agent is unavailable in "+mode+" mode. Install/configure it explicitly or choose another agent; no fallback was started")
  access, name = ("workspace", workspace_name) if workspace_name else ("host", "")
  if mode == "container" and not workspace_name:
    access = ui.choose("Container project access", [
      ("Isolated Git Clone", "New named copy of committed HEAD; source checkout is not mounted", "clone"),
      ("Live Host Directory", "WARNING: immediate host writes, including ignored files; review for secrets", "mount"),
    ])
    if access == "clone":
      name = input_value("New clone workspace name (lowercase letters, digits, hyphens)")
      if not workspaces.NAME.fullmatch(name):
        raise RuntimeError("Use 1–48 lowercase letters, digits, or hyphens, beginning with a letter or digit")
  if workspace_name:
    raw = "workspace:"+workspace_name
  else:
    source = checked_source(str(source), mode, access)
    raw = str(source)
  launch("--start", record["name"], mode, raw, access, name)


def worker(args):
  if len(args) != 6 or args[0] != "--start":
    raise RuntimeError("Invalid agent launcher arguments")
  _, agent, mode, raw, access, name = args
  project = None
  if access == "workspace":
    if mode not in ("host", "container") or raw != "workspace:"+name:
      raise RuntimeError("Invalid workspace project selection")
    project = workspace_project(name)
    source = Path(project["directory"])
  else:
    source = checked_source(raw, mode, access)
  if access == "clone" and not workspaces.NAME.fullmatch(name):
    raise RuntimeError("Invalid clone workspace name")
  if not ready(agent, mode):
    raise RuntimeError("The selected agent/runtime is unavailable. No project was prepared and no agent started")
  if access == "clone":
    records = json.loads(value(["omarchy-workspace-list", "--json"]))["workspaces"]
    if any(r["name"] == name for r in records):
      raise RuntimeError("That workspace name already exists; choose another name for a new independent clone")
  print("\nStart agent review", flush=True)
  for label, text in (("Agent", agent), ("Execution", mode), ("Source", source), ("Project access", access)):
    print(f"{label}: {ui.display(text)}", flush=True)
  if project is not None:
    print(f"Workspace project: {name}. These are the SAME files its editor uses, not another copy. Editor and harness homes/lifecycles remain separate.", flush=True)
    print("Original source: "+ui.display(project["source"]), flush=True)
    if project["mode"] == "mount":
      print("WARNING: this workspace uses a LIVE HOST DIRECTORY; writes immediately change host files, including ignored files.", flush=True)
    elif mode == "container":
      print("This is an isolated project clone; its original source checkout is not mounted.", flush=True)
  if mode == "host":
    print("WARNING: Host execution has your desktop user's permissions. The project is a working directory, not a sandbox. The existing launcher's approval options still apply.", flush=True)
  elif access == "clone":
    print(f"New clone workspace: {name}. Committed HEAD only; uncommitted/untracked files excluded; source remote removed. No editor container or VS Code window is started.", flush=True)
  elif project is None:
    print("WARNING: the container can immediately modify host files in this directory, including ignored files. No private copy protects them.", flush=True)
  if mode == "container":
    print("The agent harness is separate from the editor workspace container. Its persistent home is shared across this agent's interactive projects; host auth/home and engine sockets are not mounted.", flush=True)
    print("The existing image selector follows. Updates remain explicit. An approved clone is retained if image selection is cancelled or launch fails.", flush=True)
  print("Saved agent and execution defaults will not change.\n", flush=True)
  result = subprocess.run(["gum", "confirm", "--default=false", "--affirmative=Start Agent", "--negative=Cancel", "Continue?"])
  if result.returncode in (1, 130):
    raise ui.Cancelled()
  if result.returncode != 0:
    raise RuntimeError("Confirmation failed; no agent was started")
  directory = source
  if access == "clone":
    execute(["omarchy-workspace-create", name, str(source)])
    records = json.loads(value(["omarchy-workspace-list", "--json"]))["workspaces"]
    record = next((r for r in records if r["name"] == name and r["mode"] == "clone" and r["source"] == str(source)), None)
    if record is None or Path(record["directory"]).is_symlink() or not Path(record["directory"]).is_dir():
      raise RuntimeError("The prepared clone is unavailable; it was retained for inspection")
    directory = Path(record["directory"])
    print(f"Prepared project: {directory}. Retained under workspace name {name} even if launch is cancelled or fails.", flush=True)
  try:
    if project is None:
      remember(source)
  except (OSError, ValueError, RuntimeError) as error:
    print(f"Could not remember the project: {error}", file=sys.stderr)
  execute(["omarchy-agent", "--inline", "--agent", agent, "--directory", str(directory), "--"+mode, "--installed-only"])


def main():
  if sys.argv[1:] == ["--help"]:
    print("Usage: omarchy menu agent\nChoose a project, agent, execution target and access for one launch.")
  elif sys.argv[1:]:
    worker(sys.argv[1:])
  else:
    open_menu()


if __name__ == "__main__":
  try:
    main()
  except ui.Cancelled:
    sys.exit(130 if sys.argv[1:] else 0)
  except (RuntimeError, OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as error:
    print(f"Start agent: {error}", file=sys.stderr)
    if not sys.argv[1:]:
      try:
        ui.choose("Agent could not start", [("Close", ui.display(error), None)])
      except (ui.Cancelled, RuntimeError, OSError):
        pass
    sys.exit(1)
