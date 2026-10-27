from pathlib import Path
import json,shutil,subprocess
proof=Path(__file__).resolve().parent;meta=json.loads((proof/'snapshot-manifest.json').read_text());planner=Path(meta['temporary_root'])/'apps/planner'
repo=Path(meta['node_modules']).parents[2];source=subprocess.check_output(['git','show',meta['prior_fixture_sha']+':apps/planner/tests/geometry-import.test.mjs'],cwd=repo,text=True);header=source.split('test("a lost acknowledgement retains original bytes/key across review and an explicit retry"',1)[0]
assert len(header)<len(source)
refusal=header.replace('locale = "en-GB",','locale = "en-GB",\n        replyOverride = undefined,\n        replyStatus = 200,',1)
refusal=refusal.replace('return json(asset);','return json(replyOverride === undefined ? asset : replyOverride, replyStatus);',1)
(planner/'tests/standards-refusal-origin.test.mjs').write_text(refusal+(proof/'probe-refusal-origin.append.mjs').read_text())
shutil.copy2(proof/'probe-choice-unicode.mjs',planner/'tests/standards-choice-unicode.test.mjs')
warning=header.replace('journal,\n\t\tuploads,','journal,\n        store,\n\t\tuploads,',1)
needle='const { createRoot } = await import("react-dom/client");'
catalog='''\n if(locale.startsWith('de')){const catalog=JSON.parse(readFileSync(new URL('../../../plugins/linker-tools/languages/linker-tools-de_DE_formal-cf89287c9001d7518d0d20e58c3eb721.json',import.meta.url),'utf8')).locale_data.messages;window.wp.i18n.__=message=>catalog[message]?.[0]||message;}'''
warning=warning.replace(needle,needle+catalog,1)
(planner/'tests/standards-storage-warning.test.mjs').write_text(warning+(proof/'probe-storage-warning.append.mjs').read_text())
project=subprocess.check_output(['git','show',meta['prior_fixture_sha']+':apps/planner/tests/geometry-project.test.mjs'],cwd=repo,text=True).replace('import joins one project history step, guards navigation, and a confirmed save clears its exact original','independent acknowledged source with failed browser updates can still be adopted and saved on the server',1)
needle='await geometryImportStore.write(session.query_scope, original);'
project=project.replace(needle,needle+'''
 const nativeList=geometryImportStore.list.bind(geometryImportStore),nativeAck=geometryImportStore.acknowledge.bind(geometryImportStore);let failedAck=false;
 geometryImportStore.acknowledge=async()=>{failedAck=true;throw new Error('synthetic_ack_failure');};
 geometryImportStore.list=async(...args)=>{if(failedAck)throw new Error('synthetic_list_failure');return nativeList(...args);};
 t.after(()=>{geometryImportStore.list=nativeList;geometryImportStore.acknowledge=nativeAck;});
''',1)
needle='await click("Add roof to current design");'
project=project.replace(needle,'''
 await until(()=>document.body.textContent.includes('Browser recovery could not be read or updated.'));
 assert.ok(!document.body.textContent.includes('this upload cannot continue'));
'''+needle,1)
start=project.index('\tawait until(() => !document.querySelector(".lp-geometry-intake details"));');end=project.rindex('\n});')
project=project[:start]+'''
 const retained=await nativeList([session.query_scope],project.id);assert.equal(retained.length,1);assert.equal(retained[0].body,original);
 assert.equal(saved.revision,2);console.log(JSON.stringify({probe:'project-save-with-local-recovery-failure',server_revision:saved.revision,original_retained:true,all_inputs_saved:true}));
'''+project[end:]
(planner/'tests/standards-project-storage-failure.test.mjs').write_text(project)
print('Reconstructed four independent test files from the fixed fixture helpers and retained probe deltas.')

prepared=(planner/'tests/standards-storage-warning.test.mjs').read_text();append=(proof/'probe-storage-warning.append.mjs').read_text();assert prepared.endswith(append)
(planner/'tests/standards-correction-boundaries.test.mjs').write_text(prepared[:-len(append)]+(proof/'probe-correction-boundaries.append.mjs').read_text())
