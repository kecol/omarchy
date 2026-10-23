#!/bin/bash

set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"
python3 -B - "$ROOT/default/agents/pi/saved-default.py" <<'PY'
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
spec = importlib.util.spec_from_file_location('saved_default', sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with tempfile.TemporaryDirectory(prefix='saved-default-') as temp:
  root = Path(temp)
  assert 'Automatic' in module.saved_default(root)
  settings = root/'.pi/agent/settings.json'
  settings.parent.mkdir(parents=True)
  settings.write_text(json.dumps({'defaultProvider': 'openai', 'defaultModel': 'chosen-model', 'httpProxy': 'PRIVATE-NOT-A-MODEL'}))
  assert module.saved_default(root) == '"openai/chosen-model"'
  settings.write_text(json.dumps({'defaultProvider': 'openai', 'defaultModel': '\x1b[31mattack'}))
  assert '\x1b' not in module.saved_default(root)
  settings.write_text('PRIVATE MALFORMED JSON')
  assert module.saved_default(root) == 'Unavailable (Pi will check at startup)'
  settings.write_text(' ' * 65537)
  assert 'Unavailable' in module.saved_default(root)
  settings.unlink()
  private = root/'do-not-read.json'
  private.write_text('{"defaultProvider":"PRIVATE","defaultModel":"PRIVATE"}')
  settings.symlink_to(private)
  assert 'Unavailable' in module.saved_default(root)
  settings.unlink()
  settings.parent.rmdir()
  settings.parent.symlink_to(root)
  assert 'Unavailable' in module.saved_default(root)
print('ok - saved-default preview reads only bounded metadata and rejects malformed, symlinked, or terminal-control input')
PY
