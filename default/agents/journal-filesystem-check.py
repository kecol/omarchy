"""Check recent journal messages: exit 0 clean, 1 filesystem warning, 2 unverified."""
import json
import re
import subprocess


WARNING = re.compile(r'read-only|readonly|remount.*ro|I/O error|BTRFS error|EXT4-fs error|XFS.*error', re.I)
POLICY_LABELS = ('org.omarchy.filesystem.root', 'org.omarchy.harness.model-recovery')


def message_has_warning(entry):
  message = entry['MESSAGE']
  if not isinstance(message, str):
    raise ValueError('journal MESSAGE is not text')
  # Only structured informational Podman container events qualify. Never drop
  # a whole message: a genuine error beside a harmless label must still block.
  if (entry.get('_COMM') == 'podman' and entry.get('SYSLOG_IDENTIFIER') == 'podman'
      and entry.get('_TRANSPORT') == 'journal' and entry.get('PRIORITY') == '6'
      and entry.get('PODMAN_TYPE') == 'container'
      and isinstance(entry.get('PODMAN_EVENT'), str) and entry['PODMAN_EVENT']):
    try:
      labels = json.loads(entry.get('PODMAN_LABELS', ''))
    except (ValueError, TypeError):
      labels = None
    if isinstance(labels, dict):
      for key in POLICY_LABELS:
        if labels.get(key) == 'read-only':
          # Boundaries match Podman's rendered label list, not arbitrary prose
          # such as "key=read-only file system" or a longer label/value.
          pattern = r'(^|, |\()' + re.escape(key) + r'=read-only(?=, |\)|$)'
          message = re.sub(pattern, lambda m: m[1] + key + '=<container-policy>', message)
  return bool(WARNING.search(message))


def check_recent_journal():
  found_warning = False
  unverified = False
  try:
    with subprocess.Popen(['journalctl', '-b', '--since', '-15 minutes', '--no-pager', '-o', 'json'],
                          stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as process:
      # Drain the entire stream before deciding. Early grep -q can SIGPIPE
      # journalctl; a failed producer must never be mistaken for a clean check.
      for line in process.stdout:
        try:
          entry = json.loads(line)
          if not isinstance(entry, dict):
            raise ValueError('journal entry is not an object')
          found_warning = message_has_warning(entry) or found_warning
        except (ValueError, TypeError, KeyError):
          unverified = True
      if process.wait() != 0:
        unverified = True
  except OSError:
    return 2
  if unverified:
    return 2
  return 1 if found_warning else 0


if __name__ == '__main__':
  raise SystemExit(check_recent_journal())
