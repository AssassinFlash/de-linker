from pathlib import Path
import subprocess,json,shutil,datetime,ast,gettext,hashlib
proof=Path(__file__).resolve().parent
meta=json.loads((proof/'snapshot-manifest.json').read_text());root=Path(meta['temporary_root'])
planner=root/'apps/planner';results=[]
def run(name,args):
 result=subprocess.run(args,cwd=planner,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 (proof/(name+'.log')).write_text(result.stdout)
 summary={'name':name,'command':args,'cwd':str(planner),'exit_code':result.returncode,'log':name+'.log','summary':result.stdout[-1200:]}
 results.append(summary)
 print(json.dumps(summary),flush=True)
run('fixed-client-suite',['npm','test'])
run('fixed-build-check',['npm','run','build:check'])
# Independent tests use the actual fixed application and native-translation catalog
# through a JSDOM facade. No layout/touch/GPU/native-site evidence is claimed.
shutil.copy2(proof/'probe_overview.test.mjs',planner/'tests/standards_overview_probe.test.mjs')
source=(planner/'tests/workspace-lifecycle.test.mjs').read_text()
header=source.split('test("same identity rechecks retain delayed edits and invalid raw numeric text"',1)[0]
(planner/'tests/standards_lifecycle_probe.test.mjs').write_text(header+(proof/'probe_lifecycle_append.mjs').read_text())
run('independent-workspaces',['node','--no-warnings=ExperimentalWarning','--loader','./tests/tsx-loader.mjs','--test','tests/standards_overview_probe.test.mjs','tests/standards_lifecycle_probe.test.mjs'])
# Verify all exact new PO messages are in the compiled GNU and native WP JSON catalogs.
repo=Path('/Users/chesterjohn/Documents/de-linker-worktrees/unified-planner-548')
diff=subprocess.check_output(['git','diff',meta['base_sha']+'...'+meta['fixed_sha'],'--','plugins/linker-tools/languages/linker-tools-de_DE_formal.po'],cwd=repo,text=True)
new={};current=None
for line in diff.splitlines():
 if line.startswith('+msgid '):current=ast.literal_eval(line[7:])
 if line.startswith('+msgstr '):new[current]=ast.literal_eval(line[8:])
assert len(new)==19
language=root/'plugins/linker-tools/languages'
with (language/'linker-tools-de_DE_formal.mo').open('rb') as stream: mo=gettext.GNUTranslations(stream)
wp=json.loads((language/'linker-tools-de_DE_formal-cf89287c9001d7518d0d20e58c3eb721.json').read_text())['locale_data']['messages']
checks=[]
for message,german in new.items():
 checks.append({'english':message,'german':german,'gnu_matches':mo.gettext(message)==german,'wordpress_json_matches':wp[message][0]==german,'forbidden_prose_dash':any(x in message+german for x in ['—','–'])})
assert all(c['gnu_matches'] and c['wordpress_json_matches'] and not c['forbidden_prose_dash'] for c in checks)
(proof/'copy-catalog-check.json').write_text(json.dumps({'fixed_sha':meta['fixed_sha'],'messages':checks},indent=2,ensure_ascii=False)+'\n')
(proof/'check-results.json').write_text(json.dumps({'fixed_sha':meta['fixed_sha'],'run_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':results,'copy_catalog_entries_checked':19},indent=2)+'\n')
print(json.dumps({'copy_catalog_entries_checked':19,'all_match':True}),flush=True)
