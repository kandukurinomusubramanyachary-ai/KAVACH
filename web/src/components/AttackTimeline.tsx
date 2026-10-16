import React from 'react';
import {Inbox,Code2,Fingerprint,LockKeyhole,SlidersHorizontal,Clock3,Shield,RotateCcw,CheckCheck,Check,X,CircleDot,Database,FileText} from 'lucide-react';
import type {Decision,ValidationCheck} from '../types';
import {fmtTime} from './ui';

const NODES=[
 {key:'received',label:'Message received',detail:'Exact editor bytes delivered to the Python receiver',Icon:Inbox},
 {key:'structure',label:'Structure check',detail:'Strict JSON, exact envelope, types, size',Icon:Code2},
 {key:'identity',label:'Identity',detail:'Registered key matches the claimed sender',Icon:Fingerprint},
 {key:'authentication',label:'Authentication',detail:'HMAC-SHA256, constant-time comparison',Icon:LockKeyhole},
 {key:'payload',label:'Payload',detail:'Target, action, and value bounds',Icon:SlidersHorizontal},
 {key:'time',label:'Freshness',detail:'Lifetime and permitted clock skew',Icon:Clock3},
 {key:'permissions',label:'Authorization',detail:'Receiver policy permits the action',Icon:Shield},
 {key:'replay',label:'Replay',detail:'New message ID and strictly increasing sequence',Icon:RotateCcw},
 {key:'commit',label:'Commit / rejection',detail:'Atomic state, replay, and audit — or nothing',Icon:CheckCheck},
 {key:'audit',label:'Audit evidence',detail:'Persisted decision with a chained integrity link',Icon:Database},
] as const;

/** Attack Replay Timeline (roadmap feature 11).
 *
 * A LOGICAL sequence, not a measured one. The backend reports a single end-to-end
 * duration for the whole decision; it does not time individual stages, so no
 * per-stage duration is shown or implied. Stages that never ran display NOT RUN,
 * never PASS.
 */
export function AttackTimeline({result}:{result:Decision|null}){
 if(!result)return <div className="timeline-empty"><CircleDot size={15}/><p>Submit a message to walk the receiver's ordered checks.</p></div>;
 const checks=result.checks??[];
 const statusFor=(key:string):'PASS'|'FAIL'|'NOT_RUN'|'PENDING'=>key==='received'?'PASS':key==='audit'?(result.audit_persisted===true?'PASS':'NOT_RUN'):(checks.find(c=>c.stage===key)?.status as 'PASS'|'FAIL'|'NOT_RUN')??'NOT_RUN';
 const passed=checks.filter(c=>c.status==='PASS').length;
 const rejected=result.verdict==='REJECTED';
 return <section className="panel timeline-panel" aria-label="Attack replay timeline">
  <div className="panel-heading"><div className="panel-title"><FileText size={17}/><h2>Attack replay timeline</h2></div><span className="workstation-label">{result.verdict==='ACCEPTED'?'Accepted':rejected?'Rejected':'Service unavailable'}</span></div>
  <p className="timeline-note">Logical order only. The receiver does not time individual stages, so no per-stage duration is shown. Stages that never ran read NOT RUN, not PASS.</p>
  <ol className="timeline">
   {NODES.map((node,index)=>{
    const status=statusFor(node.key);
    const check=checks.find(c=>c.stage===node.key);
    const tone=status==='PASS'?'pass':status==='FAIL'?'fail':'notrun';
    return <li key={node.key} className={'timeline-node '+tone}>
     <span className="timeline-rail"><span className="timeline-dot">{status==='PASS'?<Check size={12}/>:status==='FAIL'?<X size={12}/>:<CircleDot size={12}/>}</span>{index<NODES.length-1&&<span className="timeline-line"/>}</span>
     <div className="timeline-body">
      <div className="timeline-title"><node.Icon size={14}/><strong>{node.label}</strong><span className={'timeline-status '+tone}>{status==='NOT_RUN'?'NOT RUN':status==='PENDING'?'PENDING':status}</span></div>
      <p>{check?.explanation??node.detail}</p>
      {node.key==='received'&&result.received_at&&<span className="timeline-meta mono">{fmtTime(result.received_at)} · input {result.input_sha256?result.input_sha256.slice(0,12)+'…':'unavailable'}</span>}
      {node.key==='audit'&&<span className="timeline-meta mono">{result.event_id?<>event {result.event_id.slice(0,8)}… · {result.audit_persisted?'persisted':'not persisted'}</>:'No audit record persisted — service failure'}</span>}
     </div>
    </li>;
   })}
  </ol>
  <div className="timeline-summary">
   <div><span>STAGES PASSED</span><strong>{passed} / 8</strong></div>
   <div><span>FIRST FAILURE</span><strong>{checks.find(c=>c.status==='FAIL')?.label??'None'}</strong></div>
   <div><span>END-TO-END</span><strong>{result.duration_ms!=null?`${result.duration_ms} ms`:'Unavailable'}</strong></div>
   <div><span>VERDICT</span><strong className={result.verdict==='ACCEPTED'?'green':'red'}>{result.verdict}</strong></div>
  </div>
  <p className="timeline-disclaimer">End-to-end duration is the receiver's own measurement for the whole decision. Individual stage timings are not measured and are not shown.</p>
 </section>;
}
