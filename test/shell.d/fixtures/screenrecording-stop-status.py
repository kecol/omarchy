"""Real stop-command status/cleanup with inert helpers; no recorder or signals."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(sys.argv[1]).resolve()


def check(condition, message):
    if not condition:
        raise AssertionError(message)


with tempfile.TemporaryDirectory(prefix="screenrecording-stop-status-") as directory:
    base = Path(directory)
    bindir = base / "bin"
    bindir.mkdir()
    stubs = {
        "omarchy-capture-screenrecording-process": r'''#!/bin/bash
printf '%s\n' "$*" >> "$TEST_CASE/signals"
[[ ${1:-} == "--pid" && ${2:-} == "424242" ]] || exit 2
if [[ ${3:-} == "--signal" ]]; then
  case $4 in
    INT)
      if [[ $TEST_MODE == graceful || $TEST_MODE == raced-exit || $TEST_MODE == cleanup-failure ]]; then
        rm -f "$TEST_CASE/active"
      fi
      [[ $TEST_MODE != raced-exit ]]
      ;;
    KILL)
      [[ $TEST_MODE != kill-failure ]] || exit 1
      rm -f "$TEST_CASE/active"
      ;;
    *) exit 2 ;;
  esac
else
  [[ -e $TEST_CASE/active ]]
fi
''',
        "omarchy-notification-send": r'''#!/bin/bash
printf '%s\n' "$@" >> "$TEST_CASE/notifications"
[[ $TEST_MODE != notification-failure ]]
''',
        "omarchy-i18n": '#!/bin/bash\nprintf "%s\\n" "$1"\n',
        "omarchy-shell": "#!/bin/bash\nexit 0\n",
        "pkill": "#!/bin/bash\nexit 0\n",
        "sleep": "#!/bin/bash\nexit 0\n",
        "pactl": '#!/bin/bash\nprintf "%s\\n" "$*" >> "$TEST_CASE/audio"\n',
        "ffprobe": '#!/bin/bash\n[[ $* == *format=duration* ]] && printf "1.0\\n"\nexit 0\n',
        "ffmpeg": r'''#!/bin/bash
for arg in "$@"; do
  case $arg in *-processed.mp4|*screenrecord-preview-*.png) : > "$arg" ;; esac
done
''',
        "rm": r'''#!/bin/bash
if [[ $TEST_MODE == cleanup-failure && $* == *omarchy-screenrecord-pid* ]]; then
  exit 1
fi
exec /usr/bin/rm "$@"
''',
    }
    for name, text in stubs.items():
        file = bindir / name
        file.write_text(text)
        file.chmod(0o700)

    for mode, toggle in (("graceful", False), ("forced", False),
                         ("forced", True), ("kill-failure", False),
                         ("notification-failure", False), ("raced-exit", False),
                         ("cleanup-failure", False)):
        case = base / (mode + ("-toggle" if toggle else ""))
        runtime = case / "runtime"
        runtime.mkdir(parents=True)
        (case / "home").mkdir()
        (case / "active").touch()
        canary = case / "unrelated"
        canary.write_text("keep\n")
        video = case / "synthetic.mp4"
        video.write_bytes(b"fixture")
        pidfile = runtime / "omarchy-screenrecord-pid"
        statefile = runtime / "omarchy-screenrecord-filename"
        modules = runtime / "omarchy-screenrecord-pa-modules"
        pidfile.write_text("424242\n")
        statefile.write_text(str(video) + "\n")
        modules.write_text("10\n11\n12\n")
        env = {
            "PATH": f"{bindir}:/usr/bin:/bin", "HOME": str(case / "home"),
            "LANG": "C", "OMARCHY_PATH": str(root),
            "XDG_RUNTIME_DIR": str(runtime), "OMARCHY_SCREENRECORD_DIR": str(case),
            "TEST_CASE": str(case), "TEST_MODE": mode,
        }
        command = ["/bin/bash", str(root / "bin/omarchy-capture-screenrecording")]
        if not toggle:
            command.append("--stop-recording")
        result = subprocess.run(command, env=env, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, timeout=15)
        expected = 0 if mode in ("graceful", "raced-exit") else 1
        label = mode + (" toggle" if toggle else " stop")
        check(result.returncode == expected,
              f"{label}: expected exit {expected}, got {result.returncode}; {result.stderr}")
        events = (case / "signals").read_text().splitlines()
        check(all(e.startswith("--pid 424242") for e in events),
              f"{label}: recorder selection widened")
        forced = mode in ("forced", "kill-failure", "notification-failure")
        check(("--pid 424242 --signal KILL" in events) == forced,
              f"{label}: wrong escalation")
        messages = (case / "notifications").read_text()
        check(("capture.recordingKilled" in messages) == forced,
              f"{label}: wrong notification")
        if forced:
            check("capture.recordingSaved" not in messages,
                  f"{label}: forced stop was announced as saved")
        check(not modules.exists(), f"{label}: audio module state leaked")
        check((case / "audio").read_text().splitlines() ==
              ["unload-module 12", "unload-module 11", "unload-module 10"],
              f"{label}: audio cleanup order changed")
        if mode != "cleanup-failure":
            check(not pidfile.exists() and not statefile.exists(),
                  f"{label}: recording state cleanup skipped")
        check(canary.read_text() == "keep\n", f"{label}: unrelated file changed")
        print(f"ok - {label} preserves cleanup and reports honest status", flush=True)
