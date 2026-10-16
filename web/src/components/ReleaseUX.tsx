import React, {useEffect, useState} from 'react';
import {ArrowUp, Copy, Check, Moon, Sun} from 'lucide-react';

export function ThemeToggle(){
 const [theme,setTheme]=useState(()=>{try{return localStorage.getItem('kavach-theme')==='light'?'light':'dark'}catch{return 'dark'}});
 const [notice,setNotice]=useState('');
 useEffect(()=>{document.documentElement.dataset.theme=theme;try{localStorage.setItem('kavach-theme',theme)}catch{setNotice('Theme changed for this tab. Preference storage is unavailable.')}},[theme]);
 return <><button className="icon-btn theme-toggle" aria-label="Light theme" aria-pressed={theme==='light'} title={theme==='dark'?'Switch to light theme':'Switch to dark theme'} onClick={()=>setTheme(theme==='dark'?'light':'dark')}>{theme==='dark'?<Sun size={17}/>:<Moon size={17}/>}</button><span className="sr-only" role="status">{notice}</span></>;
}

export function CopyValue({value,label}:{value:string|undefined;label:string}){
 const [status,setStatus]=useState('');
 useEffect(()=>{if(!status)return;const timer=setTimeout(()=>setStatus(''),3000);return()=>clearTimeout(timer)},[status]);
 return <span className="copy-value"><button className="icon-btn" disabled={!value} aria-label={'Copy '+label} title={'Copy '+label} onClick={async()=>{try{await navigator.clipboard.writeText(value!);setStatus('Copied '+label)}catch{setStatus('Copy failed. Select the value and use your copy shortcut.')}}}>{status.startsWith('Copied')?<Check size={13}/>:<Copy size={13}/>}</button>{status&&<span role="status" className="copy-feedback">{status}</span>}</span>;
}

export function BackToTop(){
 const [visible,setVisible]=useState(false);
 useEffect(()=>{const update=()=>setVisible(window.scrollY>600);window.addEventListener('scroll',update,{passive:true});update();return()=>window.removeEventListener('scroll',update)},[]);
 return visible?<button className="back-to-top btn secondary" onClick={()=>{window.scrollTo({top:0,behavior:'instant'});document.getElementById('main-content')?.focus({preventScroll:true})}}><ArrowUp size={14}/>Back to top</button>:null;
}

export function UpdatedAt({label,time}:{label:string;time:number|null|undefined}){
 return <span className="updated-at">{label} {time?<time dateTime={new Date(time*1000).toISOString()}>{new Date(time*1000).toLocaleString()}</time>:'not yet available'}</span>;
}

const FAQ=[
 ['HMAC authentication','HMAC-SHA256 authenticates the signed envelope with a shared secret. It provides integrity, not encryption. Signing keys stay on the local server. A valid tag does not grant permission.'],
 ['Replay attacks','A replay resends accepted bytes. The receiver remembers accepted message IDs and strictly increasing sequences per session and sender stream. Expiration is checked before replay, so stale messages return EXPIRED.'],
 ['Tampering','Changing a signed field without signing again invalidates the authentication tag. The Tamper fixture does exactly this; formatting changes whitespace only and never signs again.'],
 ['Authorization','The receiver reads sender permissions from its server-side policy. An observer can authenticate correctly and still receive NOT_AUTHORISED for an operator-only action.'],
 ['Message expiration','Fixtures normally expire after 60 seconds. Generate just before submission. If a demo step stalls, generate a fresh fixture. Replay requires a previously accepted message in the same session.'],
 ['Protected state','Mode and reporting interval change only after all eight checks and the atomic transaction succeed. Rejections preserve protected state, accepted telemetry and replay state. Antenna and power are synthetic model outputs.'],
 ['Audit integrity','The hash chain detects changes to covered records and broken links. It cannot prove origin or prevent a complete rewrite from genesis. Verify it in Audit & Evidence; records are not tamper-proof.'],
 ['Synthetic satellite simulation','KAVACH is a local simulator with synthetic commands and telemetry. There is no spacecraft, RF link, external tracking or production certification. The fixture issuer is privileged; keep the service on trusted loopback.'],
];
export function HelpFAQ({prototypeOnly=false}:{prototypeOnly?:boolean}){
 const [query,setQuery]=useState('');
 const items=FAQ.filter(row=>row.join(' ').toLowerCase().includes(query.trim().toLowerCase()));
 if(prototypeOnly)return <section className="help-faq"><h3>Browser-only fallback</h3><p>This file uses ephemeral browser keys and in-memory records. It does not run the Python receiver, SQLite transactions, audit-chain verification or the 31-case engine suite. Reloading clears all preview data.</p><p>Use the local Python application for the complete six-step judge demonstration.</p></section>;
 return <section className="help-faq" aria-label="Security help"><h3>Security questions</h3><label htmlFor="help-search">Search help</label><input id="help-search" type="search" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Replay, HMAC, protected state..."/>{items.map(([question,answer])=><details key={question}><summary>{question}</summary><p>{answer}</p></details>)}{!items.length&&<p role="status">No matching explanation. Try a shorter search.</p>}<p className="privacy-note">No cookies or external analytics. Only your theme preference is stored in this browser.</p><a href="https://github.com/kandukurinomusubramanyachary-ai/KAVACH/blob/main/docs/DEMO.md" target="_blank" rel="noreferrer">Read the demo documentation</a></section>;
}
