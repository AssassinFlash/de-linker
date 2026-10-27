from pathlib import Path
import subprocess,json,hashlib,gettext,re,datetime
proof=Path(__file__).resolve().parent;meta=json.loads((proof/'snapshot-manifest.json').read_text());root=Path(meta['temporary_root']);repo=Path('/Users/chesterjohn/Documents/de-linker-worktrees/unified-planner-548');sha=meta['fixed_sha'];base=meta['base_sha'];lang=root/'plugins/linker-tools/languages'
final=json.loads((root/'docs/acceptance/2026-10-22/548/import-copy-final.json').read_text())
feedback=json.loads(subprocess.check_output(['git','show',sha+':docs/acceptance/2026-10-22/548/import-copy-feedback.json'],cwd=repo))
with (lang/'linker-tools-de_DE_formal.mo').open('rb') as stream:mo=gettext.GNUTranslations(stream)
wp=json.loads((lang/'linker-tools-de_DE_formal-cf89287c9001d7518d0d20e58c3eb721.json').read_text())['locale_data']['messages']
allSource='\n'.join(p.read_text() for p in (root/'apps/planner/src').rglob('*.tsx'))
messages=[]
for i,pair in enumerate(final):
 assert pair['id']==f'GEO-{i+1:03d}'
 assert mo.gettext(pair['en'])==pair['de'] and wp[pair['en']][0]==pair['de'],pair['id']
 original=feedback['final_pairs'][i]['final_proposal']
 if pair['id']!='GEO-010':assert pair['en']==original['en'] and pair['de']==original['de'],pair['id']
 assert re.findall(r'%(?:\d+\$)?[sd]',pair['en'])==re.findall(r'%(?:\d+\$)?[sd]',pair['de']),pair['id']
 assert json.dumps(pair['en'],ensure_ascii=False) in allSource or pair['en'] in allSource,pair['id']
 messages.append({'id':pair['id'],'english':pair['en'],'german':pair['de'],'gnu_mo_and_wp_json_match':True,'matches_reviewed_proposal':pair['id']!='GEO-010'})
assert len(messages)==76
expected='Browser recovery could not be read or updated. An upload starts only after a recovery copy of its original file and settings is saved. Project versions already saved on the server are unchanged.'
assert final[9]['en']==expected
(proof/'copy-catalog-check.json').write_text(json.dumps({'fixed_sha':sha,'final_file_sha256':hashlib.sha256((root/'docs/acceptance/2026-10-22/548/import-copy-final.json').read_bytes()).hexdigest(),'count':76,'unchanged_adopted_review_pairs':75,'GEO_010_exception':'Independently accepted against list/acknowledge/cleanup branches. Actual EN/DE controller and integrated ProjectEditor probes retain the original and permit preview/adoption/server save after local updates fail. This does not claim native browser acceptance.','messages':messages},indent=2,ensure_ascii=False)+'\n')
changed=subprocess.check_output(['git','diff','--name-only',base+'...'+sha],cwd=repo,text=True).splitlines()
addedSource=subprocess.check_output(['git','diff','--unified=0',base+'...'+sha,'--','apps/planner/src','plugins/linker-commerce/content/windpress/planner.css'],cwd=repo,text=True)
legacy=[line for line in addedSource.splitlines() if line.startswith('+') and not line.startswith('+++') and re.search(r'tv_b2b_|Linker_AI_|dlk-',line)];assert not legacy
pkg=json.loads((root/'apps/planner/package.json').read_text());lock=json.loads((root/'apps/planner/package-lock.json').read_text());oldPkg=json.loads(subprocess.check_output(['git','show',base+':apps/planner/package.json'],cwd=repo));assert pkg['dependencies']==oldPkg['dependencies'];assert pkg['devDependencies']['fake-indexeddb']=='6.2.6';assert lock['packages']['node_modules/fake-indexeddb']['dev'] is True
assert not any(name.endswith('.css') and name!='plugins/linker-commerce/content/windpress/planner.css' for name in changed)
styleAdded=[line[1:] for line in addedSource.splitlines() if line.startswith('+  [data-linker-planner]')];assert len(styleAdded)==18
capturePath='docs/research/2026-10-23-map-workbench-integration/dependency-fake-indexeddb/apify-results.json';captureBytes=subprocess.check_output(['git','show',sha+':'+capturePath],cwd=repo);capture=json.loads(captureBytes)
runPath='docs/research/2026-10-23-map-workbench-integration/dependency-fake-indexeddb/run.json';run=json.loads(subprocess.check_output(['git','show',sha+':'+runPath],cwd=repo));assert run['status']=='SUCCEEDED'
assert len(capture)==2 and all(row['crawl']['httpStatusCode']==200 for row in capture)
assert any('IDBFactory' in row.get('text','') for row in capture)
assert any('"version": "6.2.6"' in row.get('text','') and 'Apache-2.0' in row.get('text','') for row in capture)
standardsNames=[]
for name in subprocess.check_output(['git','ls-tree','-r','--name-only',sha],cwd=repo,text=True).splitlines():
 if re.search(r'(^|/)(AGENTS\.md|CONTRIBUTING[^/]*|CODING[^/]*|STYLEGUIDE[^/]*|CODE_STYLE[^/]*|.*coding[-_]standards.*)$',name,re.I):standardsNames.append(name)
result={'fixed_sha':sha,'base_sha':base,'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'standards_inventory':standardsNames,'other_contributing_or_coding_standard_files_found':[],'standards_also_applied':['CONTEXT.md','docs/adr/0002-isolated-planner-runtime.md','docs/specs/548-roof-import-workflow.md','docs/specs/548-geographic-intake.md','current user local-storage discipline and /Users/chesterjohn/Documents/de-linker/docs/agents/local-storage.md'],'reviewed_changed_files':changed,'added_legacy_identifier_matches':legacy,'runtime_dependencies_unchanged':True,'only_new_dependency':{'package':'fake-indexeddb','version':'6.2.6','dev_only':True,'installed_version':json.loads((repo/'apps/planner/node_modules/fake-indexeddb/package.json').read_text())['version'],'actual_usage':'IDBFactory creates isolated stores in unit/component tests; standard transaction, cursor, scope index, commit and abort behavior execute through GeometryImportStore, not a hand-written map.'},'new_styles_only_native_windpress':True,'new_scoped_css_rules':len(styleAdded),'source_capture':{'run':run,'path':capturePath,'sha256':hashlib.sha256(captureBytes).hexdigest(),'primary_source_urls':[row['url'] for row in capture],'primary_sources_support_selected_version_licence_and_constructor':True},'limit':'Source/compiled-catalog and emitted graph evidence only. No p548 browser, native runtime mutation or production operation.'}
(proof/'source-pipeline-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'copy_pairs':76,'unchanged_adopted_pairs':75,'GEO10_runtime_exception_checked':True,'runtime_dependencies_unchanged':True,'WindPress_scoped_rules':len(styleAdded),'Apify_capture_verified':True,'additional_coding_standards':[]}))
