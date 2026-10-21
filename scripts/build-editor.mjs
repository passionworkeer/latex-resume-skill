import { build } from 'esbuild';
import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
const fallbackSources=JSON.parse(await readFile('licenses/frontend/sources.json','utf8')).sources;
const root='skills/latex-resume/assets/editor';
const result=await build({entryPoints:['frontend/editor.js'],bundle:true,minify:true,outfile:`${root}/bundle.js`,format:'iife',external:['/assets/fonts/*'],target:['es2020'],legalComments:'eof',metafile:true});
// Include the complete copyright/license notices of bundled dependencies.
const packages=new Set(Object.keys(result.metafile.inputs).filter(p=>p.includes('node_modules/')).map(p=>{const bits=p.split('node_modules/').pop().split('/');return bits[0].startsWith('@')?bits.slice(0,2).join('/'):bits[0]}));
let notices='# Bundled frontend third-party notices\n\nGenerated from the locked npm dependencies actually included in bundle.js / bundle.css. Original application code is MIT.\n';
for (const name of [...packages].sort()) {
 const base=`node_modules/${name}`;const meta=JSON.parse(await readFile(`${base}/package.json`,'utf8'));
 let license='';for(const file of ['LICENSE','LICENSE.md','LICENSE.txt','license','license.md','license.txt','COPYING']){try{license=await readFile(`${base}/${file}`,'utf8');break}catch{}}
 if(!license){
  // Exact locked versions only: upstream monorepo licenses or documented MIT declaration.
  const allowed=name==='micromark'||name.startsWith('micromark-')||name==='rehype-stringify'||name==='word-count';
  const source=allowed&&fallbackSources.find(s=>s.packages.includes(`${name}@${meta.version}`)&&s.file.endsWith(name==='word-count'?'NOTICE.txt':'LICENSE.txt'));
  if(source){
   license=await readFile(`licenses/frontend/${source.file}`,'utf8');
   if(createHash('sha256').update(license).digest('hex')!==source.sha256)throw new Error(`License integrity mismatch for ${name}`);
  }
 }
 if(!license)throw new Error(`Missing full license for bundled dependency ${name}`);
 notices+=`\n## ${name} ${meta.version}\n\nSource: https://www.npmjs.com/package/${name}/v/${meta.version}\n\nLicense: ${meta.license}\n\n\`\`\`text\n${license.trim()}\n\`\`\`\n`;
}
await writeFile(`${root}/THIRD_PARTY_NOTICES.md`,notices);
