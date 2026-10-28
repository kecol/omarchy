"""Synthetic journal replay and private doctor probes; no real engine/journal/agents."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(os.environ['ROOT']).resolve()
KEYS = ('org.omarchy.filesystem.root', 'org.omarchy.harness.model-recovery')


def event(message=None, **fields):
  # Sanitized reconstruction of observed died/remove metadata, not a raw log.
  row = {'_COMM': 'podman', 'SYSLOG_IDENTIFIER': 'podman', '_TRANSPORT': 'journal',
         'PRIORITY': '6', 'PODMAN_TYPE': 'container', 'PODMAN_EVENT': 'died',
         'PODMAN_LABELS': json.dumps(dict.fromkeys(KEYS, 'read-only')),
         'MESSAGE': message or 'fixture container died ('+', '.join(k+'=read-only' for k in KEYS)+')'}
  row.update(fields)
  return row


class JournalTests(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory(prefix='agent-doctor-journal-')
    self.addCleanup(temporary.cleanup)
    self.root = Path(temporary.name)
    self.bin = self.root/'bin'
    self.bin.mkdir()
    self.home = self.root/'home'
    self.home.mkdir()
    self.project = self.root/'project'
    self.project.mkdir()
    self.graph = self.root/'graph'
    self.graph.mkdir()
    self.data = self.root/'entries.json'
    self.calls = self.root/'journal-calls.json'
    self.drained = self.root/'producer-finished'
    self.env = {'PATH': str(self.bin)+':/usr/bin:/bin', 'HOME': str(self.home),
                'OMARCHY_PATH': str(ROOT), 'TEST_DATA': str(self.data),
                'TEST_CALLS': str(self.calls), 'TEST_DRAINED': str(self.drained),
                'TEST_GRAPH': str(self.graph)}
    shutil.copy2(ROOT/'bin/omarchy-agent-container-doctor', self.bin/'omarchy-agent-container-doctor')
    self.program('omarchy-agent-policy', '#!/bin/bash\nprintf \'%s\\n\' \'{"filesystem":{"root":"read-only","tmp":"ephemeral tmpfs"}}\'\n')
    self.program('omarchy-cmd-missing', '#!/bin/bash\nexit 1\n')
    self.program('podman', r'''#!/bin/bash
case "$*" in
  *info*Rootless*) echo true ;;
  *info*GraphRoot*) echo "$TEST_GRAPH" ;;
  *volume\ create*|*volume\ rm*) exit 0 ;;
  *) echo "unexpected fake-engine operation" >&2; exit 99 ;;
esac
''')
    self.program('journalctl', '''#!/usr/bin/python3
import json, os, pathlib, sys
args=sys.argv[1:]
pathlib.Path(os.environ['TEST_CALLS']).write_text(json.dumps(args))
entries=json.loads(pathlib.Path(os.environ['TEST_DATA']).read_text())
for row in entries:
  if isinstance(row,dict) and '--all' not in args:
    row=dict(row)
    message=row.get('MESSAGE')
    if isinstance(message,(str,list)) and len(message)>4096:row['MESSAGE']=None
  print(json.dumps(row) if 'json' in args else row.get('MESSAGE',''), flush=True)
if os.environ.get('TEST_OVERSIZE')=='1':
  print(json.dumps({'MESSAGE':'x'*(8*1024*1024)}),flush=True)
if os.environ.get('TEST_MALFORMED')=='1':print('not-json',flush=True)
for i in range(int(os.environ.get('TEST_TAIL','0'))):
  print(json.dumps({'MESSAGE':'benign tail '+str(i)+' '+('x'*200)}),flush=True)
pathlib.Path(os.environ['TEST_DRAINED']).write_text('finished')
sys.exit(int(os.environ.get('TEST_JOURNAL_EXIT','0')))
''')

  def program(self, name, content):
    path = self.bin/name
    path.write_text(content)
    path.chmod(0o755)

  def run_check(self, entries, doctor=False, **environment):
    self.data.write_text(json.dumps(entries))
    self.drained.unlink(missing_ok=True)
    command = [str(self.bin/'omarchy-agent-container-doctor'), '--quick'] if doctor else [
      '/usr/bin/python3', '-I', '-B', str(ROOT/'default/agents/journal-filesystem-check.py')]
    result = subprocess.run(command, env={**self.env, **environment}, cwd=self.project,
                            capture_output=True, text=True, timeout=15)
    return result

  def checker_module(self):
    spec = importlib.util.spec_from_file_location('journal_check', ROOT/'default/agents/journal-filesystem-check.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

  def classifier(self):
    return self.checker_module().message_has_warning

  def test_doctor_accepts_observed_policy_label_reconstruction(self):
    result = self.run_check([event(), event(PODMAN_EVENT='remove')], doctor=True)
    self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
    self.assertIn('Agent container doctor passed.', result.stdout)
    self.assertTrue(self.drained.exists())

  def test_helper_accepts_policy_labels(self):
    self.assertEqual(self.run_check([event()]).returncode, 0)

  def test_each_label_and_rendered_position(self):
    check = self.classifier()
    for key in KEYS:
      for message in (key+'=read-only', '('+key+'=read-only)',
                      '(a=b, '+key+'=read-only, c=d)', '(a=b, '+key+'=read-only)'):
        with self.subTest(message=message):
          self.assertFalse(check(event(message)))

  def test_genuine_error_in_same_metadata_message_still_blocks(self):
    check = self.classifier()
    for error in ('read-only file system', 'readonly filesystem', 'remount /dev/test ro',
                  'I/O error', 'BTRFS error (device test)', 'EXT4-fs error', 'XFS metadata error'):
      for message in (error+' '+event()['MESSAGE'], event()['MESSAGE']+' '+error):
        with self.subTest(message=message):
          self.assertTrue(check(event(message)))

  def test_real_podman_storage_error_is_not_ignored(self):
    result = self.run_check([event('Error: writing storage: read-only file system', PRIORITY='3')], doctor=True)
    self.assertNotEqual(result.returncode, 0)
    self.assertIn('recent kernel or system logs contain filesystem', result.stderr)

  def test_kernel_and_other_system_messages_still_block(self):
    for row in ({'MESSAGE': 'BTRFS error: checksum mismatch', '_TRANSPORT': 'kernel'},
                {'MESSAGE': 'I/O error on backing storage', '_COMM': 'systemd'},
                {'MESSAGE': 'root remount forced ro'}, {'MESSAGE': 'EXT4-fs error'},
                {'MESSAGE': 'XFS metadata error'}):
      with self.subTest(row=row):
        self.assertEqual(self.run_check([row]).returncode, 1)

  def test_error_in_separate_message_blocks(self):
    result = self.run_check([event(), {'MESSAGE': 'I/O error'}, event()])
    self.assertEqual(result.returncode, 1)
    self.assertTrue(self.drained.exists())

  def test_no_blanket_podman_exclusion(self):
    self.assertEqual(self.run_check([event('podman storage is readonly')]).returncode, 1)

  def test_unstructured_or_noninformational_records_are_not_exempt(self):
    check = self.classifier()
    for fields in ({'_COMM': 'other'}, {'SYSLOG_IDENTIFIER': 'other'}, {'_TRANSPORT': 'kernel'},
                   {'PRIORITY': '3'}, {'PODMAN_TYPE': 'volume'}, {'PODMAN_EVENT': ''},
                   {'PODMAN_EVENT': None}, {'PODMAN_LABELS': ''}, {'PODMAN_LABELS': 'invalid'},
                   {'PODMAN_LABELS': '[]'}, {'PODMAN_LABELS': '{}'},
                   {'PODMAN_LABELS': json.dumps(dict.fromkeys(KEYS, 'writable'))}):
      with self.subTest(fields=fields):
        self.assertTrue(check(event(**fields)))

  def test_unknown_labels_and_lookalikes_still_block(self):
    check = self.classifier()
    for message in ('(other.label=read-only)', '(prefix.'+KEYS[0]+'=read-only)',
                    '('+KEYS[0]+'.suffix=read-only)', '('+KEYS[0]+'=read-only-ish)',
                    '('+KEYS[0]+'=read-only file system)', '('+KEYS[0]+'=READ-ONLY)'):
      with self.subTest(message=message):
        self.assertTrue(check(event(message)))

  def test_benign_and_empty_journal(self):
    for rows in ([], [{'MESSAGE': 'normal system message'}]):
      with self.subTest(rows=rows):
        self.assertEqual(self.run_check(rows).returncode, 0)

  def test_current_boot_window_and_system_coverage_are_preserved(self):
    self.assertEqual(self.run_check([event()]).returncode, 0)
    args = json.loads(self.calls.read_text())
    self.assertEqual(args, ['-b', '--since', '-15 minutes', '--no-pager', '-o', 'json',
                            '--all', '--output-fields=MESSAGE,_COMM,SYSLOG_IDENTIFIER,_TRANSPORT,PRIORITY,PODMAN_TYPE,PODMAN_EVENT,PODMAN_LABELS'])
    self.assertNotIn('-k', args)

  def test_producer_is_drained_after_first_error(self):
    self.assertEqual(self.run_check([{'MESSAGE': 'I/O error'}], TEST_TAIL='2000').returncode, 1)
    self.assertTrue(self.drained.exists(), 'must not SIGPIPE producer after first match')

  def test_journal_failure_is_unverified_even_after_clean_entries(self):
    self.assertEqual(self.run_check([event()], TEST_JOURNAL_EXIT='23').returncode, 2)

  def test_journal_failure_is_unverified_even_after_error_entries(self):
    self.assertEqual(self.run_check([{'MESSAGE': 'I/O error'}], TEST_JOURNAL_EXIT='23').returncode, 2)

  def test_doctor_blocks_on_unverified_journal(self):
    result = self.run_check([], doctor=True, TEST_JOURNAL_EXIT='23')
    self.assertNotEqual(result.returncode, 0)
    self.assertIn('recent journal safety check could not be verified', result.stderr)
    self.assertNotIn('Agent container doctor passed.', result.stdout)

  def test_malformed_json_is_unverified_and_drained(self):
    self.assertEqual(self.run_check([event()], TEST_MALFORMED='1', TEST_TAIL='2000').returncode, 2)
    self.assertTrue(self.drained.exists())

  def test_invalid_entry_shapes_are_unverified(self):
    for row in ({}, {'MESSAGE': None}, {'MESSAGE': [-1]}, {'MESSAGE': [256]},
                {'MESSAGE': [True]}, {'MESSAGE': [1, 'mixed']}, ['invalid entry']):
      with self.subTest(row=row):
        self.assertEqual(self.run_check([row]).returncode, 2)

  def test_doctor_accepts_valid_byte_encoded_message(self):
    message = list(b'\x1b[32mbenign fixture log\x1b[0m')
    result = self.run_check([{'MESSAGE': message}], doctor=True)
    self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
    self.assertIn('Agent container doctor passed.', result.stdout)

  def test_byte_decoding_is_lossless(self):
    data = bytes(range(256))
    decoded = self.checker_module().decode_journal_messages(list(data))
    self.assertEqual(len(decoded), 1)
    self.assertEqual(decoded[0].encode('utf-8', errors='surrogateescape'), data)

  def test_control_and_unicode_bytes_are_scanned(self):
    for data in (b'\x01\x02\x03', '\u001b[32mfixture caf\u00e9\u001b[0m'.encode('utf-8'), b'', b'\xffbenign\xfe'):
      with self.subTest(data=data):
        self.assertEqual(self.run_check([{'MESSAGE': list(data)}]).returncode, 0)

  def test_encoded_filesystem_errors_block(self):
    for data in (b'\x1b[31mI/O error\x1b[0m', b'\xffBTRFS error\xfe', b'read-only file system',
                 b'EXT4-fs error', b'XFS metadata error', b'remount root ro', b'readonly storage'):
      with self.subTest(data=data):
        self.assertEqual(self.run_check([{'MESSAGE': list(data)}]).returncode, 1)

  def test_repeated_message_values_are_all_scanned(self):
    for values in (['benign', 'I/O error'], ['I/O error', 'benign'],
                   ['benign', list(b'\xffread-only file system')],
                   [list(b'benign'), list(b'BTRFS error')]):
      with self.subTest(values=values):
        self.assertEqual(self.run_check([{'MESSAGE': values}]).returncode, 1)

  def test_benign_repeated_values_pass(self):
    for values in (['one', 'two'], ['one', list(b'\x1b[32mtwo\x1b[0m')], [[], 'benign']):
      with self.subTest(values=values):
        self.assertEqual(self.run_check([{'MESSAGE': values}]).returncode, 0)

  def test_bad_duplicate_value_cannot_hide_behind_a_warning(self):
    for values in (['I/O error', None], ['I/O error', [256]], ['benign', [['invalid nesting']]]):
      with self.subTest(values=values):
        self.assertEqual(self.run_check([{'MESSAGE': values}]).returncode, 2)

  def test_encoded_policy_labels_retain_narrow_exemption(self):
    row = event()
    row['MESSAGE'] = list(row['MESSAGE'].encode('utf-8'))
    self.assertEqual(self.run_check([row]).returncode, 0)
    row['MESSAGE'] += list(b' I/O error')
    self.assertEqual(self.run_check([row]).returncode, 1)

  def test_long_message_is_not_elided(self):
    for text, expected in (('x'*5000, 0), ('x'*5000+' I/O error', 1)):
      with self.subTest(expected=expected):
        self.assertEqual(self.run_check([{'MESSAGE': text}]).returncode, expected)
        self.assertEqual(self.run_check([{'MESSAGE': list(text.encode('utf-8'))}]).returncode, expected)

  def test_oversized_record_fails_closed_and_drains(self):
    self.assertEqual(self.run_check([], TEST_OVERSIZE='1', TEST_TAIL='20').returncode, 2)
    self.assertTrue(self.drained.exists())

  def test_missing_journalctl_is_unverified(self):
    (self.bin/'journalctl').unlink()
    self.assertEqual(self.run_check([], PATH=str(self.bin)).returncode, 2)


if __name__ == '__main__':
  unittest.main(verbosity=2)
