"""Real Pi save/quit/relaunch regression; synthetic provider, no network calls."""
import fcntl
import json
import os
from pathlib import Path
import pty
import re
import select
import struct
import subprocess
import sys
import tempfile
import termios
import time

root, pi = Path(sys.argv[1]), sys.argv[2]
output = Path(sys.argv[3]) if len(sys.argv) > 3 else None
if output:
  output.mkdir(parents=True, exist_ok=True)


def text(data):
  result = data.decode(errors="replace")
  result = re.sub(r"\x1b\][^\x07]*(?:\x07|\x1b\\)", "", result)
  return re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", result)


with tempfile.TemporaryDirectory(prefix="model-default-relaunch-") as temp:
  base = Path(temp)
  home, agent = base/"home", base/"agent"
  home.mkdir()
  agent.mkdir()
  settings = agent/"settings.json"
  settings.write_text(json.dumps({"defaultProvider": "recovery-fixture", "defaultModel": "retired-model",
    "enableAnalytics": False, "enableInstallTelemetry": False, "cacheWarming": "off",
    "retry": {"enabled": False}, "regressionSentinel": {"preserve": True}}))
  env = {"HOME": str(home), "PATH": "/usr/bin:/bin", "TERM": "xterm-256color",
    "PI_CODING_AGENT_DIR": str(agent), "MODEL_RECOVERY_CALLS": str(base/"calls")}
  args = [pi, "--no-session", "--offline", "--no-extensions", "--no-tools", "--no-mcp",
    "--no-context-files", "--no-skills", "--no-prompt-templates", "--no-themes",
    "--extension", str(root/"test/shell.d/fixtures/model-recovery-provider.ts"),
    "--extension", str(root/"default/agents/pi/model-recovery.ts")]
  for launch in (1, 2):
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 32, 100, 0, 0))
    def setup():
      os.setsid()
      fcntl.ioctl(0, termios.TIOCSCTTY, 0)
    child = subprocess.Popen(args, cwd=base, env=env, stdin=slave, stdout=slave, stderr=slave, preexec_fn=setup)
    os.close(slave)
    data = bytearray()
    phase, start = 0, 0
    deadline = time.monotonic()+25
    try:
      while time.monotonic() < deadline:
        if select.select([master], [], [], .1)[0]:
          try:
            chunk = os.read(master, 65536)
          except OSError:
            break
          data.extend(chunk)
          if b"\x1b[6n" in chunk:
            os.write(master, b"\x1b[1;1R")
        current = text(data[start:])
        if launch == 1:
          if phase == 0 and "Choose and save a new default" in current:
            os.write(master, b"\x1b[B\r")
            phase, start = 1, len(data)
          elif phase == 1 and "Press Enter to open Pi's model picker" in current:
            os.write(master, b"\r")
            phase, start = 2, len(data)
          elif phase == 2 and "to set as default" in current and "available-model" in current:
            os.write(master, b"\r")  # Enter must honor the Save default intent.
            phase, start = 3, len(data)
          elif phase == 3 and ("Saved default " in current or "Model:" in current):
            time.sleep(.3)
            os.write(master, b"\x04")
            phase = 4
        elif phase == 0 and "[Extensions]" in current and "available-model" in current:
          assert "Choose and save a new default" not in text(data), "fresh launch repeated recovery"
          time.sleep(.2)
          os.write(master, b"\x04")
          phase = 4
        if child.poll() is not None:
          break
      assert phase == 4, (launch, phase, text(data)[-2500:])
      child.wait(timeout=5)
      assert child.returncode == 0, child.returncode
      value = json.loads(settings.read_text())
      assert value["defaultProvider"] == "recovery-fixture" and value["defaultModel"] == "available-model", value
      assert value["regressionSentinel"] == {"preserve": True}
      assert not (base/"calls").exists(), "model provider must never run"
      print(f"ok - Pi launch {launch}: saved default survives exit and no provider request occurs")
    finally:
      if child.poll() is None:
        child.kill()
        child.wait()
      os.close(master)
      if output:
        (output/f"launch-{launch}.ansi").write_bytes(data)
        (output/f"launch-{launch}.txt").write_text(text(data))
