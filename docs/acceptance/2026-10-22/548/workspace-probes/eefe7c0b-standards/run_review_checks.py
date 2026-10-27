from pathlib import Path
import subprocess,json,shutil,datetime,hashlib,gettext,re,sys
proof=Path(__file__).resolve().parent;meta=json.loads((proof/'snapshot-manifest.json').read_text());root=Path(meta['temporary_root']);planner=root/'apps/planner'
repo=Path('/Users/chesterjohn/Documents/de-linker-worktrees/unified-planner-548');results=[]
def run(name,args):
 result=subprocess.run(args,cwd=planner,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 (proof/(name+'.log')).write_text(result.stdout)
 item={'name':name,'command':args,'cwd':str(planner),'exit_code':result.returncode,'log':name+'.log','summary':result.stdout[-1000:]};results.append(item);print(json.dumps(item),flush=True)
metadata_only='--metadata-only' in sys.argv
if metadata_only:
 results=json.loads((proof/'execution-results.json').read_text())
else:
 run('fixed-client-suite',['npm','test'])
 run('fixed-build-check',['npm','run','build:check'])
shutil.copy2(proof/'probe_overview.test.mjs',planner/'tests/standards_overview_probe.test.mjs')
source=(planner/'tests/workspace-lifecycle.test.mjs').read_text();header=source.split('test("same identity rechecks retain delayed edits and invalid raw numeric text"',1)[0]
# Expose only the fixture's already-existing client so the probe can activate the
# real immediate scope fence. Application source and client behavior are untouched.
header=header.replace('return {\n\t\tannual,','return {\n        client,\n\t\tannual,',1)
assert '        client,\n\t\tannual,' in header
(planner/'tests/standards_mobile_probe.test.mjs').write_text(header+(proof/'probe_mobile_append.mjs').read_text())
if not metadata_only:
 run('independent-mobile-overview',['node','--no-warnings=ExperimentalWarning','--loader','./tests/tsx-loader.mjs','--test','tests/standards_overview_probe.test.mjs','tests/standards_mobile_probe.test.mjs'])
(proof/'execution-results.json').write_text(json.dumps(results,indent=2)+'\n')
languages=['plugins/linker-tools/languages/linker-tools-de_DE_formal.po','plugins/linker-tools/languages/linker-tools-de_DE_formal.mo','plugins/linker-tools/languages/linker-tools-de_DE_formal-cf89287c9001d7518d0d20e58c3eb721.json']
unchanged=[]
for name in languages:
 old=subprocess.check_output(['git','show','563e0387:'+name],cwd=repo);current=(root/name).read_bytes()
 unchanged.append({'path':name,'previous_sha256':hashlib.sha256(old).hexdigest(),'fixed_sha256':hashlib.sha256(current).hexdigest(),'unchanged':old==current})
assert all(x['unchanged'] for x in unchanged)
prior=json.loads((proof.parent/'563e0387-standards/copy-catalog-check.json').read_text())
with (root/languages[1]).open('rb') as stream:mo=gettext.GNUTranslations(stream)
wp=json.loads((root/languages[2]).read_text())['locale_data']['messages']
for pair in prior['messages']:
 assert mo.gettext(pair['english'])==pair['german'] and wp[pair['english']][0]==pair['german']
newSource=subprocess.check_output(['git','diff','563e0387...'+meta['fixed_sha'],'--','apps/planner/src/components/ProjectEditor.tsx'],cwd=repo,text=True)
newMessages=re.findall(r'\+.*?__\("([^"]+)"',newSource)
for message in newMessages:assert message in wp and mo.gettext(message)==wp[message][0]
(proof/'copy-unchanged.json').write_text(json.dumps({'fixed_sha':meta['fixed_sha'],'prior_independent_review':'../563e0387-standards/COPY-REVIEW.md','catalogs':unchanged,'rechecked_prior_pairs':19,'selector_reuses_existing_messages':newMessages},indent=2)+'\n')
# Source/volume/compiler metadata readback only; this is neither a layout capture
# nor proof of physical touch gestures, and makes no native writes.
cssName='plugins/linker-commerce/content/windpress/planner.css';fixedCss=(root/cssName).read_bytes()
wpContent=Path('/Users/chesterjohn/de-linker-local/p548/wordpress/wp-content');wind=wpContent/'uploads/windpress'
volume=wind/'data/planner.css';cache=wind/'cache/tailwind.css';compiled=cache.read_text();main=(wind/'data/main.css').read_text()
selectors=['.lp-plan-svg','.lp-overview-preview .lp-plan-svg','.lp-overview-preview-title > span','.lp-mobile-workspace']
rules={}
for selector in selectors:
 pattern=re.escape('[data-linker-planner] '+selector).replace(r'\ ',r'\s*')+r'\s*\{([^{}]*)\}'
 rules[selector]=[re.sub(r'\s+','',body) for body in re.findall(pattern,compiled)]
assert volume.read_bytes()==fixedCss
assert '@import "./planner.css";' in main
assert any('touch-action:none' in x for x in rules['.lp-plan-svg'])
assert any('touch-action:auto' in x for x in rules['.lp-overview-preview .lp-plan-svg'])
assert any('overflow-wrap:anywhere' in x and 'min-width:0' in x for x in rules['.lp-overview-preview-title > span'])
assert any('display:none' in x for x in rules['.lp-mobile-workspace']) and any('display:block' in x for x in rules['.lp-mobile-workspace'])
nativeBuild=wpContent/'plugins/linker-tools/build/planner';manifest=(root/'plugins/linker-tools/build/planner/source-manifest.json').read_bytes()
assert (nativeBuild/'source-manifest.json').read_bytes()==manifest
(proof/'native-windpress-readback.json').write_text(json.dumps({'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'fixed_sha':meta['fixed_sha'],'fixed_planner_css_sha256':hashlib.sha256(fixedCss).hexdigest(),'volume_path':str(volume),'volume_sha256':hashlib.sha256(volume.read_bytes()).hexdigest(),'volume_matches_fixed':True,'native_main_imports_planner':True,'cache_path':str(cache),'cache_sha256':hashlib.sha256(cache.read_bytes()).hexdigest(),'cache_mtime_ns':cache.stat().st_mtime_ns,'compiled_rules':rules,'native_module_manifest_path':str(nativeBuild/'source-manifest.json'),'native_module_manifest_sha256':hashlib.sha256(manifest).hexdigest(),'native_manifest_matches_fixed':True,'limits':'Filesystem metadata and compiled rules only; not current browser cache, actual viewport visibility or physical-touch acceptance.'},indent=2)+'\n')
(proof/'check-results.json').write_text(json.dumps({'fixed_sha':meta['fixed_sha'],'run_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':results,'copy_catalogs_unchanged':True,'native_volume_and_compiled_rules_match':True},indent=2)+'\n')
print(json.dumps({'copy_catalogs_unchanged':True,'native_volume_and_compiled_rules_match':True}),flush=True)
