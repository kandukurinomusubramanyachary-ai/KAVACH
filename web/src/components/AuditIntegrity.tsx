import React,{useState} from 'react';
import {Link2,ShieldCheck,ShieldAlert,RefreshCw,Info,FileWarning} from 'lucide-react';
import type {AuditChainReport} from '../types';
import {Badge} from './ui';

/** Tamper-Evident Audit Evidence (roadmap feature 9).
 * Verification is strictly read-only: it never repairs, rewrites, or deletes a record.
 * Limitations are shown alongside the result rather than omitted.
 */
export function AuditIntegrity({report,onVerify,busy,error}:{report:AuditChainReport|null;onVerify:()=>void;busy:boolean;error:string}){
 const [open,setOpen]=useState(false);
 const verified=report?.status==='VERIFIED';
 return <section className="panel integrity-panel" aria-label="Audit integrity">
  <div className="panel-heading"><div className="panel-title"><Link2 size={17}/><h2>Audit integrity</h2></div><button className="btn secondary" onClick={onVerify} disabled={busy}>{busy?<RefreshCw size={13} className="spin"/>:<ShieldCheck size={13}/>} {busy?'Verifying…':'Verify chain'}</button></div>
  {error&&<p className="inline-error" role="alert">{error}</p>}
  {!report&&<div className="integrity-empty"><Link2 size={22} strokeWidth={1}/><p>Verify the hash-linked audit log to check whether any covered record was altered after commit.</p></div>}
  {report&&<>
   <div className={'integrity-result '+(verified?'verified':'failed')} role="status">
    {verified?<ShieldCheck size={19}/>:<ShieldAlert size={19}/>}
    <div><strong>{verified?'Chain verified':'Integrity check failed'}</strong><span>{report.links_checked} linked record{report.links_checked===1?'':'s'} checked{report.uncovered_records?` · ${report.uncovered_records} uncovered`:''}</span></div>
    <Badge tone={verified?'green':'red'}>{report.status}</Badge>
   </div>
   {report.uncovered_records>0&&<p className="integrity-uncovered"><Info size={12}/><span>{report.uncovered_note}</span></p>}
   {report.problems.length>0&&<div className="integrity-problems">
    <h4><FileWarning size={13}/> Detected problems</h4>
    {report.problems.map((p,i)=><div key={i} className="integrity-problem"><Badge tone="red">{p.kind}</Badge><span>{p.detail}</span>{p.link&&<code>link {p.link}</code>}</div>)}
   </div>}
   <div className="integrity-covered">
    <h4>Covered fields</h4>
    <div className="code-grid">{report.covered_fields.map(f=><div key={f}><code>{f}</code></div>)}</div>
    <p className="integrity-covered-note">Fields outside this list are not covered by the chain.</p>
   </div>
   <button className="text-btn" onClick={()=>setOpen(o=>!o)}>{open?'Hide':'Show'} limitations<Info size={12}/></button>
   {open&&<><ul className="integrity-limitations">{report.limitations.map((l,i)=><li key={i}>{l}</li>)}</ul>
    <p className="integrity-disclaimer">A hash chain detects modification of covered records and broken links. It does not prove origin and does not prevent an attacker with write access from rewriting the entire chain from genesis. It is not tamper-proof.</p></>}
  </>}
 </section>;
}
