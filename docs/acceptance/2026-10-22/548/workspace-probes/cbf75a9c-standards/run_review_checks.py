from pathlib import Path
import subprocess,json,shutil,datetime,hashlib,gettext,re,ast
proof=Path(__file__).resolve().parent;meta=json.loads((proof/'snapshot-manifest.json').read_text());root=Path(meta['temporary_root']);planner=root/'apps/planner';repo=Path('/Users/chesterjohn/Documents/de-linker-worktrees/unified-planner-548');results=[]
def run(name,args):
 result=subprocess.run(args,cwd=planner,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 (proof/(name+'.log')).write_text(result.stdout)
 item={'name':name,'command':args,'cwd':str(planner),'exit_code':result.returncode,'log':name+'.log','summary':result.stdout[-1800:]};results.append(item)
 (proof/'execution-results.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(item),flush=True)
run('fixed-client-suite',['npm','test']);run('fixed-build-check',['npm','run','build:check'])
shutil.copy2(proof/'probe_overview.test.mjs',planner/'tests/standards_overview_probe.test.mjs')
source=(planner/'tests/workspace-lifecycle.test.mjs').read_text();header=source.split('test("same identity rechecks retain delayed edits and invalid raw numeric text"',1)[0]
mobileHeader=header.replace('return {\n\t\tannual,','return {\n        client,\n\t\tannual,',1)
assert '        client,\n\t\tannual,' in mobileHeader
(planner/'tests/standards_mobile_probe.test.mjs').write_text(mobileHeader+(proof/'probe_mobile_append.mjs').read_text())
annualStart=header.index('\tconst annual = () =>');annualEnd=header.index('\n\treturn {',annualStart)
warningHeader=header[:annualStart]+'\tconst annual = () => document.querySelector("#lp-load input");'+header[annualEnd:]
assert 'locale: "en-US"' in warningHeader
warningHeader=warningHeader.replace('locale: "en-US"','locale: independentLocale',1)
prefix='import { readFileSync } from "node:fs";\nlet independentLocale="en-US";\nconst independentCatalog=JSON.parse(readFileSync(new URL("../../../plugins/linker-tools/languages/linker-tools-de_DE_formal-cf89287c9001d7518d0d20e58c3eb721.json",import.meta.url),"utf8")).locale_data.messages;\n'
(planner/'tests/standards_warning_probe.test.mjs').write_text(prefix+warningHeader+(proof/'probe_warning_append.mjs').read_text())
run('independent-mobile-overview-warning',['node','--no-warnings=ExperimentalWarning','--loader','./tests/tsx-loader.mjs','--test','tests/standards_overview_probe.test.mjs','tests/standards_mobile_probe.test.mjs','tests/standards_warning_probe.test.mjs'])
languages=root/'plugins/linker-tools/languages'
with (languages/'linker-tools-de_DE_formal.mo').open('rb') as stream:mo=gettext.GNUTranslations(stream)
wp=json.loads((languages/'linker-tools-de_DE_formal-cf89287c9001d7518d0d20e58c3eb721.json').read_text())['locale_data']['messages']
prior=json.loads((proof.parent/'563e0387-standards/copy-catalog-check.json').read_text())
for pair in prior['messages']:assert mo.gettext(pair['english'])==pair['german'] and wp[pair['english']][0]==pair['german']
diff=subprocess.check_output(['git','diff','eefe7c0b...'+meta['fixed_sha'],'--','plugins/linker-tools/languages/linker-tools-de_DE_formal.po'],cwd=repo,text=True)
new={};current=None
for line in diff.splitlines():
 if line.startswith('+msgid '):current=ast.literal_eval(line[7:])
 if line.startswith('+msgstr '):new[current]=ast.literal_eval(line[8:])
assert len(new)==2
for message,german in new.items():assert mo.gettext(message)==german and wp[message][0]==german
(proof/'copy-catalog-check.json').write_text(json.dumps({'fixed_sha':meta['fixed_sha'],'unchanged_prior_pairs':19,'new_pairs':[{'english':en,'german':de,'compiled_gnu_and_wp_agree':True} for en,de in new.items()]},indent=2,ensure_ascii=False)+'\n')
fixedCss=(root/'plugins/linker-commerce/content/windpress/planner.css').read_bytes();wpContent=Path('/Users/chesterjohn/de-linker-local/p548/wordpress/wp-content');wind=wpContent/'uploads/windpress';volume=wind/'data/planner.css';cache=wind/'cache/tailwind.css';compiled=cache.read_text()
selectors=['.lp-plan-svg','.lp-overview-preview .lp-plan-svg','.lp-overview-preview-title > span','.lp-mobile-workspace','.lp-overview-metrics dd small']
rules={}
for selector in selectors:
 pattern=re.escape('[data-linker-planner] '+selector).replace(r'\ ',r'\s*')+r'\s*\{([^{}]*)\}'
 rules[selector]=[re.sub(r'\s+','',body) for body in re.findall(pattern,compiled)]
assert volume.read_bytes()==fixedCss
assert any('touch-action:none' in x for x in rules['.lp-plan-svg'])
assert any('touch-action:auto' in x and 'height:360px' in x for x in rules['.lp-overview-preview .lp-plan-svg'])
assert any('height:220px' in x for x in rules['.lp-overview-preview .lp-plan-svg'])
assert any('overflow-wrap:anywhere' in x and 'min-width:0' in x for x in rules['.lp-overview-preview-title > span'])
assert any('margin-inline-start:4px' in x for x in rules['.lp-overview-metrics dd small'])
focusRules=[]
for selectorsText,body in re.findall(r'([^{}]+)\{([^{}]*)\}',compiled):
 if 'outline:none' in re.sub(r'\s+','',body) and '.lp-section[tabindex=' in selectorsText:
  focusRules.append({'selectors':selectorsText.strip(),'body':body.strip()})
assert len(focusRules)==1
assert '.lp-overview[tabindex=' in focusRules[0]['selectors']
assert all(not re.search(r'(?<![\w-])'+tag+r'(?![\w-])',focusRules[0]['selectors']) for tag in ['input','button','select','textarea'])
main=(wind/'data/main.css').read_text();assert '@import "./planner.css";' in main
nativeManifest=wpContent/'plugins/linker-tools/build/planner/source-manifest.json';fixedManifest=(root/'plugins/linker-tools/build/planner/source-manifest.json').read_bytes();assert nativeManifest.read_bytes()==fixedManifest
(proof/'native-windpress-readback.json').write_text(json.dumps({'fixed_sha':meta['fixed_sha'],'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'volume_path':str(volume),'fixed_planner_css_sha256':hashlib.sha256(fixedCss).hexdigest(),'volume_matches_fixed':True,'cache_path':str(cache),'cache_sha256':hashlib.sha256(cache.read_bytes()).hexdigest(),'compiled_rules':rules,'section_focus_suppression':focusRules,'main_imports_planner':True,'native_module_manifest_path':str(nativeManifest),'native_manifest_sha256':hashlib.sha256(fixedManifest).hexdigest(),'native_manifest_matches_fixed':True,'limits':'Read-only filesystem/compiler evidence only, not browser focus appearance, viewport geometry or physical touch.'},indent=2)+'\n')
(proof/'check-results.json').write_text(json.dumps({'fixed_sha':meta['fixed_sha'],'checks':results,'prior_copy_pairs_unchanged':19,'new_copy_pairs_match':2,'native_volume_compiler_and_manifest_match':True},indent=2)+'\n')
print(json.dumps({'prior_copy_pairs_unchanged':19,'new_copy_pairs_match':2,'native_volume_compiler_and_manifest_match':True}),flush=True)
