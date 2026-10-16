# CI verification

Workflow: `.github/workflows/ci.yml`. Five jobs on pull requests to main, pushes to
main, and manual dispatch. Read-only contents permission; checkout
credentials are not persisted. No deployment, production credentials or private
runtime files. Dependency caches contain packages, never runtime databases/keys.

Python 3.12 / Node 22 on disposable Ubuntu runners. Python job installs npm modules
because the pytest suite runs actual editor/CSV subprocesses. It publishes actual
passed/failed/error/skipped counts and duration from JUnit; Linux required skips fail.
Browser job pins Playwright, installs Chromium with OS dependencies and executes all
four existing suites plus browser_ux. Secure-release builds/verifies an exact allowlist
ZIP and installs/builds/starts/tests a clean extraction, including Chromium smoke.
Only reviewed source ZIPs, result JSON/XML and screenshots are uploaded, for 7 days.

References checked against official [GitHub Actions](https://github.com/actions/setup-python)
and [Playwright Python CI](https://playwright.dev/python/docs/ci) documentation.

Remote result: NOT RUN at document creation. A locally validated workflow is not a
successful GitHub Actions run. This section will be updated after pushing and reading
GitHub's actual run/job status. Branch protection remains an administrator choice;
this task does not automatically change repository protection or deployment settings.
