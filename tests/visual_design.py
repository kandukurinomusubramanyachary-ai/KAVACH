"""Visual verification of the Linear design language applied to KAVACH.

Captures real screenshots of every page against a live server, then asserts the
design tokens are actually applied (canvas, surface ladder, hairlines, lavender,
Inter/JetBrains Mono, radius scale) and that no rule violation slipped in.

Run: .venv/bin/python tests/visual_design.py
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
PORT = int(os.environ.get('KAVACH_VISUAL_PORT', '8031'))
BASE = f'http://127.0.0.1:{PORT}'
OUT = ROOT / 'reports' / 'design'
OUT.mkdir(parents=True, exist_ok=True)
PAGES = [
    ('console', 'Console'),
    ('demo', 'Demo'),
    ('scenarios', 'Scenarios'),
    ('timeline', 'Timeline'),
    ('compare', 'Compare'),
    ('metrics', 'Metrics'),
    ('audit', 'Audit'),
    ('policy', 'Policy'),
]
RESULTS = []


def record(name, passed, detail=''):
    RESULTS.append({'name': name, 'passed': bool(passed), 'detail': detail})


def main():
    from playwright.sync_api import sync_playwright
    with tempfile.TemporaryDirectory(prefix='kavach-visual-') as directory:
        server = subprocess.Popen(
            [sys.executable, '-m', 'backend', '--port', str(PORT)],
            cwd=ROOT, env=dict(os.environ, KAVACH_DATA_DIR=directory),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for _ in range(80):
                try:
                    with urllib.request.urlopen(BASE + '/api/health', timeout=5) as r:
                        if json.load(r).get('status') == 'online':
                            break
                except Exception:
                    pass
                time.sleep(0.25)
            else:
                print('BLOCKED: server did not become healthy.')
                return 2

            with sync_playwright() as p:
                browser = p.chromium.launch(args=['--no-sandbox', '--force-color-profile=srgb'])
                errors = []
                for width, label in [(1440, 'desktop'), (820, 'tablet'), (480, 'mobile')]:
                    context = browser.new_context(viewport={'width': width, 'height': 1000},
                                                  device_scale_factor=2)
                    page = context.new_page()
                    page.on('pageerror', lambda e: errors.append(str(e)))
                    page.goto(BASE, wait_until='networkidle')
                    page.wait_for_timeout(700)
                    seed_activity(page)

                    for slug, title in PAGES:
                        navigate(page, title, 450)
                        page.screenshot(path=str(OUT / f'{slug}-{label}.png'), full_page=True)

                    # Drive a real decision so the result surfaces are populated.
                    navigate(page, 'Demo', 350)
                    try:
                        page.click('.demo-actions button:has-text("Generate")', timeout=5000)
                        page.wait_for_timeout(500)
                        # The submit control lives on the Mission Console.
                        navigate(page, 'Console', 350)
                        page.click('.submit-btn', timeout=5000)
                        page.wait_for_timeout(1000)
                        page.screenshot(path=str(OUT / f'decision-{label}.png'), full_page=True)
                    except Exception as exc:
                        record(f'Drive a real decision ({label})', False, str(exc)[:90])
                    context.close()

                # ---- responsive behaviour at every breakpoint ----
                assert_responsive(browser)

                # ---- token assertions on the real rendered page ----
                context = browser.new_context(viewport={'width': 1440, 'height': 1000})
                page = context.new_page()
                page.goto(BASE, wait_until='networkidle')
                page.wait_for_timeout(600)
                assert_tokens(page)
                context.close()

                record('No uncaught page errors', not errors, '; '.join(errors[:3])[:160])
                browser.close()
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()

    width = max(len(r['name']) for r in RESULTS)
    print(f"\n{'CHECK':<{width}}  RESULT  DETAIL")
    print('-' * (width + 26))
    for row in RESULTS:
        print(f"{row['name']:<{width}}  {'PASS' if row['passed'] else 'FAIL':<6}  {row['detail']}")
    failed = [r for r in RESULTS if not r['passed']]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} design checks passed. "
          f"Screenshots in {OUT.relative_to(ROOT)}/")
    return 1 if failed else 0




def navigate(page, title, wait=400):
    """Click a nav item, opening the hamburger first when the nav is collapsed."""
    toggle = page.locator('.nav-toggle')
    if toggle.count() and toggle.first.is_visible():
        if not page.locator('.topbar nav.open').count():
            toggle.first.click()
            page.wait_for_timeout(220)
    page.click(f'.nav-item:has-text("{title}")', timeout=8000)
    page.wait_for_timeout(wait)

def seed_activity(page):
    """Drive real decisions so the metrics, comparison and audit pages carry data."""
    for scenario, button in [('valid', 'Tamper'), ('tampered', 'Tamper'),
                             ('unauthorised', 'Unauthorised'), ('telemetry', 'Telemetry fixture')]:
        try:
            navigate(page, 'Console', 250)
            page.click(f'.quick-actions button:has-text("{button}")')
            page.wait_for_timeout(300)
            page.click('.submit-btn')
            page.wait_for_timeout(700)
        except Exception:
            pass
    # capture one side of the comparison
    try:
        page.click('.quick-actions button:has-text("Capture normal")')
        page.wait_for_timeout(250)
    except Exception:
        pass
    try:
        page.click('.quick-actions button:has-text("Tamper")')
        page.wait_for_timeout(300)
        page.click('.submit-btn')
        page.wait_for_timeout(700)
        page.click('.quick-actions button:has-text("Capture attack")')
        page.wait_for_timeout(250)
    except Exception:
        pass


def assert_responsive(browser):
    """No horizontal overflow and a working nav at every breakpoint (spec: Responsive)."""
    for width in (1440, 1280, 1024, 820, 480):
        context = browser.new_context(viewport={'width': width, 'height': 900})
        page = context.new_page()
        page.goto(BASE, wait_until='networkidle')
        page.wait_for_timeout(600)
        overflow = page.evaluate(
            "()=>document.documentElement.scrollWidth>document.documentElement.clientWidth+1")
        record(f'No horizontal overflow at {width}px', not overflow,
               f'scrollWidth={page.evaluate("()=>document.documentElement.scrollWidth")}')
        nav_visible = page.locator('.topbar nav').is_visible()
        toggle_visible = page.locator('.nav-toggle').is_visible()
        # Exactly one of the two must be visible: the inline nav or the hamburger.
        record(f'Nav collapses correctly at {width}px', nav_visible != toggle_visible,
               f'nav={nav_visible} hamburger={toggle_visible}')
        if toggle_visible:
            page.click('.nav-toggle')
            page.wait_for_timeout(250)
            opened = page.locator('.topbar nav.open').is_visible()
            record(f'Hamburger opens the menu at {width}px', opened, str(opened))
            # Choosing a destination must close the menu again.
            page.click('.nav-item:has-text("Scenarios")')
            page.wait_for_timeout(400)
            closed = not page.locator('.topbar nav.open').count()
            record(f'Menu closes after navigating at {width}px', closed, str(closed))
        context.close()

def assert_tokens(page):
    """Read computed styles off the live DOM and compare against the Linear spec."""
    probe = page.evaluate("""() => {
      const cs = getComputedStyle(document.body);
      const btn = document.querySelector('.btn.primary, .submit-btn');
      const panel = document.querySelector('.panel');
      const nav = document.querySelector('.nav-item.active') || document.querySelector('.nav-item');
      const h1 = document.querySelector('h1');
      const badge = document.querySelector('.badge.neutral, .count-pill') || document.querySelector('.badge');
      return {
        canvas: cs.backgroundColor,
        fontFamily: cs.fontFamily,
        bodySize: cs.fontSize,
        btnBg: btn ? getComputedStyle(btn).backgroundColor : null,
        btnRadius: btn ? getComputedStyle(btn).borderRadius : null,
        btnHeight: btn ? getComputedStyle(btn).height : null,
        secHeight: (document.querySelector('.btn.secondary') ? getComputedStyle(document.querySelector('.btn.secondary')).height : null),
        panelBg: panel ? getComputedStyle(panel).backgroundColor : null,
        panelBorder: panel ? getComputedStyle(panel).borderTopColor : null,
        panelRadius: panel ? getComputedStyle(panel).borderRadius : null,
        panelShadow: panel ? getComputedStyle(panel).boxShadow : null,
        navRadius: nav ? getComputedStyle(nav).borderRadius : null,
        h1Size: h1 ? getComputedStyle(h1).fontSize : null,
        h1Weight: h1 ? getComputedStyle(h1).fontWeight : null,
        h1Tracking: h1 ? getComputedStyle(h1).letterSpacing : null,
        badgeRadius: badge ? getComputedStyle(badge).borderRadius : null,
        badgeBg: badge ? getComputedStyle(badge).backgroundColor : null,
      };
    }""")

    def rgb(hex_value):
        h = hex_value.lstrip('#')
        return f'rgb({int(h[0:2],16)}, {int(h[2:4],16)}, {int(h[4:6],16)})'

    record('Canvas is #010102 (not true black)', probe['canvas'] == rgb('#010102'), probe['canvas'])
    record('Surface-1 panel background', probe['panelBg'] == rgb('#0c0e12'), probe['panelBg'])
    record('Hairline border #23252a', probe['panelBorder'] == rgb('#23252a'), probe['panelBorder'])
    record('Card radius is 12px (rounded.lg)', probe['panelRadius'] == '12px', probe['panelRadius'])
    record('No drop shadow on panels', probe['panelShadow'] in ('none', ''), probe['panelShadow'])
    record('Primary CTA is lavender #5e6ad2', probe['btnBg'] == rgb('#5e6ad2'), probe['btnBg'])
    record('Button radius is 8px (rounded.md)', probe['btnRadius'] == '8px', probe['btnRadius'])
    record('Primary CTA meets the >=40px touch target', probe['btnHeight'] in ('40px','44px'), probe['btnHeight'])
    record('Secondary button uses the 32px compact spec', probe['secHeight'] == '32px', str(probe['secHeight']))
    record('Nav radius is 8px', probe['navRadius'] == '8px', probe['navRadius'])
    record('Page title is headline 28px', probe['h1Size'] == '28px', probe['h1Size'])
    record('Display weight caps at 600', probe['h1Weight'] == '600', probe['h1Weight'])
    record('Negative display tracking (-0.6px)', probe['h1Tracking'] == '-0.6px', probe['h1Tracking'])
    record('Status pill radius is 9999px', probe['badgeRadius'] == '9999px', probe['badgeRadius'])
    record('Status pill sits on surface-2 #131519', probe['badgeBg'] == rgb('#131519'), probe['badgeBg'])
    record('Body type is 14px (body-sm working size)', probe['bodySize'] == '14px', probe['bodySize'])
    record('Inter is the loaded family', 'Inter' in probe['fontFamily'], probe['fontFamily'])

    fonts = page.evaluate("""() => ({
      inter: document.fonts.check("16px Inter"),
      mono: document.fonts.check("12px 'JetBrains Mono'"),
    })""")
    record('Inter actually loaded', fonts['inter'], str(fonts['inter']))
    record('JetBrains Mono actually loaded', fonts['mono'], str(fonts['mono']))

    # A rejected/verdict surface must use the danger hue; accepted uses success green.
    navigate(page, 'Console', 350)
    page.click('.quick-actions button:has-text("Tamper")')
    page.wait_for_timeout(400)
    page.click('.submit-btn')
    page.wait_for_timeout(1000)
    verdict = page.evaluate("""() => {
      const b = document.querySelector('.verdict-banner');
      if (!b) return null;
      const cs = getComputedStyle(b);
      return {bg: cs.backgroundColor, border: cs.borderTopColor, text: b.textContent.slice(0,60)};
    }""")
    if verdict:
        record('Rejected verdict uses danger tint', 'rgba(229, 72, 77' in verdict['bg'],
               f"{verdict['bg']} / {verdict['text'].strip()[:34]}")
        record('Rejected verdict border is danger', 'rgba(229, 72, 77' in verdict['border'], verdict['border'])


if __name__ == '__main__':
    sys.exit(main())
