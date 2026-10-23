#!/usr/bin/python3
"""Preview only non-secret model defaults; never start a container or read auth."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import stat


def saved_default(root):
  descriptors = []
  try:
    descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    descriptors.append(descriptor)
    for name in (".pi", "agent"):
      descriptor = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
      descriptors.append(descriptor)
    descriptor = os.open("settings.json", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptor)
    descriptors.append(descriptor)
    if not stat.S_ISREG(os.fstat(descriptor).st_mode):
      return "Unavailable (Pi will check at startup)"
    raw = os.read(descriptor, 65537)
    if len(raw) > 65536:
      return "Unavailable (Pi will check at startup)"
    settings = json.loads(raw)
    provider, model = settings.get("defaultProvider"), settings.get("defaultModel")
    if not isinstance(provider, str) or not isinstance(model, str) or not provider or not model:
      return "Automatic (no saved container default)"
    # Terminal metadata is untrusted text, not an escape sequence or a command.
    text = json.dumps(f"{provider}/{model}", ensure_ascii=True)
    return text[:120] + ("..." if len(text) > 120 else "")
  except FileNotFoundError:
    return "Automatic (no saved container default)"
  except (OSError, ValueError, AttributeError, UnicodeError):
    return "Unavailable (Pi will check at startup)"
  finally:
    for descriptor in reversed(descriptors):
      os.close(descriptor)


def main():
  if len(sys.argv) != 2 or not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", sys.argv[1]):
    raise SystemExit(1)
  try:
    result = subprocess.run(["podman", "volume", "inspect", f"omarchy-agent-{sys.argv[1]}-home", "--format", "{{.Mountpoint}}"], capture_output=True, text=True, timeout=5)
  except (OSError, subprocess.TimeoutExpired):
    print("Unavailable (Pi will check at startup)")
    return
  if result.returncode or not result.stdout.strip():
    print("Automatic (no saved container default)")
  else:
    print(saved_default(Path(result.stdout.strip())))


if __name__ == "__main__":
  main()
