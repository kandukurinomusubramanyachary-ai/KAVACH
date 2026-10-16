"""Run the real editor/CSV gates across supported Node and OS layouts.
Use esbuild's public API and explicit TAP so Windows executable paths and
Node's default reporter cannot invalidate the verification harness."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
EDITOR_GATE = ROOT / 'scripts' / 'test-editor.mjs'
ESBUILD_API = ROOT / 'node_modules' / 'esbuild' / 'lib' / 'main.js'


def _node_available() -> bool:
    return shutil.which('node') is not None


@pytest.mark.skipif(not _node_available(), reason='Node.js is not installed in this environment.')
@pytest.mark.skipif(not ESBUILD_API.exists(), reason='node_modules is not installed; run npm ci first.')
class TestEditorGate:
    def test_editor_gate_passes(self):
        """The documented frontend gate must actually run and pass."""
        completed = subprocess.run(
            ['node', '--test-reporter=tap', str(EDITOR_GATE)],
            cwd=ROOT, capture_output=True, text=True, timeout=180,
        )
        assert completed.returncode == 0, (
            'npm run test:editor failed.\n'
            f'stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}'
        )
        summary = dict(re.findall(r'^# (pass|fail|tests) (\d+)$', completed.stdout, re.M))
        assert summary.get('fail') == '0', f'Editor gate reported failures: {summary}'
        assert int(summary.get('pass', 0)) > 0, f'Editor gate ran no tests: {summary}'

    def test_gates_resolve_esbuild_via_supported_api(self):
        for name in ['test-editor.mjs', 'test-csv.mjs']:
            source = (ROOT / 'scripts' / name).read_text(encoding='utf-8')
            assert "from 'esbuild'" in source
            assert 'await build(' in source
            assert 'spawnSync' not in source

    def test_csv_gate_passes(self):
        completed = subprocess.run(
            ['node', '--test-reporter=tap', 'scripts/test-csv.mjs'], cwd=ROOT,
            capture_output=True, text=True, timeout=180)
        assert completed.returncode == 0, completed.stdout + completed.stderr
        summary = dict(re.findall(r'^# (pass|fail|tests) (\d+)$', completed.stdout, re.M))
        assert summary.get('fail') == '0'
        assert int(summary.get('pass', 0)) > 0


@pytest.mark.skipif(not _node_available(), reason='Node.js is not installed in this environment.')
class TestPackageGate:
    def test_documented_npm_scripts_exist(self):
        """Every verification command named in README.md must exist in package.json."""
        package = json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))
        for script in ['test:editor', 'build', 'dev', 'preview']:
            assert script in package['scripts'], f'package.json is missing the "{script}" script.'

    def test_editor_test_compiles_typescript(self):
        """The gate must compile web/src/editor.ts, not a stale copy."""
        source = EDITOR_GATE.read_text(encoding='utf-8')
        assert 'web/src/editor.ts' in source, 'Editor gate must compile the real editor source.'


@pytest.mark.skipif(not _node_available() or not ESBUILD_API.exists(),reason='Install Node and npm ci for renderer gate.')
def test_timeline_renders_real_service_failure_without_acceptance_claim(tmp_path,monkeypatch):
    import sqlite3
    from backend.engine import Engine
    receiver=Engine(tmp_path)
    raw=json.dumps(receiver.issue(payload={'mode':'SAFE'})).encode()
    def unavailable():
        raise sqlite3.OperationalError('synthetic storage outage')
    monkeypatch.setattr(receiver,'connect',unavailable)
    result=receiver.validate(raw)
    assert result['verdict']=='SERVICE_ERROR' and not result['audit_persisted']
    rendered=subprocess.run(['node','scripts/test-render.mjs'],input=json.dumps(result),cwd=ROOT,
                            capture_output=True,text=True,timeout=180)
    assert rendered.returncode==0,rendered.stdout+rendered.stderr
