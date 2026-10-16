"""Verify a source ZIP by installing, building and running only its extracted files."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

from release import validate_archive


def verify(archive: Path, browser: bool = False) -> dict:
    inspected = validate_archive(archive)
    npm = shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
    if not npm:
        raise RuntimeError('npm is required for clean-extraction verification')
    with tempfile.TemporaryDirectory(prefix='kavach-extraction-') as directory:
        temporary = Path(directory)
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(temporary)  # exact member/path/symlink checks above
        root = temporary/'kavach'
        environment = dict(os.environ, KAVACH_DATA_DIR=str(temporary/'runtime'),
                           PYTHONUTF8='1', PYTHONIOENCODING='utf-8')
        for name in ('KAVACH_ALLOW_EXTERNAL', 'KAVACH_ALLOW_POLICY_ADMIN', 'KAVACH_URL'):
            environment.pop(name, None)

        def run(*command):
            subprocess.run(command, cwd=root, env=environment, check=True, timeout=600)

        run(sys.executable, '-m', 'venv', str(temporary/'python'))
        python = temporary/'python'/('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        run(str(python), '-m', 'pip', 'install', '-r', 'requirements-dev.txt')
        if browser:
            run(str(python), '-m', 'pip', 'install', '-r', 'requirements-browser.txt')
            run(str(python), '-m', 'playwright', 'install', '--with-deps', 'chromium')
        run(npm, 'ci')
        run(npm, 'run', 'test:editor')
        run(npm, 'run', 'test:csv')
        run(npm, 'run', 'build')
        run(str(python), '-m', 'scripts.run_scenarios')
        run(str(python), 'tests/acceptance_scenario.py')
        # Import helper from extracted tests, never from the developer checkout.
        probe = '''
import json, sys, urllib.request
sys.path.insert(0, 'tests')
from _isolated_server import isolated_server
with isolated_server() as base:
    with urllib.request.urlopen(base) as response:
        html = response.read().decode()
        assert response.status == 200 and '/assets/' in html
    with urllib.request.urlopen(base + '/fonts/inter-400.woff2') as response:
        assert response.status == 200 and response.read(4) == b'wOF2'
    with urllib.request.urlopen(base + '/api/health') as response:
        assert json.load(response)['status'] == 'online'
print('Clean-extraction HTML, font and API startup: PASS')
'''
        run(str(python), '-c', probe)
        if browser:
            run(str(python), 'tests/browser_smoke.py')
    return {'status': 'PASS', 'archive': inspected, 'clean_install': True,
            'frontend_build': True, 'security_scenarios': True,
            'acceptance_checks': True, 'html_font_api_startup': True, 'chromium_smoke': 'PASS' if browser else 'NOT RUN'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--browser', action='store_true', help='Also install Chromium and run smoke from extracted source.')
    args = parser.parse_args()
    if args.report:
        args.report.unlink(missing_ok=True)
    result = verify(args.archive.resolve(), args.browser)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
