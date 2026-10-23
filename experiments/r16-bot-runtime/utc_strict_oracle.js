"use strict";
const fs=require('node:fs');
function strictUtc(s){
  const m=/^([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})(?:\.([0-9]{1,9}))?(Z|([+-])([0-9]{2}):([0-9]{2}))$/.exec(s);
  if(!m)return false;
  const [year,mon,day,hh,mm,ss]=m.slice(1,7).map(Number);
  if(year<1||year>9999||hh>23||mm>59||ss>59||mon<1||mon>12||day<1||day>31)return false;
  const offh=m[10]===undefined?0:Number(m[10]), offm=m[11]===undefined?0:Number(m[11]);
  if(offh>18||offm>59||(offh===18&&offm!==0))return false;
  const d=new Date(0);d.setUTCFullYear(year,mon-1,day);d.setUTCHours(hh,mm,ss,0);
  return d.getUTCFullYear()===year&&d.getUTCMonth()===mon-1&&d.getUTCDate()===day&&d.getUTCHours()===hh&&d.getUTCMinutes()===mm&&d.getUTCSeconds()===ss;
}
const raw=fs.readFileSync('utc_strict_oracle_cases.tsv','utf8');
const lines=raw.replace(/\r?\n$/, '').split(/\r?\n/);
if(lines.length<2 || lines[0]!=='value\texpected')throw Error('invalid or empty fixture');
const rows=lines.slice(1);
let count=0;
for (const row of rows){
  const fields=row.split('\t');
  if(fields.length!==2 || !['PASS','FAIL'].includes(fields[1]))throw Error('malformed case '+(count+1));
  const [s,expected]=fields;
  const got=strictUtc(s)?'PASS':'FAIL';
  if(got!==expected)throw Error('case '+(count+1)+' '+s+' got '+got+' expected '+expected);
  count++;
}
console.log(`JavaScript strict timestamp oracle: PASS ${count}/${count}`);
