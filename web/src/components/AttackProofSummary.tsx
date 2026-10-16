import React from 'react';
import {ArrowRight,ChevronDown,CheckCircle2,AlertTriangle} from 'lucide-react';
import type {Decision,ProtectedState} from '../types';
const snapshot=(s?:ProtectedState|null)=>s?`${s.mode} / ${s.report_interval_s}s / ${s.antenna_status} / ${s.power_level_pct}%`:'Unavailable';
/** Facts from one receiver response. Never predicts permission or persistence. */
export function AttackProofSummary({result,expectation,onInspect}:{result:Decision;expectation:string|null;onInspect:(d:Decision)=>void}){
 const gates=[['identity','Sender / key match'],['authentication','Message authentication'],['permissions','Action authorisation']] as const;
 const STAGE_LABELS:Record<string,string>={structure:'Message structure',identity:'Sender identity',authentication:'Message authentication',payload:'Payload & target',time:'Timestamp validity',permissions:'Sender permissions',replay:'Replay protection',commit:'State commit'};
 // Which check failed first, taken from the receiver's own ordered checks. Never inferred.
 const failedStage=(result.checks||[]).find(c=>c.status==='FAIL')?.stage ?? result.first_failed_stage ?? null;
 const firstFailed=failedStage?`${STAGE_LABELS[failedStage]??failedStage}`:'None';
 return <section className="attack-summary" aria-label="Attempt proof summary">
  <div className="commit-receipt"><div><span>Protected state</span><strong>{result.protected_state_before&&result.protected_state_after?result.state_changed?'Updated':'Unchanged':'Unavailable'}</strong></div><div><span>Replay advanced</span><strong>{result.replay_state_advanced===true?'Yes':result.replay_state_advanced===false?'No':'Unconfirmed'}</strong></div><div><span>Audit record</span><strong className={result.audit_persisted===true?'green':'amber'}>{result.audit_persisted===true?<><CheckCircle2 size={12}/>Persisted</>:<><AlertTriangle size={12}/>Unconfirmed</>}</strong></div></div>
  <details className="receipt-disclosure"><summary>Attempt proof & identity<ChevronDown size={14}/></summary><div className="receipt-body">
   <p className="receipt-action"><code>{result.message?.action??'Unparseable message'}</code><span>Claimed sender: <code>{result.message?.sender_id??'Unavailable'}</code></span></p>
   <div className="identity-gates">{gates.map(([stage,label])=>{const status=result.checks?.find(c=>c.stage===stage)?.status;return <div key={stage}><span>{label}</span><strong className={status==='PASS'?'green':status==='FAIL'?'red':'muted'}>{status==='PASS'?(stage==='permissions'?'Permitted':'Passed'):status==='FAIL'?(stage==='permissions'?'Denied':'Failed'):'Not evaluated'}</strong></div>})}</div>
   <p className="identity-principle">Authentication confirms message authenticity. Authorisation determines whether the requested action is permitted.</p>
   <dl className="receipt-facts"><div><dt>First failed stage</dt><dd>{firstFailed}</dd></div><div><dt>Fixture expectation</dt><dd>{expectation??'Not specified / edited'}</dd></div><div><dt>Observed result</dt><dd>{result.verdict==='ACCEPTED'?'ACCEPTED':result.reason_code}</dd></div><div><dt>Protected state</dt><dd>{snapshot(result.protected_state_before)}<ArrowRight size={12}/>{snapshot(result.protected_state_after)}</dd></div><div><dt>Replay sequence</dt><dd>{result.replay_sequence_before??'Unavailable'}<ArrowRight size={12}/>{result.replay_sequence_after??'Unavailable'}</dd></div><div><dt>Session</dt><dd>{result.session_id??'Unavailable'}</dd></div></dl>
   <button className="text-btn" onClick={()=>onInspect(result)}>{result.audit_persisted===true?'Open persisted decision':'Inspect decision'}<ArrowRight size={13}/></button>
  </div></details>
  <span className="sr-only">{result.reason_code} {result.verdict}</span>
 </section>;
}
