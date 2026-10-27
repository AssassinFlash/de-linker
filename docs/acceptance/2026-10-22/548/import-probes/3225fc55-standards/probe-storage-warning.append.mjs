const translated=(value)=>window.wp.i18n.__(value,'linker-tools');
const chosenButton=(label)=>[...document.querySelectorAll('button')].find(node=>node.textContent.trim()===translated(label));
async function chooseButton(label){assert.ok(chosenButton(label),label);await act(async()=>chosenButton(label).click());}
const warningMessage='Browser recovery could not be read or updated. An upload starts only after a recovery copy of its original file and settings is saved. Project versions already saved on the server are unchanged.';
for(const locale of ['en-GB','de-DE']){
 test('independent recovery-update failure still allows confirmed preview and explicit adoption '+locale,async(t)=>{
  const fixture=await rig(t,{intake:true,locale});
  const body=JSON.stringify(command());await fixture.journal.write(scope,body);
  await fixture.render({confirmedAssetIds:['f'.repeat(32)]});
  await until(()=>chosenButton(asset.metadata.geometry_import_options.source.label));
  const originalList=fixture.store.list;let failedAck=false;
  fixture.store.acknowledge=async()=>{failedAck=true;throw new Error('synthetic_local_ack_failure');};
  fixture.store.list=async(...args)=>{if(failedAck)throw new Error('synthetic_local_read_failure');return originalList(...args);};
  await chooseButton(asset.metadata.geometry_import_options.source.label);
  await chooseButton('Check or retry this upload');
  await until(()=>chosenButton('Add roof to current design')&&!chosenButton('Add roof to current design').disabled);
  await until(()=>document.body.textContent.includes(translated(warningMessage)));
  assert.equal(fixture.uploads.length,1);
  assert.ok(document.querySelector('.lp-import-review svg'));
  assert.ok(!document.body.textContent.includes('this upload cannot continue'));
  await chooseButton('Add roof to current design');
  assert.equal(fixture.attachments.length,1);
  assert.equal(fixture.attachments[0].prepared.id,asset.id);
  const retained=await fixture.journal.list([scope],projectId);assert.equal(retained.length,1);assert.equal(retained[0].body,body);
  console.log(JSON.stringify({probe:'recovery-copy',locale,confirmed_preview:true,explicit_adoption:true,original_retained:true,warning:translated(warningMessage)}));
 });
}
test('independent concurrent quota decisions preserve the first committed originals without eviction',async(t)=>{
 const fixture=await rig(t);const bodies=Array.from({length:33},()=>JSON.stringify(command()));
 const results=await Promise.allSettled(bodies.map(body=>fixture.journal.write(scope,body)));
 assert.equal(results.filter(value=>value.status==='fulfilled').length,32);
 assert.equal(results.filter(value=>value.status==='rejected').length,1);
 const records=await fixture.journal.list([scope],projectId);assert.equal(records.length,32);
 for(let i=0;i<results.length;i++)if(results[i].status==='fulfilled')assert.ok(records.some(record=>record.body===bodies[i]));
});
