import React from 'react';
import {AlertTriangle,Crosshair,FileDiff,ArrowRight,CheckCircle2,Shield} from 'lucide-react';
import type {Decision} from '../types';
import {Badge} from './ui';

export interface ScenarioMeta {
 id:string;name:string;desc:string;expected:string;tone:string;
 intent:string;threat:string;changed:string;
}

/** Threat Explanation Panel (roadmap feature 17).
 * Grounded in the selected scenario preset and the observed receiver decision.
 * Never predicts an outcome: the observed column only appears after a real submission. */
export function ThreatPanel({scenario,result,expectation}:{scenario:ScenarioMeta|null;result:Decision|null;expectation?:string|null}){
 if(!scenario)return null;
 const observed=result?result.reason_code:null;
 const changedState=result?result.state_changed:null;
 return <section className="panel threat-panel" aria-label="Threat explanation">
  <div className="panel-heading"><div className="panel-title"><Crosshair size={17}/><h2>Threat explanation</h2></div><span className="workstation-label">{scenario.name}</span></div>
  <dl className="threat-facts">
   <div><dt><Crosshair size={12}/>Attack intent</dt><dd>{scenario.intent}</dd></div>
   <div><dt><FileDiff size={12}/>What is changed</dt><dd>{scenario.changed}</dd></div>
   <div><dt><AlertTriangle size={12}/>Why it matters</dt><dd>{scenario.threat}</dd></div>
  </dl>
  <div className="threat-outcomes">
   <div className="threat-outcome"><span>EXPECTED</span><Badge tone={scenario.tone}>{scenario.expected}</Badge></div>
   <ArrowRight size={14} className="threat-arrow"/>
   <div className="threat-outcome"><span>OBSERVED</span>{observed
    ?<Badge tone={result?.verdict==='ACCEPTED'?'green':'red'}>{observed}</Badge>
    :<span className="threat-pending">Submit to observe</span>}</div>
  </div>
  {result&&<div className={'threat-state '+(changedState?'changed':'')}>
   {changedState?<AlertTriangle size={13}/>:<Shield size={13}/>}
   <span>{changedState?'Protected state changed in a committed transaction.':'Protected state unchanged. No execution committed.'}</span>
  </div>}
  {result&&expectation&&<p className="threat-match">{expectation===result.reason_code
   ?<><CheckCircle2 size={12}/>Fixture expectation matched the observed receiver decision.</>
   :<>Fixture expectation <code>{expectation}</code> differed from the observed decision <code>{result.reason_code}</code>. The receiver is authoritative.</>}</p>}
  <p className="threat-disclaimer">Expectations come from the fixture preset, not from the receiver. Only the observed column is a real decision.</p>
 </section>;
}
