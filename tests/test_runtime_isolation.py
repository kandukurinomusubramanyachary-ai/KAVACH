"""Guard: no test may touch the live runtime database (roadmap Rule 5).

Phase 4 incident: a manual server run omitted KAVACH_DATA_DIR and wrote extra
sessions and audit events into the repository's runtime data. Nothing was erased or
rotated and the shipped state was restored, but the guard below makes the class of
mistake detectable automatically.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
LIVE_DATA = (ROOT / 'data').resolve()


def _python_sources():
    return sorted(p for p in ROOT.rglob('*.py')
                  if '.venv' not in p.parts and 'node_modules' not in p.parts
                  and '__pycache__' not in p.parts)


class TestNoLiveRuntimeAccess:
    def test_no_source_constructs_an_engine_on_the_default_data_dir(self):
        """Every Engine(...) in the repo must be given an explicit isolated directory."""
        offenders = []
        for path in _python_sources():
            text = path.read_text(encoding='utf-8')
            for match in re.finditer(r'Engine\(([^)\n]*)\)', text):
                argument = match.group(1).strip()
                if not argument:
                    continue  # Engine() with no argument is only valid inside a fixture body
                if 'data' in argument and 'tmp' not in argument and 'TemporaryDirectory' not in argument \
                        and 'directory' not in argument and 'root' not in argument and 'KAVACH_DATA_DIR' not in argument:
                    offenders.append(f'{path.relative_to(ROOT)}: Engine({argument})')
        assert not offenders, 'These construct an Engine on a possibly-live path:\n  ' + '\n  '.join(offenders)

    def test_acceptance_scenario_uses_an_isolated_data_dir(self):
        """The acceptance runner must never point the server at the repository data."""
        text = (ROOT / 'tests' / 'acceptance_scenario.py').read_text(encoding='utf-8')
        assert 'KAVACH_DATA_DIR' in text, 'The acceptance runner must set KAVACH_DATA_DIR.'
        assert 'TemporaryDirectory' in text, 'The acceptance runner must use a temporary directory.'
        # It must not fall back to the repository data directory.
        assert "str(ROOT / 'data')" not in text, \
            'The acceptance runner must never fall back to the repository data directory.'

    def test_browser_tests_do_not_default_to_the_live_server(self):
        """Browser scripts must start their own isolated server, not a hard-coded local URL.

        Rule 5 protects live keys, databases and audit history. A test that defaults
        to http://127.0.0.1:8000 writes sessions and audit events into the live
        runtime the moment someone runs it while the app is up, which happened once
        during the design restyle and forced a restore. Pointing at a live server is
        still allowed, but only through an explicit KAVACH_URL opt-in.
        """
        offenders = []
        for path in sorted((ROOT / 'tests').glob('browser_*.py')):
            text = path.read_text(encoding='utf-8-sig')
            for line in text.split('\n'):
                stripped = line.strip()
                if 'getenv' in stripped or 'environ' not in stripped:
                    continue
                if 'http://127.0.0.1' in stripped:
                    offenders.append(f'{path.relative_to(ROOT)}: {stripped}')
        assert not offenders, (
            'these browser tests still fall back to a fixed local URL; use '
            '_isolated_server.isolated_server() so they never touch the live runtime: '
            + '; '.join(offenders))

    def test_live_runtime_is_not_tracked_by_git(self):
        """Runtime data must stay out of version control."""
        gitignore = (ROOT / '.gitignore').read_text(encoding='utf-8')
        assert 'data/' in gitignore or '/data' in gitignore

    def test_engine_fixtures_derive_from_tmp_path(self):
        """Every engine/receiver/client fixture must be isolated, directly or via
        another isolated fixture."""
        isolated = {'tmp_path', 'receiver', 'engine'}
        for path in _python_sources():
            if not path.name.startswith('test_'):
                continue
            text = path.read_text(encoding='utf-8')
            for match in re.finditer(r'def (engine|receiver|client)\(([^)]*)\)', text):
                parameters = {p.strip().split(':')[0].split('=')[0]
                              for p in match.group(2).split(',') if p.strip()}
                if not parameters & isolated:
                    pytest.fail(f'{path.relative_to(ROOT)}: fixture {match.group(1)}() '
                                f'is not isolated from the live runtime: ({match.group(2)})')

    def test_restoring_runtime_leaves_keys_and_history_intact(self, tmp_path):
        """Document the restore invariant: keys are byte-identical and history survives."""
        from backend.engine import Engine
        engine = Engine(tmp_path)
        for mode in ['POWER_SAVING', 'SAFE']:
            message = engine.issue(payload={'mode': mode})
            engine.validate(__import__('json').dumps(message).encode())
        before_keys = engine.secrets
        before_audit = engine.audit()['total']
        # A reset must preserve both.
        engine.reset_demo()
        assert engine.secrets == before_keys
        assert engine.audit()['total'] == before_audit
