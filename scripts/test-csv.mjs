import {build} from 'esbuild';
import {mkdirSync} from 'node:fs';
import {pathToFileURL} from 'node:url';
import path from 'node:path';
import assert from 'node:assert/strict';
import test from 'node:test';

mkdirSync('.arena',{recursive:true});
// Resolve the platform executable through esbuild's supported API.
await build({entryPoints:['web/src/csv.ts'],format:'esm',platform:'node',outfile:'.arena/csv-under-test.mjs'});
const {csvCell,toCsv}=await import(pathToFileURL(path.resolve('.arena/csv-under-test.mjs')).href);

test('plain values pass through unchanged',()=>{
 assert.equal(csvCell('operator-01'),'operator-01');
 assert.equal(csvCell(42),'42');
 assert.equal(csvCell('ACCEPTED'),'ACCEPTED');
});

test('null and undefined become empty cells, never the string "null"',()=>{
 assert.equal(csvCell(null),'');
 assert.equal(csvCell(undefined),'');
});

test('commas force quoting',()=>{assert.equal(csvCell('a,b'),'"a,b"')});

test('double quotes are escaped by doubling, per RFC 4180',()=>{
 assert.equal(csvCell('say "hi"'),'"say ""hi"""');
});

test('carriage returns also force quoting',()=>{
 assert.equal(csvCell('a\rb'),'"a\rb"');
});

test('newlines force quoting so a record cannot split across rows',()=>{
 assert.equal(csvCell('line1\nline2'),'"line1\nline2"');
 assert.equal(toCsv([['a','b\nc'],['d','e']]).split('\r\n').length,2);
});

test('rows are separated by CRLF and cells by comma',()=>{
 assert.equal(toCsv([['a','b'],['c','d']]),'a,b\r\nc,d');
});

test('a realistic decision row round-trips with a stable column count',()=>{
 const head=['event_id','session_id','received_at','verdict','reason_code','first_failed_stage','sender','message_type','action','sender_verified','state_changed','replay_state_advanced','audit_persisted','input_sha256'];
 const row=['evt-1','KVC-123','2026-10-16T00:00:00.000Z','REJECTED','AUTH_FAILED','authentication','operator-01','COMMAND','SET_MODE',true,false,false,true,'abc123'];
 const lines=toCsv([head,row]).split('\r\n');
 assert.equal(lines.length,2);
 assert.equal(lines[0].split(',').length,14);
 assert.equal(lines[1].split(',').length,14);
 assert.ok(lines[1].includes('AUTH_FAILED'));
});

test('empty input produces an empty document, not a stray newline',()=>{
 assert.equal(toCsv([]),'');
 assert.equal(toCsv([[]]),'');
});

test('a value containing a comma stays inside one quoted cell',()=>{
 // Naive comma-splitting would wrongly yield 3 cells; the quoting is what prevents it.
 const csv=toCsv([['reason','note'],['A,B','x']]);
 assert.equal(csv,'reason,note\r\n"A,B",x');
 assert.equal(csv.split('\r\n').length,2,'Still exactly two records.');
 assert.equal(csvCell('A,B'),'"A,B"');
 // A reader that honours quotes must recover the original two cells.
 const cells=[...csv.split('\r\n')[1].matchAll(/"((?:[^"]|"")*)"|([^,]+)/g)].map(m=>m[1]!==undefined?m[1].replaceAll('""','"'):m[2]);
 assert.deepEqual(cells,['A,B','x']);
});

test('untrusted formula prefixes are exported as literal spreadsheet text',()=>{
 for(const value of ['=1+1','+SUM(A1)','-cmd','@SUM(A1)','  =1','\t=1','\r=1']){
  assert.ok(csvCell(value).includes("'"),'Formula prefix must be escaped');
 }
});
test('numeric negative measurements retain their numeric representation',()=>{
 assert.equal(csvCell(-12),'-12');
 assert.equal(csvCell('operator-01'),'operator-01');
});
