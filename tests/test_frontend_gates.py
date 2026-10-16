"""Regression coverage for repository verification gates.

DEFECT-01: `npm run test:editor` used to spawn the esbuild *native ELF binary*
through `process.execPath`, so node tried to parse machine code as JavaScript and
the documented frontend gate crashed for every user. These tests execute the real
gate and assert the invocation shape so the defect cannot silently return.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
EDITOR_GATE = ROOT / 'scripts' / 'test-editor.mjs'
ESBUILD_BIN = ROOT / 'node_modules' / 'esbuild' / 'bin' / 'esbuild'


def _node_available() -> bool:
    return shutil.which('node') is not None


@pytest.mark.skipif(not _node_available(), reason='Node.js is not installed in this environment.')
@pytest.mark.skipif(not ESBUILD_BIN.exists(), reason='node_modules is not installed; run npm ci first.')
class TestEditorGate:
    def test_editor_gate_passes(self):
        """The documented frontend gate must actually run and pass."""
        completed = subprocess.run(
            ['node', str(EDITOR_GATE)],
            cwd=ROOT, capture_output=True, text=True, timeout=180,
        )
        assert completed.returncode == 0, (
            'npm run test:editor failed.\n'
            f'stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}'
        )
        summary = dict(re.findall(r'^# (pass|fail|tests) (\d+)$', completed.stdout, re.M))
        assert summary.get('fail') == '0', f'Editor gate reported failures: {summary}'
        assert int(summary.get('pass', 0)) > 0, f'Editor gate ran no tests: {summary}'

    def test_esbuild_binary_is_not_handed_to_node(self):
        """Guard the root cause: the esbuild binary must be executed, not parsed by node."""
        source = EDITOR_GATE.read_text(encoding='utf-8')
        # The esbuild binary is a native executable; passing process.execPath as the
        # command makes node try to parse it as JavaScript.
        assert 'process.execPath' not in source, (
            'test-editor.mjs must not use process.execPath to launch esbuild; '
            'node_modules/esbuild/bin/esbuild is a native binary since esbuild 0.16.'
        )
        assert 'esbuild/bin/esbuild' in source, 'Expected the esbuild binary to be invoked directly.'

    def test_esbuild_binary_is_native_not_a_shim(self):
        """Confirm the assumption the fix relies on, so a future layout change is caught."""
        if not ESBUILD_BIN.exists():
            pytest.skip('node_modules is not installed.')
        magic = ESBUILD_BIN.read_bytes()[:4]
        assert magic == b'\x7fELF', (
            'esbuild/bin/esbuild is no longer a native ELF binary. Revisit the invocation '
            'in scripts/test-editor.mjs before assuming the direct-exec fix still applies.'
        )


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
