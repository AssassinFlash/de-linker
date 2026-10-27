from pathlib import Path
import json,hashlib,shutil,datetime,tempfile,os
proof=Path(__file__).resolve().parent;meta=json.loads((proof/'snapshot-manifest.json').read_text());root=Path(meta['temporary_root']);planner=root/'apps/planner'
assert root.name.startswith('roof-import-standards-eff8-') and root.parent.resolve()==Path(tempfile.gettempdir()).resolve()
assert root.is_dir() and not root.is_symlink()
required=['REVIEW.md', 'REPRODUCE.md', 'review-results.json', 'baseline-runner.py', 'rebuild_snapshot.py', 'prepare-probes.py', 'probe-refusal-origin.append.mjs', 'probe-choice-unicode.mjs', 'probe-storage-warning.append.mjs', 'probe-correction-boundaries.append.mjs', 'execution-results.json', 'copy-catalog-check.json', 'source-pipeline-check.json', 'message-inventory-check.json', 'verify-message-inventory.mjs', 'verify-source-catalogs.py', 'heuristic-judgments.json', 'probe-reconstruction-check.json', 'original-probes-unchanged.json', 'unchanged-counterexample-replay-result.json', 'independent-correction-boundaries-result.json', 'independent-correction-boundaries-initial-result.json', 'fixed-client-suite.log', 'fixed-build-check.log', 'unchanged-counterexample-replay.log', 'independent-correction-boundaries.log', 'independent-correction-boundaries-initial.log', 'harness-notes.md', 'message-inventory-initial-error.txt']
assert all((proof/name).is_file() for name in required)
mismatches=[]
for entry in meta['files']:
 path=root/entry['path']
 if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:mismatches.append(entry['path'])
assert not mismatches,mismatches
expected=json.loads((proof/'probe-reconstruction-check.json').read_text())['files'];sourceNames={entry['path'] for entry in meta['files']};generated=[];links=[]
for current,directories,files in os.walk(root,followlinks=False):
 for name in directories+files:
  path=Path(current)/name
  if path.is_symlink():links.append({'path':str(path.relative_to(root)),'target':os.readlink(path)})
 for name in files:
  path=Path(current)/name;relative=str(path.relative_to(root))
  if relative not in sourceNames:
   assert relative=='apps/planner/tests/'+path.name and path.name in expected,relative
   content=path.read_bytes();digest=hashlib.sha256(content).hexdigest();assert digest==expected[path.name],relative
   generated.append({'path':relative,'bytes':len(content),'sha256':digest})
assert links==[{'path':'apps/planner/node_modules','target':meta['node_modules']}],links
assert len(generated)==5
(proof/'generated-artifact-manifest.json').write_text(json.dumps({'fixed_sha':meta['fixed_sha'],'files':generated,'links':links,'probes_match_retained_reconstruction':True},indent=2)+'\n')
freeBefore=shutil.disk_usage(root).free;shutil.rmtree(root);freeAfter=shutil.disk_usage(proof).free
assert not root.exists();assert Path(meta['node_modules']).is_dir()
result={'fixed_sha':meta['fixed_sha'],'owner':meta['owner'],'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'deleted_root':str(root),'source_files':len(meta['files']),'source_bytes':sum(entry['bytes'] for entry in meta['files']),'source_hash_mismatches':mismatches,'generated_files':len(generated),'generated_bytes':sum(entry['bytes'] for entry in generated),'node_modules_symlink_removed_only':True,'shared_dependencies_retained':True,'temporary_root_absent':True,'retained_unique_evidence':required+['generated-artifact-manifest.json','cleanup_snapshot.py','cleanup.json','snapshot-manifest.json'],'free_before_bytes':freeBefore,'free_after_bytes':freeAfter,'observed_free_delta_bytes':freeAfter-freeBefore,'space_readback_note':'Filesystem observation; concurrent activity and allocation affect the delta. No shared/native/implementation resources removed.'}
(proof/'cleanup.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
