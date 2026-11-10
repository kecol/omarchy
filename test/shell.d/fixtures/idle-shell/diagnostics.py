"""Bounded, read-only failure metadata. Never copy cores, environments or argv."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import time

LIMIT = 4 * 1024 * 1024
REPORT_LIMIT = 65536


def directory(path):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts:
        raise ValueError('Expected an absolute directory without parent traversal')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def read_file(root, relative, limit=LIMIT):
    parts = Path(relative).parts
    if not parts or Path(relative).is_absolute() or any(p in ('.', '..') for p in parts):
        raise ValueError('Unsafe relative path')
    parent = os.dup(root)
    fd = None
    try:
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            os.close(parent)
            parent = child
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > limit:
            raise ValueError('Not a bounded single-link regular file')
        data = bytearray()
        while len(data) <= limit:
            chunk = os.read(fd, min(65536, limit + 1 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
        after = os.fstat(fd)
        fields = lambda s: (s.st_dev, s.st_ino, s.st_mode, s.st_nlink, s.st_uid, s.st_gid, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if len(data) > limit or len(data) != before.st_size or fields(before) != fields(after):
            raise ValueError('File changed or exceeded the read limit')
        return bytes(data), {'size': len(data), 'sha256': hashlib.sha256(data).hexdigest(), 'mtime_ns': before.st_mtime_ns}
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent)


def report_summary(data):
    # A report is untrusted text, not authenticated symbolization. Keep symbols
    # only; argument values, source paths, arbitrary messages and env stay out.
    text = data.decode('utf-8', errors='replace')
    frames = re.findall(r'^#([0-9]{1,4})\s+(?:0x[0-9a-fA-F]+\s+)?(?:in\s+)?([A-Za-z_][A-Za-z_0-9:~.$<>]*)\s*\(', text, re.MULTILINE)
    signals = re.findall(r'^Signal:\s*([0-9]{1,2})\s*$', text, re.MULTILINE)
    return {'unverified_frame_symbols': [{'frame': int(n), 'symbol': s} for n, s in frames[:32]], 'reported_signals': [int(n) for n in signals[:4]], 'raw_report_omitted': True}


def collect(scratch, runtime, status):
    if not 1 <= status <= 255:
        raise ValueError('Failure status required')
    result = {'schema': 1, 'observed_ns': time.time_ns(), 'test_exit_status': status,
              'scope': 'post-failure named-file metadata, NOT original process identity or cause proof',
              'files': {}, 'reports': [], 'packages': {}, 'gaps': [], 'raw_cores_and_process_environment_not_read': True}
    root = directory(scratch)
    try:
        if os.fstat(root).st_uid != os.getuid():
            raise ValueError('Scratch directory must belong to the caller')
        for name in ('quickshell.log', 'exec-log.so', 'omarchy/shell/shell.qml'):
            try:
                _, result['files'][name] = read_file(root, name)
            except (OSError, ValueError):
                result['gaps'].append(name)
        try:
            reports = directory(Path(scratch) / 'home/.cache/quickshell/crashes')
            try:
                # Do not follow directory aliases or inspect unrelated HOME data.
                with os.scandir(reports) as entries:
                    names = []
                    for entry in entries:
                        if len(names) >= 16:
                            raise ValueError('Too many crash directories')
                        names.append(entry.name)
                for name in sorted(names):
                    try:
                        data, meta = read_file(reports, name + '/report.txt', REPORT_LIMIT)
                        summary = report_summary(data)
                        result['reports'].append({**meta, **summary})
                        if not summary['unverified_frame_symbols']:
                            result['gaps'].append('no_recognized_stack_frames')
                        if not summary['reported_signals']:
                            result['gaps'].append('no_recognized_reported_signal')
                    except (OSError, ValueError):
                        result['gaps'].append('crash_report_refused')
            finally:
                os.close(reports)
        except (OSError, ValueError):
            result['gaps'].append('crash_reports_unavailable_or_over_limit')
    finally:
        os.close(root)
    public = directory(runtime)
    try:
        for name in ('usr/bin/quickshell', 'usr/lib/libQt6Core.so.6'):
            try:
                _, result['files'][name] = read_file(public, name, 64 * 1024 * 1024)
            except (OSError, ValueError):
                result['gaps'].append(name)  # A symlink is not a verified executable.
        try:
            packages = directory(Path(runtime) / 'var/lib/pacman/local')
            try:
                with os.scandir(packages) as entries:
                    count = 0
                    for entry in entries:
                        count += 1
                        if count > 8192:
                            raise ValueError('Package inventory limit')
                        if not entry.name.startswith(('quickshell-', 'qt6-base-', 'glibc-', 'mesa-')):
                            continue
                        data, _ = read_file(packages, entry.name + '/desc', REPORT_LIMIT)
                        fields = data.decode('ascii').split('\n\n')
                        values = dict(f.split('\n', 1) for f in fields if '\n' in f)
                        name, version = values.get('%NAME%', ''), values.get('%VERSION%', '')
                        if name not in ('quickshell', 'qt6-base', 'glibc', 'mesa') or not re.fullmatch(r'[A-Za-z0-9.+_:~-]{1,128}', version) or name in result['packages']:
                            raise ValueError('Invalid or duplicate package identity')
                        result['packages'][name] = version
            finally:
                os.close(packages)
        except (OSError, ValueError, UnicodeError):
            result['gaps'].append('package_metadata_incomplete_or_refused')
    finally:
        os.close(public)
    if not result['reports']:
        result['gaps'].append('no_report_summary_available')
    if set(result['packages']) != {'quickshell', 'qt6-base', 'glibc', 'mesa'}:
        result['gaps'].append('required_package_metadata_missing')
    result['capture_status'] = 'partial' if result['gaps'] else 'collected_not_cause_proof'
    return result


if __name__ == '__main__':
    try:
        result = collect(Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3]))
        payload = json.dumps(result, separators=(',', ':'))
        if len(payload.encode()) > 32768:
            raise ValueError('Diagnostic output limit')
        print('# idle-shell-diagnostic ' + payload, file=sys.stderr)
    except (OSError, ValueError, IndexError):
        print('# idle-shell-diagnostic unavailable; original failure retained', file=sys.stderr)
        raise SystemExit(1)
