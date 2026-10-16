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

## Actual GitHub result

**PASS**, observed 17 October 2026 (Asia/Kolkata), implementation commit
`11573ee31b239d87bdfbcdbea1116fb746fecdab`.

[Successful workflow run 38973628633](https://github.com/kandukurinomusubramanyachary-ai/KAVACH/actions/runs/38973628633)
/ [Pull request 1](https://github.com/kandukurinomusubramanyachary-ai/KAVACH/pull/1).
GitHub returned status completed / conclusion success. Each of python, frontend,
security-scenarios, browser and secure-release completed with conclusion success.

Python job logs report **251 passed, 0 failed, 0 skipped, 8.18 s**. Both local
Windows skips executed successfully on Ubuntu. Frontend editor/CSV/build, 31 security
cases, 9 acceptance checks, all five Chromium suites and clean-extracted startup /
Chromium smoke passed. The source ZIP, Python XML and selected real screenshots/results
are uploaded as verified-source-release, python-results and browser-evidence, retained
7 days. No runtime directory or signing key was uploaded.

The Linux release job independently verified ZIP SHA-256
`959d9c22add9b07ba005c094339782123b062dd385bcc28c00dbb6aa0b492c30`.
The local Windows archive/report has its own verified hash because Git checkout line
endings differ. Determinism means identical input bytes produce identical ZIP bytes;
per-file hashes validate each actual archive. This is not a cross-platform byte identity
claim.

This document records the completed implementation run. The follow-up evidence-only
commit triggers the same workflow again; the PR's current checks identify the latest
head. No production deployment, merge, force push or branch-protection change occurred.
Branch protection remains an administrator choice.
