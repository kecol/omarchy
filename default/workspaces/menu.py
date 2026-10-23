"""Menu entry point for the existing container workspace backend."""
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

NAME = re.compile(r"[a-z0-9][a-z0-9-]{0,47}\Z")


class Cancelled(Exception):
  pass


def command(args, capture=False):
  return subprocess.run(args, check=True, text=True, stdout=subprocess.PIPE if capture else None)


def display(value):
  return "".join(c if c.isprintable() else " " for c in str(value))


def choose(title, choices):
  # The native picker returns label + subtext. Never interpret that as a command.
  rows = {label+"\t"+description: value for label, description, value in choices}
  result = subprocess.run(["omarchy-menu-select", title, *["\t"+row for row in rows], "--", "--width", "760"],
    text=True, stdout=subprocess.PIPE)
  if result.returncode == 1:
    raise Cancelled()
  if result.returncode != 0:
    raise RuntimeError("The workspace menu could not open")
  selected = result.stdout.removesuffix("\n")
  if selected not in rows:
    raise RuntimeError("The workspace selection changed or was invalid; reopen the menu")
  return rows[selected]


def confirm_terminal(name, source, directory, mode, state, create=False):
  # Native picker subtext is elided. Review full paths and warnings in the
  # presentation terminal instead, where long lines wrap rather than disappear.
  access = "Isolated clone; the source checkout is not mounted" if mode == "clone" else "LIVE HOST DIRECTORY: writes change host files, including ignored files"
  print("\nContainer workspace review", flush=True)
  print("Action: "+("Create workspace and open VS Code" if create else "Open VS Code; start the workspace if needed"), flush=True)
  for label, value in (("Name", name), ("Source", source), ("Workspace", directory), ("Access", access), ("State", state)):
    print(f"{label}: {display(value)}", flush=True)
  if mode == "clone":
    print("New clones include committed Git HEAD only, not uncommitted or untracked files. The source remote is removed.", flush=True)
  else:
    print("Review the directory for secrets before granting access. No copy isolates these files from the host.", flush=True)
  print("First VS Code setup downloads its server/extensions. No image is built or pulled automatically.\n", flush=True)
  action = "Create and Open" if create else "Open in VS Code"
  result = subprocess.run(["gum", "confirm", "--default=false", "--affirmative="+action, "--negative=Cancel", "Continue?"])
  if result.returncode in (1, 130):
    raise Cancelled()
  if result.returncode != 0:
    raise RuntimeError("Workspace confirmation failed; no workspace action was performed")


def launch(*args):
  worker = str(Path(os.environ["OMARCHY_PATH"])/"default/workspaces/menu.py")
  # The existing presentation wrapper accepts a command string. Quote every argument.
  command(["omarchy-launch-floating-terminal-with-presentation", shlex.join(["python3", worker, *args])])


def open_menu():
  if subprocess.run(["omarchy-cmd-present", "code"], stdout=subprocess.DEVNULL).returncode != 0:
    raise RuntimeError("VS Code is required. Install VS Code explicitly, then reopen this menu")
  listing = json.loads(command(["omarchy-workspace-list", "--json"], capture=True).stdout)
  records = listing["workspaces"]
  choices = [("Create from Project", "Create an independent container workspace", None)]
  for record in records:
    name = record["name"]
    if not NAME.fullmatch(name) or record["mode"] not in ("clone", "mount"):
      raise RuntimeError("Invalid workspace metadata; inspect it with omarchy workspace list")
    access = "Isolated clone" if record["mode"] == "clone" else "LIVE host directory"
    description = display(f"{access} | {record['state']} | {record['source']}")
    choices.append((name, description, record))
  record = choose("Open Container Workspace", choices)
  if record is not None:
    launch("--open", record["name"])
    return

  picked = subprocess.run(["omarchy-file-select", "--directory", "--title", "Select workspace source project"],
    text=True, stdout=subprocess.PIPE)
  if picked.returncode == 1:
    raise Cancelled()
  if picked.returncode != 0:
    raise RuntimeError("The project directory chooser could not open")
  source = picked.stdout.removesuffix("\n")
  if not source or any(not c.isprintable() for c in source):
    raise RuntimeError("Select one project directory without control characters")
  source = Path(source).expanduser().resolve(strict=True)
  if not source.is_dir():
    raise RuntimeError("The selected project directory is unavailable")
  result = subprocess.run(["omarchy-menu-input", "Workspace name: lowercase letters, digits, hyphens (1–48)", "--width", "760"],
    text=True, stdout=subprocess.PIPE)
  if result.returncode == 1:
    raise Cancelled()
  if result.returncode != 0:
    raise RuntimeError("The workspace name prompt could not open")
  name = result.stdout.removesuffix("\n")
  if not NAME.fullmatch(name):
    raise RuntimeError("Use 1–48 lowercase letters, digits, or hyphens, beginning with a letter or digit")
  if any(record["name"] == name for record in records):
    raise RuntimeError("That workspace already exists. Select it from the menu, or choose another name")
  mode = choose("Workspace file access", [
    ("Isolated Git Clone", "Committed HEAD only; uncommitted/untracked files excluded; source remote removed", "clone"),
    ("Live Host Directory", "WARNING: immediate host writes, including ignored files; review for secrets first", "mount"),
  ])
  launch("--create", name, str(source), mode)


def worker(args):
  if len(args) == 2 and args[0] == "--open" and NAME.fullmatch(args[1]):
    records = json.loads(command(["omarchy-workspace-list", "--json"], capture=True).stdout)["workspaces"]
    record = next((r for r in records if r["name"] == args[1]), None)
    if record is None or record["mode"] not in ("clone", "mount"):
      raise RuntimeError("Workspace is unavailable; reopen the menu")
    confirm_terminal(record["name"], record["source"], record["directory"], record["mode"], record["state"])
    command(["omarchy-workspace-code", args[1]])
  elif len(args) == 4 and args[0] == "--create" and NAME.fullmatch(args[1]) and args[3] in ("clone", "mount"):
    confirm_terminal(args[1], args[2], "New independent clone" if args[3] == "clone" else args[2], args[3], "Not created", create=True)
    command(["omarchy-workspace-create", args[1], args[2], *(["--mount"] if args[3] == "mount" else [])])
    print("Workspace created. If the editor cannot open, select this workspace from the menu to retry.", flush=True)
    command(["omarchy-workspace-code", args[1]])
  else:
    raise RuntimeError("Invalid workspace launcher arguments")


def main():
  if sys.argv[1:] == ["--help"]:
    print("Usage: omarchy menu workspace\nSelect or create a container workspace and open its isolated VS Code window.")
  elif sys.argv[1:]:
    worker(sys.argv[1:])
  else:
    open_menu()


if __name__ == "__main__":
  try:
    main()
  except Cancelled:
    # The presentation wrapper treats 130 as a dismissed dialog, not a failure.
    sys.exit(130 if sys.argv[1:] else 0)
  except (RuntimeError, OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as error:
    print(f"Container workspace: {error}", file=sys.stderr)
    if not sys.argv[1:]:
      try:
        choose("Container workspace could not open", [("Close", display(error), None)])
      except (Cancelled, RuntimeError, OSError):
        pass
    sys.exit(1)
