import React,{useState} from 'react';
import {ArrowRight,Check,X,FileDiff,Shield,Database,Download} from 'lucide-react';
import type {Decision} from '../types';
import {Badge,fmtTime} from './ui';

interface Side {label:string;result:Decision|null;raw:string}

const KEYS=['version','message_id','message_type','sender_id','target_id','key_id','sequence','issued_at','expires_at','action','payload','auth_tag'] as const;

function diffFields(a:Decision|null,b:Decision|null){
 if(!a?.message||!b?.message)return [] as string[];
 const out:string[]=[];
 for(const key of KEYS){
  const av=JSON.stringify((a.message as Record<string,unknown>)[key]??null);
  const bv=JSON.stringify((b.message as Record<string,unknown>)[key]??null);
  if(av!==bv)out.push(key);
 }
 return out;
}

/** Normal vs Attack Comparison (roadmap feature 12).
 * Grounded in two real submitted messages and their real receiver decisions.
 * No verdict is predicted; both columns come from the Python receiver.
 */
export function ComparisonView({normal,attack}:{normal:Side;attack:Side}){
 const [tab,setTab]=useState<'fields'|'raw'>('fields');
 const changed=diffFields(normal.result,attack.result);
 const ready=!!normal.result&&!!attack.result;
 return <section className="panel compare-panel" aria-label="Normal versus attack comparison">
  <div className="panel-heading"><div className="panel-title"><FileDiff size={17}/><h2>Normal vs attack</h2></div><span className="workstation-label">{changed.length} field{changed.length===1?'':'s'} differ</span></div>
  <p className="compare-note">Both columns are real submissions with real receiver decisions. Nothing here is predicted.</p>
  <div className="compare-grid">
   {[normal,attack].map(side=>(
    <div key={side.label} className={'compare-col '+(side.result?.verdict==='ACCEPTED'?'accepted':side.result?'rejected':'')}>
     <div className="compare-col-head"><span className="tiny-caps">{side.label}</span>{side.result?<Badge tone={side.result.verdict==='ACCEPTED'?'green':'red'}>{side.result.verdict}</Badge>:<span className="compare-pending">Awaiting submission</span>}</div>
     {side.result?<>
      <div className="compare-verdict"><span>REASON</span><code>{side.result.reason_code}</code></div>
      <p className="compare-explanation">{side.result.explanation}</p>
      <div className="compare-meta">
       <div><span>Sender verified</span><strong className={side.result.sender_verified?'green':'red'}>{side.result.sender_verified?'Yes':'No'}</strong></div>
       <div><span>State changed</span><strong className={side.result.state_changed?'amber':'green'}>{side.result.state_changed?'Yes':'No'}</strong></div>
       <div><span>Replay advanced</span><strong>{side.result.replay_state_advanced?'Yes':'No'}</strong></div>
       <div><span>Audit</span><strong>{side.result.event_id?'Persisted':'Not persisted'}</strong></div>
      </div>
      <div className="compare-state"><span>PROTECTED STATE · BEFORE</span><pre>{JSON.stringify(side.result.protected_state_before,null,1)}</pre><ArrowRight size={13}/><span>AFTER</span><pre>{JSON.stringify(side.result.protected_state_after,null,1)}</pre></div>
      {side.result.checks&&<div className="compare-stages">{side.result.checks.map(c=><div key={c.stage} className={c.status==='PASS'?'pass':c.status==='FAIL'?'fail':'notrun'}><span>{c.status==='PASS'?<Check size={11}/>:c.status==='FAIL'?<X size={11}/>:'—'}</span><em>{c.label}</em></div>)}</div>}
      <div className="compare-event"><Database size={12}/><code>{side.result.event_id??'—'}</code>{side.result.received_at&&<span>{fmtTime(side.result.received_at)}</span>}</div>
     </>:<div className="compare-empty"><Shield size={22} strokeWidth={1}/><p>Generate and submit this side to populate the comparison.</p></div>}
    </div>
   ))}
  </div>
  {ready&&<>
   <div className="compare-tabs"><button aria-pressed={tab==='fields'} className={tab==='fields'?'selected':''} onClick={()=>setTab('fields')}>Changed fields</button><button aria-pressed={tab==='raw'} className={tab==='raw'?'selected':''} onClick={()=>setTab('raw')}>Raw bytes</button></div>
   {tab==='fields'
    ?<div className="compare-diff">{changed.length?changed.map(k=><div key={k} className="diff-row"><code>{k}</code><span>{JSON.stringify((normal.result!.message as Record<string,unknown>)[k]??null)}</span><ArrowRight size={12}/><span className="diff-after">{JSON.stringify((attack.result!.message as Record<string,unknown>)[k]??null)}</span></div>):<p className="compare-none">The submitted messages are byte-identical, so no field differs.</p>}</div>
    :<div className="compare-raw"><div><span>NORMAL · SUBMITTED BYTES</span><pre>{normal.result!.submitted_text??'Not retained for this decision'}</pre></div><div><span>ATTACK · SUBMITTED BYTES</span><pre>{attack.result!.submitted_text??'Not retained for this decision'}</pre></div></div>}
   <div className="compare-foot">
    <p><Shield size={12}/>First failure — normal: <strong>{normal.result!.checks?.find(c=>c.status==='FAIL')?.label??'none'}</strong> · attack: <strong>{attack.result!.checks?.find(c=>c.status==='FAIL')?.label??'none'}</strong></p>
    <button className="btn secondary" onClick={()=>downloadComparison(normal,attack,changed)}><Download size={13}/>Export comparison</button>
   </div>
  </>}
 </section>;
}

function downloadComparison(normal:Side,attack:Side,changed:string[]){
 const payload={label:'Synthetic comparison — local simulation only. Not tamper-proof.',generated_at:new Date().toISOString(),
  changed_fields:changed,
  normal:{scenario:normal.label,decision:normal.result,submitted_text:normal.result?.submitted_text??null},
  attack:{scenario:attack.label,decision:attack.result,submitted_text:attack.result?.submitted_text??null}};
 const url=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}));
 const a=document.createElement('a');a.href=url;a.download='kavach-comparison.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
