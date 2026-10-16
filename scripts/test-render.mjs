import {build} from 'esbuild';
import {readFileSync,mkdirSync} from 'node:fs';
import {pathToFileURL} from 'node:url';
import path from 'node:path';
import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import assert from 'node:assert/strict';
mkdirSync('.arena',{recursive:true});
await build({entryPoints:['web/src/components/AttackTimeline.tsx'],bundle:true,format:'esm',platform:'node',external:['react','react-dom','lucide-react'],outfile:'.arena/timeline-test.mjs'});
const {AttackTimeline}=await import(pathToFileURL(path.resolve('.arena/timeline-test.mjs')).href);
// Input is a real fail-closed receiver response created by the Python regression.
const result=JSON.parse(readFileSync(0,'utf8'));
assert.equal(result.verdict,'SERVICE_ERROR');
const markup=renderToStaticMarkup(React.createElement(AttackTimeline,{result}));
assert.match(markup,/workstation-label">Service unavailable/);
assert.doesNotMatch(markup,/workstation-label">Accepted/);
assert.ok(markup.includes(result.checks.find(c=>c.status==='FAIL').label));
console.log('Real SERVICE_ERROR timeline rendering: PASS');
