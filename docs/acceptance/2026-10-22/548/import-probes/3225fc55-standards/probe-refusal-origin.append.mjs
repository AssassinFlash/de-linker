for (const responseStatus of [200, 422, 500]) {
 test(`independent malformed ${responseStatus} response retains the committed original as an unknown result`,async(t)=>{
  const fixture=await rig(t,{replyOverride:[],replyStatus:responseStatus});
  const request=command();
  await act(async()=>fixture.flow.prepare(request));
  const records=await fixture.journal.list([scope],projectId);
  console.log(JSON.stringify({probe:'response-origin',response_status:responseStatus,upload_count:fixture.uploads.length,error_code:fixture.flow.error?.code,error_status:fixture.flow.error?.status,intent_retained:fixture.flow.intent!==null,journal_count:records.length,original_key:request.key}));
  assert.equal(fixture.uploads.length,1,'a real client dispatch occurred after the committed recovery write');
  assert.equal(records.length,1,'an unusable response is not evidence of a pre-mutation input refusal');
  assert.equal(records[0].key,request.key);
  assert.equal(fixture.flow.intent.body,fixture.uploads[0]);
 });
}
test('independent identified input refusal still releases the committed original',async(t)=>{
 const fixture=await rig(t,{refusal:'invalid_input'});
 await act(async()=>fixture.flow.prepare(command()));
 assert.equal(fixture.uploads.length,1);
 assert.equal(fixture.flow.intent,null);
 assert.deepEqual(await fixture.journal.list([scope],projectId),[]);
});
