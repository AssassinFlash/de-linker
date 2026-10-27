from pathlib import Path
import json,hashlib,shutil,datetime,tempfile,os
proof=Path(__file__).resolve().parent;meta=json.loads((proof/'snapshot-manifest.json').read_text());root=Path(meta['temporary_root']);planner=root/'apps/planner'
assert root.name.startswith('journal-standards-f0df-') and root.parent.resolve()==Path(tempfile.gettempdir()).resolve()
assert root.is_dir() and not root.is_symlink()
required=['REVIEW.md','REPRODUCE.md','run_review_checks.py','rebuild_snapshot.py','probe_overview.test.mjs','probe_mobile_append.mjs','probe_warning_append.mjs','execution-results.json','check-results.json','copy-catalog-check.json','guard-relocation-check.json','native-windpress-readback.json','scope-check.json','fixed-client-suite.log','fixed-build-check.log','independent-mobile-overview-warning.log']
assert all((proof/name).is_file() for name in required)
mismatches=[]
for entry in meta['files']:
 path=root/entry['path']
 if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:mismatches.append(entry['path'])
assert not mismatches,mismatches
source=(planner/'tests/workspace-lifecycle.test.mjs').read_text();header=source.split('test("same identity rechecks retain delayed edits and invalid raw numeric text"',1)[0]
mobileHeader=header.replace('return {\n\t\tannual,','return {\n        client,\n\t\tannual,',1)
annualStart=header.index('\tconst annual = () =>');annualEnd=header.index('\n\treturn {',annualStart)
warningHeader=header[:annualStart]+'\tconst annual = () => document.querySelector("#lp-load input");'+header[annualEnd:]
warningHeader=warningHeader.replace('locale: "en-US"','locale: independentLocale',1)
prefix='import { readFileSync } from "node:fs";\nlet independentLocale="en-US";\nconst independentCatalog=JSON.parse(readFileSync(new URL("../../../plugins/linker-tools/languages/linker-tools-de_DE_formal-cf89287c9001d7518d0d20e58c3eb721.json",import.meta.url),"utf8")).locale_data.messages;\n'
expected={
 'apps/planner/tests/standards_overview_probe.test.mjs':(proof/'probe_overview.test.mjs').read_bytes(),
 'apps/planner/tests/standards_mobile_probe.test.mjs':(mobileHeader+(proof/'probe_mobile_append.mjs').read_text()).encode(),
 'apps/planner/tests/standards_warning_probe.test.mjs':(prefix+warningHeader+(proof/'probe_warning_append.mjs').read_text()).encode(),
}
for name,content in expected.items():assert (root/name).read_bytes()==content,name
sourceNames={entry['path'] for entry in meta['files']};generated=[];links=[]
for current,directories,files in os.walk(root,followlinks=False):
 for name in directories+files:
  path=Path(current)/name
  if path.is_symlink():links.append({'path':str(path.relative_to(root)),'target':os.readlink(path)})
 for name in files:
  path=Path(current)/name;relative=str(path.relative_to(root))
  if relative not in sourceNames:
   assert relative in expected,relative
   content=path.read_bytes();generated.append({'path':relative,'bytes':len(content),'sha256':hashlib.sha256(content).hexdigest()})
assert links==[{'path':'apps/planner/node_modules','target':meta['node_modules']}],links
assert len(generated)==3
(proof/'generated-artifact-manifest.json').write_text(json.dumps({'fixed_sha':meta['fixed_sha'],'files':generated,'links':links,'probes_match_retained_reconstruction':True},indent=2)+'\n')
freeBefore=shutil.disk_usage(root).free;shutil.rmtree(root);freeAfter=shutil.disk_usage(proof).free
assert not root.exists();assert Path(meta['node_modules']).is_dir()
result={'fixed_sha':meta['fixed_sha'],'owner':meta['owner'],'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'deleted_root':str(root),'source_files':len(meta['files']),'source_bytes':sum(entry['bytes'] for entry in meta['files']),'source_hash_mismatches':mismatches,'generated_files':len(generated),'generated_bytes':sum(entry['bytes'] for entry in generated),'node_modules_symlink_removed_only':True,'shared_dependencies_retained':True,'temporary_root_absent':True,'retained_unique_evidence':required+['generated-artifact-manifest.json','cleanup_snapshot.py','cleanup.json','snapshot-manifest.json','metadata-initial-error.txt'],'free_before_bytes':freeBefore,'free_after_bytes':freeAfter,'observed_free_delta_bytes':freeAfter-freeBefore,'space_readback_note':'Filesystem observation; concurrent activity and allocation affect the delta. No shared/native/implementation resources removed.'}
(proof/'cleanup.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
