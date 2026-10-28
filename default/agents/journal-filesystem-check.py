"""Check recent journal messages: exit 0 clean, 1 filesystem warning, 2 unverified."""
import json
import re
import subprocess


WARNING = re.compile(r'read-only|readonly|remount.*ro|I/O error|BTRFS error|EXT4-fs error|XFS.*error', re.I)
POLICY_LABELS = ('org.omarchy.filesystem.root', 'org.omarchy.harness.model-recovery')


# --all avoids journalctl's null elision for fields larger than 4096 bytes.
# Project only these fields so --all does not export unrelated binary payloads.
JOURNAL_FIELDS = 'MESSAGE,_COMM,SYSLOG_IDENTIFIER,_TRANSPORT,PRIORITY,PODMAN_TYPE,PODMAN_EVENT,PODMAN_LABELS'
MAX_ENTRY_BYTES = 8 * 1024 * 1024


def decode_journal_messages(value):
  def decode_one(item):
    if isinstance(item, str):
      return item
    if isinstance(item, list) and all(type(n) is int and 0 <= n <= 255 for n in item):
      # Surrogateescape preserves arbitrary bytes, including ASCII warning text;
      # invalid UTF-8 is valid journal data and must not be dropped or ignored.
      return bytes(item).decode('utf-8', errors='surrogateescape')
    raise ValueError('invalid journal MESSAGE encoding')

  # A numeric array is one byte-valued field. Other arrays represent repeated
  # field values, each of which must be valid before any result is trusted.
  if isinstance(value, list) and value and not all(type(n) is int for n in value):
    return [decode_one(item) for item in value]
  return [decode_one(value)]


def text_has_warning(message, entry):
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


def message_has_warning(entry):
  messages = decode_journal_messages(entry['MESSAGE'])
  return any(text_has_warning(message, entry) for message in messages)


def journal_lines(stream):
  while True:
    line = stream.readline(MAX_ENTRY_BYTES + 1)
    if not line:
      return
    if len(line) > MAX_ENTRY_BYTES:
      # Fail closed on oversized records, but drain them without unbounded RAM.
      while line and not line.endswith(b'\n'):
        line = stream.readline(MAX_ENTRY_BYTES + 1)
      yield None
    else:
      yield line


def check_recent_journal():
  found_warning = False
  unverified = False
  try:
    with subprocess.Popen(['journalctl', '-b', '--since', '-15 minutes', '--no-pager', '-o', 'json',
                           '--all', '--output-fields=' + JOURNAL_FIELDS],
                          stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as process:
      # Drain the entire stream before deciding. Early grep -q can SIGPIPE
      # journalctl; a failed producer must never be mistaken for a clean check.
      for line in journal_lines(process.stdout):
        if line is None:
          unverified = True
          continue
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
