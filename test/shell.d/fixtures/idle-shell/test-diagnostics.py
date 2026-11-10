"""Inert regressions for failure evidence; never start Quickshell or a compositor."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('idle_diagnostics', HERE / 'diagnostics.py')
diag = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diag)
SCRIPT = HERE.parents[1] / 'shell-idle-spawn-test.sh'


class DiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.scratch = self.root / 'scratch'
        self.scratch.mkdir()
        self.runtime = self.root / 'runtime'
        self.runtime.mkdir()
        for name in ('quickshell.log', 'exec-log.so', 'omarchy/shell/shell.qml'):
            f = self.scratch / name
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text('synthetic bytes\n')
        self.report = self.scratch / 'home/.cache/quickshell/crashes/fixture/report.txt'
        self.report.parent.mkdir(parents=True)
        self.report.write_text('Signal: 11\n#0 0xabcdef in QProcess::start (token="SECRET_ARGUMENT") at /private/SECRET_PATH:1\nAPI_KEY=SECRET_ENV\n')
        # A core must never be opened, even when it is a blocking special file.
        os.mkfifo(self.report.parent / 'core')
        for name in ('quickshell', 'qt6-base', 'glibc', 'mesa'):
            f = self.runtime / f'var/lib/pacman/local/{name}-1-1/desc'
            f.parent.mkdir(parents=True)
            f.write_text(f'%NAME%\n{name}\n\n%VERSION%\n1.0-1\n\n')

    def test_bounded_sanitized_report_and_package_metadata(self):
        result = diag.collect(self.scratch, self.runtime, 37)
        self.assertEqual(result['test_exit_status'], 37)
        self.assertEqual(result['reports'][0]['reported_signals'], [11])
        self.assertEqual(result['reports'][0]['unverified_frame_symbols'], [{'frame': 0, 'symbol': 'QProcess::start'}])
        self.assertEqual(result['packages']['qt6-base'], '1.0-1')
        text = json.dumps(result)
        for secret in ('SECRET_ARGUMENT', 'SECRET_ENV', 'SECRET_PATH'):
            self.assertNotIn(secret, text)
        self.assertLess(len(text), 32768)
        self.assertEqual(self.report.read_text().count('SECRET'), 3)

    def test_symlink_hardlink_fifo_oversize_and_directory_alias_refused(self):
        target = self.root / 'external'
        target.write_text('Signal: 6\n')
        self.report.unlink()
        variants = ('symlink', 'hardlink', 'fifo', 'oversize')
        for variant in variants:
            with self.subTest(variant=variant):
                if variant == 'symlink':
                    self.report.symlink_to(target)
                elif variant == 'hardlink':
                    os.link(target, self.report)
                elif variant == 'fifo':
                    os.mkfifo(self.report)
                else:
                    self.report.write_bytes(b'x' * (diag.REPORT_LIMIT + 1))
                result = diag.collect(self.scratch, self.runtime, 1)
                self.assertEqual(result['reports'], [])
                self.assertIn('crash_report_refused', result['gaps'])
                self.report.unlink()
        with self.assertRaises(ValueError):
            diag.collect(self.scratch, self.runtime, 0)
        alias = self.root / 'alias'
        alias.symlink_to(self.scratch, target_is_directory=True)
        with self.assertRaises(OSError):
            diag.collect(alias, self.runtime, 1)

    def cleanup_case(self, status, break_collector=False):
        # Extract ONLY the actual cleanup function. The real test's top-level
        # compositor gate, shell launch and signal helpers are never executed.
        text = SCRIPT.read_text()
        cleanup = text.split('cleanup() {', 1)[1].split('\ntrap cleanup EXIT', 1)[0]
        source = self.root / 'fixture-shell.d'
        if break_collector:
            source.mkdir()
        else:
            source = HERE.parents[1]
        script = 'set -euo pipefail\n' + '''
TMPDIR=$1
SHELL_TEST_DIR=$2
QS_PID=""
test_root=""
exec_log=""
stop_event_monitors() { :; }
stop_processes() { :; }
cleanup() {''' + cleanup + '\ntrap cleanup EXIT\nexit "$3"\n'
        result = subprocess.run(['/bin/bash', '-c', script, 'inert-cleanup', str(self.scratch), str(source), str(status)], stdin=subprocess.DEVNULL, capture_output=True)
        self.assertEqual(result.returncode, status)
        self.assertFalse(self.scratch.exists(), 'Real synthetic scratch cleanup must still run')
        return result.stderr.decode()

    def test_failure_evidence_precedes_real_scratch_deletion_and_status_survives(self):
        output = self.cleanup_case(37)
        marker = '# idle-shell-diagnostic '
        self.assertIn(marker, output)
        result = json.loads(next(line[len(marker):] for line in output.splitlines() if line.startswith(marker)))
        self.assertEqual(result['test_exit_status'], 37)
        self.assertEqual(result['reports'][0]['reported_signals'], [11])
        self.assertNotIn('SECRET', output)

    def test_collector_failure_preserves_original_failure_and_cleanup(self):
        output = self.cleanup_case(37, break_collector=True)
        self.assertIn('diagnostic collection failed; original failure retained', output)

    def test_success_is_unchanged_and_has_no_failure_capture(self):
        self.assertNotIn('idle-shell-diagnostic', self.cleanup_case(0))


if __name__ == '__main__':
    unittest.main(verbosity=2)
