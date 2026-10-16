# Release verification

Original failure reproduced on main 6b473b4: missing
`reports/browser-results.json`. The old manifest referenced unpublished recordings
and reports and omitted current modules, CSS, fonts, tests and documentation.

The reviewed exact allowlist now includes the app's source/import graph, local fonts
and licenses, backend, manifests, test utilities, docs and CI. Generated reports,
recordings, runtime data, dependencies and caches are excluded. Discovery checks are
fail-only: a newly introduced source/asset must be explicitly reviewed and allowlisted.
Safe-path checks were strengthened for Windows drive/stream/reserved/normalized names.
Existing secret scanning, symlink refusal, archive-member equality, CRC and per-file
hash validation remain mandatory. A generated archive manifest is not trusted as a
substitute for source completeness.

The initial repaired source archive passed clean installation, 31 scenarios, 9
acceptance checks and HTML/font/API startup. After final source/documentation updates,
`verify_release.py --browser` independently repeats those checks and Chromium smoke
from the exact final extraction. Its generated `reports/final/clean-extraction.json`
contains the actual status and SHA-256; the CI release artifact includes this report.
Read that execution result rather than treating these instructions as evidence.
A stale tracked root RELEASE_MANIFEST.json was removed; each ZIP gets a newly
computed manifest. Generated reports remain outside the allowlist.

Reproduce (choose a temporary destination on your platform):

```sh
python scripts/release.py --output /tmp/KAVACH-final-release.zip
python scripts/release.py --verify /tmp/KAVACH-final-release.zip
python scripts/verify_release.py /tmp/KAVACH-final-release.zip --browser --report reports/final/clean-extraction.json
```

The last command creates and cleans a private temporary extraction, virtualenv and
runtime. It installs pinned project manifests, builds only extracted sources, runs
security/acceptance and Chromium smoke, and checks HTML/font/API startup. It never
uses a presenter's data directory. No missing reports are manufactured.

Regression gates cover omitted/new/missing source, private data names, Windows unsafe
paths, actual OS symlinks on Linux, archive symlinks on all platforms, known secrets in
source/compiled assets, private-key markers, deterministic builds and hash tampering.
Secret detection is scoped to known sources and private-key markers, not a universal
secret detector.

## Executed outcome

PASS: the independent local extraction installed a fresh Python environment and
locked npm dependencies, passed editor/CSV/build, 31 security and 9 acceptance cases,
served HTML/fonts/API and passed 16/16 Chromium smoke checks. The generated JSON
report's archive hash was compared to the delivered ZIP bytes.

The actual [successful GitHub run](https://github.com/kandukurinomusubramanyachary-ai/KAVACH/actions/runs/38973628633)
also built, independently verified and exercised a clean extraction on Ubuntu. CI
artifacts contain the source ZIP and machine-readable verification result. Archive
hashes can differ between Windows CRLF and Linux LF checkouts; every distributed
archive is verified against its own exact manifest. No generic workspace ZIP is used.
