import React from 'react';
import {Activity,ShieldCheck,ShieldX,RotateCcw,Fingerprint,LockKeyhole,FlaskConical,AlertTriangle,BarChart3} from 'lucide-react';
import type {Metrics,AnomalyReport} from '../types';
import {Badge} from './ui';

const STAGE_LABELS:Record<string,string>={
 structure:'Structure',identity:'Identity',authentication:'Authentication',payload:'Payload',
 time:'Freshness',permissions:'Authorization',replay:'Replay',commit:'Commit'};

/** Security Metrics Dashboard (roadmap feature 13).
 * Every number is fetched from GET /api/metrics, which computes it from persisted
 * audit records. Nothing on this screen is hardcoded, and live-session counters are
 * kept structurally separate from isolated scenario-suite counters.
 */
export function MetricsDashboard({metrics,anomalies,loading}:{metrics:Metrics|null;anomalies:AnomalyReport|null;loading:boolean}){
 if(loading&&!metrics)return <section className="panel metrics-panel"><div className="panel-heading"><div className="panel-title"><BarChart3 size={17}/><h2>Security metrics</h2></div></div><div className="metrics-empty"><Activity size={22} strokeWidth={1}/><p>Loading metrics from persisted records…</p></div></section>;
 if(!metrics)return <section className="panel metrics-panel"><div className="panel-heading"><div className="panel-title"><BarChart3 size={17}/><h2>Security metrics</h2></div></div><div className="metrics-empty"><AlertTriangle size={22} strokeWidth={1}/><p>Metrics are unavailable. The local API may be offline.</p></div></section>;
 const live=metrics.live,suite=metrics.scenario_suites;
 const maxReason=Math.max(1,...Object.values(live.reason_code_breakdown));
 const maxStage=Math.max(1,...Object.values(live.first_failed_stages));
 return <section className="panel metrics-panel" aria-label="Security metrics">
  <div className="panel-heading"><div className="panel-title"><BarChart3 size={17}/><h2>Security metrics</h2></div><span className="workstation-label">{metrics.scope}</span></div>
  <p className="metrics-note">Computed from persisted audit records in session <code>{metrics.session_id}</code>. No value on this screen is hardcoded.</p>
  <div className="metric-cards">
   <MetricCard icon={<Activity size={15}/>} label="Messages checked" value={live.messages_checked}/>
   <MetricCard icon={<ShieldCheck size={15}/>} label="Accepted" value={live.accepted} tone="green"/>
   <MetricCard icon={<ShieldX size={15}/>} label="Rejected" value={live.rejected} tone="red"/>
   <MetricCard icon={<RotateCcw size={15}/>} label="Replay attempts" value={live.replay_attempts_detected} tone="amber"/>
   <MetricCard icon={<Fingerprint size={15}/>} label="Auth failures" value={live.authentication_failures} tone="red"/>
   <MetricCard icon={<LockKeyhole size={15}/>} label="Authorization denials" value={live.authorisation_denials} tone="red"/>
  </div>
  <div className="metrics-columns">
   <div className="metric-block">
    <h3>Rejection reasons</h3>
    {Object.keys(live.rejection_reasons).length
     ?Object.entries(live.rejection_reasons).sort((a,b)=>b[1]-a[1]).map(([reason,count])=><div key={reason} className="bar-row"><span className="bar-label mono">{reason}</span><span className="bar-track"><span className="bar-fill red" style={{width:(count/maxReason*100)+'%'}}/></span><span className="bar-value">{count}</span></div>)
     :<p className="metric-none">No rejections recorded in this session yet.</p>}
   </div>
   <div className="metric-block">
    <h3>First failed validation stage</h3>
    {Object.keys(live.first_failed_stages).length
     ?Object.entries(live.first_failed_stages).sort((a,b)=>b[1]-a[1]).map(([stage,count])=><div key={stage} className="bar-row"><span className="bar-label">{STAGE_LABELS[stage]??stage}</span><span className="bar-track"><span className="bar-fill amber" style={{width:(count/maxStage*100)+'%'}}/></span><span className="bar-value">{count}</span></div>)
     :<p className="metric-none">No stage has failed in this session yet.</p>}
   </div>
  </div>
  <div className="metrics-columns">
   <div className="metric-block">
    <h3>Reason-code breakdown</h3>
    <div className="code-grid">{Object.entries(live.reason_code_breakdown).sort((a,b)=>b[1]-a[1]).map(([code,count])=><div key={code} className={code==='OK'?'ok':''}><code>{code}</code><span>{count}</span></div>)}</div>
    {live.acceptance_rate!=null&&<p className="metric-rate">Acceptance rate <strong>{(live.acceptance_rate*100).toFixed(1)}%</strong></p>}
   </div>
   <div className="metric-block">
    <h3><FlaskConical size={13}/> Isolated scenario suites</h3>
    <p className="metric-note">Runs in an isolated session with an injected clock. Never mixed into the live counters above.</p>
    <div className="metric-cards compact">
     <MetricCard label="Suite runs" value={suite.runs}/>
     <MetricCard label="Cases executed" value={suite.cases_executed}/>
     <MetricCard label="Cases passed" value={suite.cases_passed} tone="green"/>
     <MetricCard label="Cases failed" value={suite.cases_failed} tone={suite.cases_failed?'red':'green'}/>
    </div>
    <div className="integrity-flag"><span>Protected-state integrity violations reported by tests</span><Badge tone={suite.protected_state_integrity_violations?'red':'green'}>{suite.protected_state_integrity_violations}</Badge></div>
   </div>
  </div>
  {anomalies&&<div className="metric-block anomaly-block">
   <h3><AlertTriangle size={13}/> Synthetic telemetry anomalies</h3>
   <p className="metric-note">{anomalies.disclaimer}</p>
   {anomalies.finding_count
    ?<div className="anomaly-list">{anomalies.findings.map((f,i)=><div key={i} className="anomaly-row"><Badge tone="amber">{f.rule}</Badge><span>{f.detail}</span><code>{f.event_id?f.event_id.slice(0,8)+'…':'—'}</code></div>)}</div>
    :<p className="metric-none">No anomaly rules fired on the accepted telemetry in this session.</p>}
  </div>}
 </section>;
}

function MetricCard({icon,label,value,tone='neutral'}:{icon?:React.ReactNode;label:string;value:number;tone?:string}){
 return <div className={'metric-card '+tone}>{icon&&<span className="metric-icon">{icon}</span>}<span className="metric-label">{label}</span><strong className="metric-value">{value}</strong></div>;
}
