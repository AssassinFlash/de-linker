import {createRequire} from 'node:module';
import {execFileSync} from 'node:child_process';
import {readFileSync,writeFileSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
const proof=dirname(new URL(import.meta.url).pathname),meta=JSON.parse(readFileSync(resolve(proof,'snapshot-manifest.json'),'utf8'));
const require=createRequire(resolve(meta.temporary_root,'apps/planner/package.json')),ts=require('typescript');
const repo=resolve(meta.node_modules,'../../..');
function inventory(sha){
 const result=new Set();
 const files=execFileSync('git',['ls-tree','-r','--name-only',sha],{cwd:repo,encoding:'utf8'}).split('\n').filter(name=>name.startsWith('apps/planner/src/')&&/\.tsx?$/.test(name)&&!name.endsWith('.test.ts'));
 for(const name of files){
  const source=ts.createSourceFile(name,execFileSync('git',['show',sha+':'+name],{cwd:repo,encoding:'utf8'}),ts.ScriptTarget.Latest,true,name.endsWith('.tsx')?ts.ScriptKind.TSX:ts.ScriptKind.TS);
  const visit=node=>{if(ts.isCallExpression(node)&&ts.isIdentifier(node.expression)&&node.expression.text==='__'&&node.arguments[0]&&ts.isStringLiteral(node.arguments[0]))result.add(node.arguments[0].text);ts.forEachChild(node,visit);};visit(source);
 }
 return result;
}
const base=inventory(meta.base_sha),prior=inventory(meta.prior_fixture_sha),target=inventory(meta.fixed_sha),final=JSON.parse(readFileSync(resolve(meta.temporary_root,'docs/acceptance/2026-10-22/548/import-copy-final.json'),'utf8'));
const priorPO=execFileSync('git',['show',meta.prior_fixture_sha+':plugins/linker-tools/languages/linker-tools-de_DE_formal.po'],{cwd:repo,encoding:'utf8'});
const approvedReusedSiteTerms=new Set(['Choose file']);for(const term of approvedReusedSiteTerms)if(!priorPO.includes('msgid '+JSON.stringify(term)+'\n'))throw new Error('Missing prior site catalog term '+term);
const reviewed=new Set(final.map(pair=>pair.en)),newOutsideReview=[...target].filter(message=>!base.has(message)&&!reviewed.has(message)&&!approvedReusedSiteTerms.has(message));
if(newOutsideReview.length)throw new Error('Unreviewed new message ids: '+JSON.stringify(newOutsideReview));
const correctionNew=[...target].filter(message=>!prior.has(message));if(correctionNew.some(message=>!approvedReusedSiteTerms.has(message)))throw new Error('Correction introduced unreviewed message ids: '+JSON.stringify(correctionNew));
const wp=JSON.parse(readFileSync(resolve(meta.temporary_root,'plugins/linker-tools/languages/linker-tools-de_DE_formal-cf89287c9001d7518d0d20e58c3eb721.json'),'utf8')).locale_data.messages;
const reused=['Choose file','No file selected','Complete this field to continue.'].map(en=>{if(!target.has(en)||!wp[en]?.[0])throw new Error('Missing actual-source or catalog reuse '+en);return {en,de:wp[en][0],planner_message_previously_present:prior.has(en),previous_site_catalog_term_present:priorPO.includes('msgid '+JSON.stringify(en)+'\n')};});
writeFileSync(resolve(proof,'message-inventory-check.json'),JSON.stringify({fixed_sha:meta.fixed_sha,parser:'Installed TypeScript syntax tree; customer message calls only',base_message_count:base.size,target_message_count:target.size,new_scope_messages:[...target].filter(message=>!base.has(message)),new_messages_outside_review:newOutsideReview,correction_added_planner_references:correctionNew,correction_new_unreviewed_wording:[],existing_site_term_reuse_authority:'Explicit parent task approval plus the prior GNU catalog; no old implementation copied.',reused_control_messages:reused,limit:'Catalog/source evidence plus independent DOM wording, not native OS file-dialog language or production loading.'},null,2)+'\n');
console.log(JSON.stringify({scope_new_messages:[...target].filter(message=>!base.has(message)).length,unreviewed_new_messages:0,correction_new_planner_references:correctionNew,correction_unreviewed_messages:0,reused}));
