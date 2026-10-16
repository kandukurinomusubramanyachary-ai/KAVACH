import React from 'react';
import {Play,ChevronRight,ChevronLeft,RotateCcw,CheckCircle2,Shield,Clock3,Fingerprint,Radio,FileText,BarChart3} from 'lucide-react';
import type {Decision} from '../types';

export interface DemoStep {
 id:string;title:string;goal:string;scenario:string;watch:string;
}

export const DEMO_STEPS:DemoStep[]=[
 {id:'valid',title:'Valid command',goal:'A correctly signed, authorised operator command changes the simulated mode.',scenario:'valid',watch:'All eight stages PASS. Protected mode moves to POWER_SAVING. An audit record is persisted.'},
 {id:'replay',title:'Replay attempt',goal:'Resend the exact accepted bytes and watch the receiver refuse them.',scenario:'replay',watch:'Structure, identity, authentication and freshness all PASS. Replay is the stage that fails — REPLAY.'},
 {id:'tamper',title:'Payload tampering',goal:'Alter the payload after signing, without generating a new signature.',scenario:'tampered',watch:'Authentication fails. Every later stage reads NOT RUN, and protected state does not move.'},
 {id:'unauthorised',title:'Authenticated but unauthorised',goal:'A correctly authenticated observer tries to change spacecraft mode.',scenario:'unauthorised',watch:'Authentication PASSES and authorisation FAILS. HMAC PASS is not permission.'},
 {id:'compare',title:'Protected-state comparison',goal:'Compare the accepted run against a rejected one side by side.',scenario:'valid',watch:'Only the accepted request produced a committed state transition.'},
 {id:'evidence',title:'Audit evidence and tests',goal:'Inspect the persisted record, verify the integrity chain, and read the real suite result.',scenario:'valid',watch:'Every decision has an event ID, and the chain reports whether any covered record was altered.'},
];

/** Guided Demo Mode (roadmap feature 14).
 * Every step is user-triggered: the guide explains and navigates, but the operator
 * presses Generate and Submit. Nothing is submitted silently, and no authentication,
 * authorisation, or freshness check is bypassed to make a step succeed.
 */
export function GuidedDemo({index,result,onNavigate,onRunStep,busy,expected}:{
 index:number;result:Decision|null;onNavigate:(i:number)=>void;onRunStep:(s:DemoStep)=>void;busy:string;expected:string|null;
}){
 const step=DEMO_STEPS[index];
 const last=index===DEMO_STEPS.length-1;
 const observed=result?result.reason_code:null;
 const icons:Record<string,React.ReactNode>={valid:<CheckCircle2 size={16}/>,replay:<RotateCcw size={16}/>,tamper:<Fingerprint size={16}/>,unauthorised:<Shield size={16}/>,compare:<BarChart3 size={16}/>,evidence:<FileText size={16}/>};
 return <section className="panel demo-panel" aria-label="Guided demo">
  <div className="panel-heading"><div className="panel-title"><Play size={17}/><h2>Guided demo</h2></div><span className="workstation-label">Step {index+1} of {DEMO_STEPS.length}</span></div>
  <ol className="demo-steps">
   {DEMO_STEPS.map((s,i)=><li key={s.id} className={i===index?'current':i<index?'done':''}><button onClick={()=>onNavigate(i)}><span className="demo-step-index">{i<index?<CheckCircle2 size={12}/>:i+1}</span><span>{s.title}</span></button></li>)}
  </ol>
  <div className="demo-body">
   <h3>{icons[step.id]}{step.title}</h3>
   <p className="demo-goal">{step.goal}</p>
   <div className="demo-actions">
    <button className="btn secondary" onClick={()=>onRunStep(step)} disabled={!!busy}>{busy==='generate'?<RotateCcw size={14} className="spin"/>:<Play size={14}/>} Generate {step.title.toLowerCase()} fixture</button>
    <span className="demo-hint">Then press <strong>Submit for validation</strong> in the message builder. Nothing is submitted for you.</span>
   </div>
   <div className="demo-expect">
    <div><span>WHAT TO WATCH</span><p>{step.watch}</p></div>
    <div><span>FIXTURE EXPECTATION</span><p><code>{expected??'Generate a fixture to see the preset expectation'}</code></p></div>
    <div><span>OBSERVED</span><p>{observed?<code className={result?.verdict==='ACCEPTED'?'green':'red'}>{observed}</code>:<em>Not submitted yet</em>}</p></div>
   </div>
   {observed&&<p className="demo-note">The observed value comes from the Python receiver. If it differs from the preset expectation, the receiver is authoritative.</p>}
  </div>
  <div className="demo-nav">
   <button className="btn secondary" onClick={()=>onNavigate(Math.max(0,index-1))} disabled={index===0}><ChevronLeft size={14}/>Back</button>
   <span className="demo-clock"><Clock3 size={12}/> Fixtures expire after 60 seconds — regenerate if a step stalls.</span>
   {last
    ?<button className="btn primary" onClick={()=>onNavigate(0)}><RotateCcw size={14}/>Restart walkthrough</button>
    :<button className="btn primary" onClick={()=>onNavigate(index+1)}>Next step<ChevronRight size={14}/></button>}
  </div>
  <p className="demo-disclaimer"><Radio size={11}/> Synthetic local simulation. No live command channel, and no check is bypassed to make a step succeed.</p>
 </section>;
}
