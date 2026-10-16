# KAVACH visual system

Restyled in the Linear design language: a near-black canvas, a four-step surface ladder, hairline borders instead of shadows, a single lavender accent, and a type scale with aggressively negative tracking. The console is a dense security tool, so the marketing spec's display sizes are capped and 14px is the working text size.

The authoritative implementation is `web/src/tokens.css` (tokens, font faces, reset, focus ring) and `web/src/styles.css` (every component). `web/src/mission.css` is a retirement stub — the previous system's cyan theme is gone. All 337 class names used by the React tree are covered; no class was renamed.

## Tokens

| Role | Token | Value |
|---|---|---|
| Canvas | `--bg` | `#010102` |
| Surface 1 (cards) | `--surface-1` | `#0c0e12` |
| Surface 2 (raised) | `--surface-2` | `#131519` |
| Surface 3 (pills, inputs) | `--surface-3` | `#191c22` |
| Surface 4 (hover) | `--surface-4` | `#21252c` |
| Hairline | `--hairline` | `#23252a` |
| Hairline strong | `--hairline-strong` | `#2f3238` |
| Hairline tertiary | `--hairline-tertiary` | `#1a1c20` |
| Primary (lavender) | `--primary` | `#5e6ad2` |
| Primary hover | `--primary-hover` | `#828fff` |
| Primary focus tint | `--primary-focus` | `#5e69d1` |
| Brand secure | `--brand-secure` | `#7a7fad` |
| Text | `--ink` | `#f7f8f8` |
| Text muted | `--ink-muted` | `#d0d6e0` |
| Text subtle | `--ink-subtle` | `#8a8f98` |
| Text tertiary | `--ink-tertiary` | `#62666d` |
| Success | `--success` | `#27a644` |
| Danger | `--danger` | `#e5484d` |
| Warning | `--warn` | `#f0b429` |

The canvas is `#010102`, not `#000000` — true black is not used anywhere.

## Depth

No drop shadows, at any elevation. Depth comes from the surface ladder (`#010102` → `#0c0e12` → `#131519` → `#191c22` → `#21252c`), a 1px hairline border, and on panels a faint white top-edge highlight (`linear-gradient(rgba(255,255,255,.04), transparent)`). Focus is a real 2px outline in `--primary` at 50% opacity with a 1px offset, not a box-shadow, so it survives forced-colors mode.

## Typography

Inter 400/500/600/700 substitutes Linear's proprietary Display and Text cuts, with the SF Pro Display fallback chain the spec documents. JetBrains Mono substitutes Linear Mono. Both families are vendored as WOFF2 in `web/public/fonts` so the app is self-contained and renders identically offline — the in-app preview has no network access. The unreferenced `kavach-font-*.ttf` files remain on disk.

Scale, with the spec's negative tracking:

| Role | Size | Line height | Tracking | Weight |
|---|---|---|---|---|
| display-xl | 80px | 88px | −3.0px | 600 |
| display-lg | 56px | 60px | −2.0px | 600 |
| display-md | 40px | 48px | −1.0px | 600 |
| display-sm | 28px | 34px | −0.6px | 600 |
| title-xl | 22px | 30px | −0.4px | 600 |
| title-lg | 18px | 26px | −0.2px | 500 |
| title-md | 16px | 22px | −0.1px | 500 |
| body-lg | 15px | 22px | −0.1px | 400 |
| **body-sm** | **14px** | **20px** | **0** | **400** |
| caption | 12px | 16px | 0 | 400 |
| eyebrow | 13px | 18px | +0.4px | 500 |

`body-sm` at 14px is the console's working size. Headings are capped at weight 600. Mono is reserved for code, identifiers, keys, timestamps and measured values.

## Space and radius

4px base: `--s-1:4` through `--s-section:96`. Radius scale `--r-xs:4`, `--r-sm:6`, `--r-md:8`, `--r-lg:12`, `--r-xl:16`, plus `--r-pill:9999px`. Buttons and inputs are 8px; cards are 12px; panels are 16px. Buttons are never pill-rounded — pill is reserved for status chips and badges.

## Components

- **Buttons.** Primary is lavender on white text, 40px tall (raised from the spec's 32px to satisfy the 40px touch-target rule). Secondary and tertiary are 32px, hairline-bordered, transparent, filling to `--surface-4` on hover. Ghost buttons carry only text plus a 13px icon.
- **Nav.** 56px sticky, blurred and translucent over the canvas, separated by a hairline, items 8px radius, centred, with a 32px avatar-free right cluster.
- **Panels and cards.** 12–16px radius, `--surface-1`/`--surface-2`, 1px hairline, no shadow, 20–24px padding.
- **Status chips.** Pill radius, `--surface-2` background, a coloured dot plus an explicit word. The dot is never the only signal.
- **Code and evidence.** `--surface-3`, 8px radius, JetBrains Mono at 12–13px, syntax colours from a restrained ANSI-like set that never competes with the lavender accent.

## Responsive

Content max-width 1280px, centred. The grid is 3-up, then 2-up at 1100px, then 1-up at 760px. The nav collapses to a hamburger at **1200px** rather than the spec's 768px, because KAVACH has eight destinations rather than a marketing site's four; between 1280 and 1440px the brand subtitle is hidden so the nav fits. Tables keep horizontal scrolling and are never shrunk to fit. Dialogs contain focus and restore it on close. `prefers-reduced-motion` disables all transitions.

## Documented deviation: verdict colours

The spec allows exactly one chromatic colour — lavender — plus neutral greys, because a marketing page never has to say "this failed a security check". KAVACH must. Two hues are therefore added and used **only** for security verdicts, never for decoration:

- `--danger #e5484d` — REJECTED, FAIL, authentication and integrity failures.
- `--warn #f0b429` — ATTENTION: anomalies and fixtures nearing expiry.
- `--success #27a644` — ACCEPTED, PASS, a clean audit chain. This is the spec's own green and needs no deviation.

A stage that never executed is **neutral** (`--ink-tertiary`), never amber or red: "not run" is neither a pass nor a failure, and colouring it would read as a defect where there is only an absent step.

KAVACH's own rule still binds on top of this: semantic states never rely on colour alone. Every verdict is paired with an explicit word (PASS / FAIL / NOT_RUN) and a symbol.

## Behaviour preserved

The restyle changes pixels, not behaviour. The receiver explanation remains the primary outcome text. Authentication, key match and authorisation are rendered independently from their checks; authorisation is never inferred from a valid HMAC. Unknown or not-run facts stay explicit. Scenario expectations are labelled as expectations, never as receiver verdicts. Persisted audit status always comes from the receiver. No live-system claims, no ornamental monitoring graphs.

## Verification

`tests/visual_design.py` reads computed styles off the live DOM and asserts the tokens are actually applied — canvas `rgb(1,1,2)`, surface-1 `rgb(12,14,18)`, hairline `rgb(35,37,42)`, 12px card radius, no panel shadow, lavender CTA at 8px radius and 40px height, 32px secondary, 9999px pill, 14px body, 28px headline at weight 600 with −0.6px tracking, both font families loaded, and the danger tint on a rejected verdict. It also asserts no horizontal overflow and correct nav collapse at 1440/1280/1024/820/480, that the hamburger opens and closes, and that no page error fires. Screenshots land in `reports/design/`.

`tests/browser_design.py` verifies reflow at 1440/1024/768/390/320, modal focus containment and restoration, and a visible editor focus ring. `tests/browser_smoke.py` and `tests/browser_hardening.py` cover the functional walkthrough. All three start their own isolated server — see `tests/_isolated_server.py`.
