"""Real Chromium UX and six-step judge journey, with disposable server/runtime."""
import csv
import io
import json
from pathlib import Path
import sys
import time
from playwright.sync_api import sync_playwright, expect
from _isolated_server import isolated_server
expect.set_options(timeout=15000)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'reports/final'
OUT.mkdir(parents=True, exist_ok=True)
CHECKS = []


def record(name, condition=True):
    CHECKS.append({'name': name, 'passed': bool(condition)})
    assert condition, name


def navigate(page, name):
    if page.locator('.nav-toggle').is_visible() and not page.locator('nav.open').count():
        page.get_by_role('button', name='Toggle navigation', exact=True).click()
    page.get_by_role('button', name=name, exact=True).click()


def main():
    errors = []
    started = time.perf_counter()
    with isolated_server() as base, sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={'width':1440,'height':1000},
                                      permissions=['clipboard-read','clipboard-write'])
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(base)
        expect(page.locator('.submit-btn')).to_be_enabled()
        # A fresh namespace makes the valid state transition independently observable.
        draft_before_reset=page.get_by_label('Editable message JSON').input_value()
        page.get_by_role('button', name='Reset', exact=True).click()
        expect(page.get_by_role('dialog', name='Reset demo')).to_be_visible()
        page.get_by_role('button', name='Keep current session', exact=True).click()
        record('Reset requires confirmation; cancel preserves draft', page.get_by_label('Editable message JSON').input_value()==draft_before_reset)
        page.get_by_role('button', name='Reset', exact=True).click()
        page.get_by_role('button', name='Reset demo', exact=True).click()
        expect(page.get_by_role('dialog')).to_have_count(0)
        navigate(page, 'Demo')
        demo_started = time.perf_counter()
        decisions = []
        for index, expected in enumerate(['OK','REPLAY','AUTH_FAILED','NOT_AUTHORISED']):
            if index:
                page.get_by_role('button', name='Next step', exact=True).click()
            page.locator('.demo-actions button').first.click()
            expect(page.get_by_role('heading', name='Mission Console', exact=True)).to_be_visible()
            expect(page.locator('.submit-btn')).to_be_enabled()
            with page.expect_response(lambda r:'/api/messages?' in r.url and r.request.method=='POST') as response:
                page.locator('.submit-btn').click()
            decision = response.value.json()
            decisions.append(decision)
            record('Guided step '+str(index+1)+' actual receiver '+expected, decision['reason_code']==expected)
            if index==0:
                record('Guide accepts operator SET_MODE after reset with eight passes',
                       decision['state_changed'] and all(c['status']=='PASS' for c in decision['checks'])
                       and decision['message']['sender_id']=='operator-01')
            else:
                record('Guided rejection preserves all protected domains '+expected,
                       decision['protected_state_before']==decision['protected_state_after']
                       and decision['telemetry_before']==decision['telemetry_after']
                       and not decision['replay_state_advanced'])
            page.get_by_role('button', name='Return to guided demo', exact=True).click()
            expect(page.locator('.demo-expect')).to_contain_text(expected)
        page.get_by_role('button', name='Next step', exact=True).click()
        page.get_by_role('button', name='Open captured comparison').click()
        expect(page.locator('.compare-col.accepted')).to_have_count(1)
        expect(page.locator('.compare-col.rejected')).to_have_count(1)
        page.screenshot(path=str(OUT/'ux-comparison.png'), full_page=True)
        record('Guide step 5 comparison retains two actual decisions')
        navigate(page,'Demo')
        page.get_by_role('button', name='Next step', exact=True).click()
        page.get_by_role('button', name='Verify audit chain', exact=True).click()
        expect(page.locator('.demo-expect')).to_contain_text('VERIFIED')
        live_before = page.request.get(base+'/api/metrics').json()['live']
        page.get_by_role('button', name='Run security suite', exact=True).click()
        expect(page.locator('.demo-expect')).to_contain_text('31/31', timeout=30000)
        live_after = page.request.get(base+'/api/metrics').json()['live']
        record('Guide step 6 real 31-case suite and chain; live metrics unpolluted', live_before==live_after)
        record('Guided completion reflects actual outcomes', page.locator('.demo-steps li.done').count()==6)
        demo_seconds = round(time.perf_counter()-demo_started,2)
        page.screenshot(path=str(OUT/'ux-guide-completed.png'),full_page=True)

        navigate(page,'Audit')
        search=page.get_by_label('Search audit events',exact=True)
        for needle,count in [(decisions[0]['event_id'],1), (decisions[0]['message']['message_id'],2), ('NOT_AUTHORISED',1)]:
            search.fill(needle)
            expect(page.locator('.audit-table tbody tr')).to_have_count(count)
            record('Audit search finds '+('reason' if needle=='NOT_AUTHORISED' else 'actual identifier'))
        page.locator('.audit-table tbody tr').first.click()
        expect(page.get_by_role('dialog',name='Validation decision')).to_be_visible()
        for label in ['event ID','session ID','message ID','input hash','rejection code']:
            page.get_by_role('button',name='Copy '+label,exact=True).click()
            expect(page.get_by_role('button',name='Copy '+label,exact=True).locator('..').locator('[role=status]')).to_contain_text('Copied '+label)
        record('Evidence IDs, hash and rejection code copy with feedback')
        page.emulate_media(media='print')
        record('Print decision hides navigation/background and expands evidence',
               not page.locator('.topbar').is_visible() and not page.locator('main').is_visible()
               and page.get_by_role('dialog').is_visible()
               and page.locator('.detail-modal').evaluate('(e)=>getComputedStyle(e).maxHeight')=='none')
        page.emulate_media(media='screen')
        page.keyboard.press('Escape')
        search.fill('')
        expect(page.locator('.audit-table tbody tr')).to_have_count(4)
        # Generate >200 real records through the receiver to prove export is not truncated.
        for _ in range(202):
            response=page.request.post(base+'/api/messages', data='{}', headers={'Content-Type':'application/json'})
            assert response.json()['reason_code']=='SCHEMA_INVALID'
        page.get_by_role('button',name='Refresh audit',exact=True).click()
        expect(page.locator('.pagination')).to_contain_text('206 decisions')
        with page.expect_download() as download:
            page.get_by_role('button',name='Export CSV',exact=True).click()
        rows=list(csv.reader(io.StringIO(Path(download.value.path()).read_text(encoding='utf-8'))))
        record('CSV exports all 206 real records across API pages',len(rows)==207 and len(rows[0])==14)
        # The empty future interval must also constrain CSV, not only the table.
        page.locator('#since').fill('2099-01-01T00:00')
        expect(page.locator('.audit-table tbody tr')).to_have_count(0)
        record('Audit date filtering is real and empty CSV cannot be requested',not page.get_by_role('button',name='Export CSV',exact=True).is_enabled())
        page.locator('#since').fill('')
        search.fill('NOT_AUTHORISED')
        expect(page.locator('.audit-table tbody tr')).to_have_count(1)
        with page.expect_download() as download:
            page.get_by_role('button',name='Export CSV',exact=True).click()
        rows=list(csv.reader(io.StringIO(Path(download.value.path()).read_text(encoding='utf-8'))))
        record('Filtered CSV uses the same actual search results',len(rows)==2 and rows[1][4]=='NOT_AUTHORISED')
        with page.expect_download() as download:
            page.get_by_role('button',name='Export JSON',exact=True).click()
        evidence=json.loads(Path(download.value.path()).read_text(encoding='utf-8'))
        record('JSON contains actual records and verified chain',len(evidence['events'])==206 and evidence['audit_chain']['status']=='VERIFIED')
        page.route('**/api/export?*',lambda route:route.abort())
        page.get_by_role('button',name='Export JSON',exact=True).click()
        expect(page.locator('.toast')).to_contain_text('JSON export failed')
        page.unroute('**/api/export?*')
        record('Failed evidence download reports error and restores control')

        navigate(page,'Scenarios')
        page.get_by_label('Search scenarios').fill('Replay attack')
        expect(page.locator('.scenario-card')).to_have_count(1)
        record('Scenario search filters actual preset metadata')
        page.get_by_label('Search scenarios').fill('')
        expect(page.locator('.scenario-card')).to_have_count(11)
        page.get_by_title('About this simulator').click()
        page.get_by_label('Search help').fill('HMAC')
        page.locator('.help-faq summary').first.click()
        expect(page.locator('.help-faq details[open]')).to_be_visible()
        for _ in range(20):
            page.keyboard.press('Tab')
            assert page.evaluate('document.activeElement.closest("[role=dialog]")!==null')
        record('Searchable expandable FAQ includes native keyboard controls and focus containment')
        page.keyboard.press('Escape')
        expect(page.get_by_title('About this simulator')).to_be_focused()

        navigate(page,'Console')
        page.get_by_role('button',name='Generate fresh signed sample',exact=True).click()
        expect(page.locator('.submit-btn')).to_be_enabled()
        draft=page.get_by_label('Editable message JSON').input_value()
        page.route('**/api/messages?*',lambda route:route.abort())
        page.locator('.submit-btn').click()
        expect(page.locator('[role=alert]').first).to_contain_text('unavailable')
        record('Failed submission preserves exact editor text',page.get_by_label('Editable message JSON').input_value()==draft)
        page.unroute('**/api/messages?*')
        page.locator('#sender').select_option('operator-01')
        page.locator('#action').select_option('GET_STATUS')
        page.get_by_role('button',name='Generate fresh signed sample',exact=True).click()
        expect(page.locator('.submit-btn')).to_be_enabled()
        with page.expect_response(lambda r:'/api/messages?' in r.url and r.request.method=='POST') as response:
            page.locator('.submit-btn').click()
        status=response.value.json()
        record('GET_STATUS acceptance is distinct from protected-state change',status['reason_code']=='OK' and not status['state_changed'] and status['replay_state_advanced'])
        expect(page.locator('.threat-state')).to_contain_text('Command accepted; protected state unchanged.')
        record('Pipeline rows and highlighted editor match the actual DOM',page.evaluate("""() => {
          const pre=document.querySelector('.syntax-viewport pre').getBoundingClientRect();
          const input=document.querySelector('.syntax-viewport textarea').getBoundingClientRect();
          return Math.abs(pre.width-input.width)<1 && Math.abs(pre.height-input.height)<1 &&
            getComputedStyle(document.querySelector('.pipeline-step summary')).display==='flex' &&
            getComputedStyle(document.querySelector('.line-numbers span')).display==='block';
        }"""))
        # Default and persisted light theme; capture each shipped view in light.
        record('Default theme is dark',page.evaluate('document.documentElement.dataset.theme')=='dark')
        page.screenshot(path=str(OUT/'ux-console-dark.png'),full_page=True)
        page.get_by_role('button',name='Light theme',exact=True).click()
        expect(page.get_by_role('button',name='Light theme',exact=True)).to_have_attribute('aria-pressed','true')
        page.reload()
        expect(page.locator('.submit-btn')).to_be_enabled()
        record('Light theme persists across reload',page.evaluate('document.documentElement.dataset.theme')=='light')
        for name in ['Console','Demo','Scenarios','Timeline','Compare','Metrics','Audit','Policy']:
            navigate(page,name)
            record('Light '+name+' layout fits',not page.evaluate('document.documentElement.scrollWidth>innerWidth'))
            page.screenshot(path=str(OUT/('ux-light-'+name.lower()+'.png')),full_page=True)
        for width in [1440,1024,768,390,320]:
            page.set_viewport_size({'width':width,'height':900})
            navigate(page,'Console')
            record('Light reflow '+str(width),not page.evaluate('document.documentElement.scrollWidth>innerWidth'))
        page.get_by_role('button',name='Toggle navigation',exact=True).click()
        expect(page.locator('nav [aria-current=page]')).to_be_focused()
        page.keyboard.press('Escape')
        expect(page.get_by_role('button',name='Toggle navigation',exact=True)).to_be_focused()
        record('Mobile menu focuses active destination; Escape restores toggle')
        page.evaluate('scrollTo(0,document.body.scrollHeight)')
        page.get_by_role('button',name='Back to top',exact=True).click()
        expect(page.locator('#main-content')).to_be_focused()
        record('Back-to-top targets document scroll and main focus',page.evaluate('scrollY')==0)
        page.get_by_role('link',name='Skip to content',exact=True).focus()
        page.keyboard.press('Enter')
        expect(page.locator('#main-content')).to_be_focused()
        record('Skip link bypasses repeated navigation')
        page.screenshot(path=str(OUT/'ux-mobile-light.png'),full_page=True)
        record('No uncaught browser errors',not errors)
        context.close()
        browser.close()
    return {'status':'PASS','passed':len(CHECKS),'total':len(CHECKS),'checks':CHECKS,
            'guided_demo_automation_seconds':demo_seconds,'duration_seconds':round(time.perf_counter()-started,2),
            'note':'All security decisions are real HTTP responses. Aborted requests exercise transport errors only.'}


if __name__=='__main__':
    try:
        result=main()
    except Exception as exc:
        (OUT/'ux-results.json').write_text(json.dumps({'status':'FAIL','checks':CHECKS,'error':str(exc)},indent=2),encoding='utf-8')
        raise
    (OUT/'ux-results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
