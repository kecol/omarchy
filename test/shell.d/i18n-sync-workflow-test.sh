#!/bin/bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

# Exercise the actual inline gate without a YAML package or any credentials.
python3 - <<'PY'
import os
import re
import subprocess
import tempfile
import textwrap
from pathlib import Path

workflow = (Path(os.environ['ROOT']) / '.github/workflows/i18n-sync.yml').read_text()
jobs = dict(re.findall(r'^  ([a-z-]+):\n(.*?)(?=^  [a-z-]+:\n|\Z)', workflow.split('\njobs:\n', 1)[1], re.M | re.S))
prepare = jobs['prepare']
gate = prepare.split('      - name: Check translation configuration\n', 1)[1].split('      - uses:', 1)[0]
script = textwrap.dedent(gate.split('        run: |\n', 1)[1])
assert prepare.index('Check translation configuration') < prepare.index('actions/checkout@')
assert 'MUSE_API_KEY: ${{ secrets.MUSE_API_KEY }}' in gate
assert '${{ secrets.MUSE_API_KEY }}' not in prepare.replace(gate, '')
assert prepare.count("if: steps.configuration.outputs.enabled == 'true'") == 2
for output, default in [('locales', '[]'), ('extract', 'false'), ('has_work', 'false')]:
  assert f"{output}: ${{{{ steps.pending.outputs.{output} || '{default}' }}}}" in prepare
assert "- '.github/workflows/i18n-sync.yml'" in workflow
print('ok - gate precedes checkout, scopes the secret to one step, and supplies safe skipped-step outputs')

# Every downstream job must stop when prepare has no work. In particular,
# always() jobs must not bypass the missing-secret no-op.
assert set(jobs) == {'prepare', 'extract', 'validate-extract', 'publish-extract', 'translate', 'collect', 'land'}
for name in ('extract', 'validate-extract'):
  assert "if: needs.prepare.outputs.extract == 'true'" in jobs[name]
assert "if: needs.prepare.outputs.locales != '[]'" in jobs['translate']
assert 'needs: [prepare, publish-extract]' in jobs['translate']
assert 'fromJSON(needs.prepare.outputs.locales)' in jobs['translate']
for name in ('publish-extract', 'collect'):
  assert "needs.prepare.outputs.has_work == 'true'" in jobs[name]
assert "needs.publish-extract.result == 'success'" in jobs['collect']
assert "needs.collect.result == 'success'" in jobs['land']
print('ok - disabled defaults skip extraction, matrix translation, and always-conditioned publishing jobs')

check = (Path(os.environ['ROOT']) / '.github/workflows/i18n-check.yml').read_text()
assert 'bash test/shell.d/i18n-sync-workflow-test.sh' in check
pattern = re.search(r"grep -qE '([^']+)'", check).group(1)
assert re.search(pattern, 'test/shell.d/i18n-test.sh')
assert re.search(pattern, 'test/shell.d/i18n-sync-workflow-test.sh')
assert re.search(pattern, '.github/workflows/i18n-sync.yml')
print('ok - pull-request checks run this regression when either the workflow or its tests change')

with tempfile.TemporaryDirectory(prefix='omarchy i18n gate ') as directory:
  root = Path(directory)
  marker = root / 'unexpected-execution'
  synthetic = f"synthetic-'\"-$(touch '{marker}')\nnot-a-real-key"
  for name, key, enabled in [('unset', None, False), ('empty', '', False), ('configured', synthetic, True)]:
    output, summary = root / (name + '.output'), root / (name + '.summary')
    env = {'PATH': '/usr/bin:/bin', 'HOME': directory, 'GITHUB_OUTPUT': str(output), 'GITHUB_STEP_SUMMARY': str(summary)}
    if key is not None:
      env['MUSE_API_KEY'] = key
    result = subprocess.run(['/bin/bash', '-e', '-c', script], env=env, text=True, capture_output=True, timeout=5)
    assert result.returncode == 0, result.stderr
    assert output.read_text() == f"enabled={str(enabled).lower()}\n"
    text = result.stdout + result.stderr + (summary.read_text() if summary.exists() else '')
    if enabled:
      assert not summary.exists()
      assert not text
      assert key not in output.read_text()
    else:
      assert '::notice::Automatic translation sync skipped' in result.stdout
      assert 'optional' in summary.read_text()
      assert 'English fallback' in summary.read_text()
    assert not marker.exists()
    print(f'ok - {name} synthetic secret selects the expected path without exposure or shell evaluation')
PY
