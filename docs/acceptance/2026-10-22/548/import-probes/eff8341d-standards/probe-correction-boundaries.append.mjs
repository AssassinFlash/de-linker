const text=(value)=>window.wp.i18n.__(value,'linker-tools');
const findButton=(label)=>[...document.querySelectorAll('button')].find(node=>node.textContent.trim()===text(label));
const input=(name)=>document.querySelector(`[name="${name}"]`);
async function press(label){assert.ok(findButton(label),label);await act(async()=>findButton(label).click());}
async function chooseOriginal(){
 await act(async()=>{
  const control=document.querySelector('input[type="file"]');
  Object.defineProperty(control,'files',{value:[{name:'Independent original.geojson',size:source.length,arrayBuffer:async()=>Uint8Array.from(source).buffer}]});
  control.dispatchEvent(new window.Event('change',{bubbles:true}));
 });
 await until(()=>findButton('Continue')&&!findButton('Continue').disabled);
}
for(const locale of ['en-GB','de-DE']){
 for(const rawKind of ['empty','invalid']){
  test('independent zero-height bypass keeps original raw validity and localized rights guidance '+locale+' '+rawKind,async(t)=>{
   const fixture=await rig(t,{intake:true,locale,refusal:'invalid_input'});
   await press('Import roof geometry');
   const file=document.querySelector('input[type="file"]');
   assert.equal(document.getElementById(file.getAttribute('aria-labelledby')).textContent,text('Roof file'));
   assert.equal(document.querySelector('.lp-file-button').textContent,text('Choose file'));
   assert.equal(document.querySelector('.lp-file-button').getAttribute('aria-hidden'),'true');
   assert.equal(document.querySelector('.lp-file-name').textContent,text('No file selected'));
   for(const id of file.getAttribute('aria-describedby').split(/\s+/))assert.ok(document.getElementById(id));
   await chooseOriginal();assert.equal(document.querySelector('.lp-file-name').textContent,'Independent original.geojson');
   await press('Continue');
   await enter(input('pitch'),locale.startsWith('de')?'30,5':'30.5');
   await enter(input('bearing'),'180');await enter(input('basis'),'Independent synthetic roof-plane basis');
   const raw=rawKind==='empty'?'':locale.startsWith('de')?'1,,':'1,';
   if(raw)await enter(input('height'),raw);
   const height=input('height');await press('Continue');
   assert.equal(document.querySelector('[data-import-step="1"]').hidden,false);
   assert.ok(height.validationMessage);
   const zero=document.querySelector('input[type="checkbox"]:not([name])');await act(async()=>zero.click());
   await press('Continue');assert.equal(document.querySelector('[data-import-step="2"]').hidden,false);
   assert.equal(height.value,raw);assert.ok(height.validationMessage,'the hidden original error is retained');
   await enter(input('source'),'Independent synthetic source');await enter(input('rights'),'Synthetic original; permission to derive and retain both privately');
   await press('Prepare roof preview');
   assert.equal(input('retention').validationMessage,text('Complete this field to continue.'));
   assert.deepEqual(fixture.uploads,[]);
   await act(async()=>input('retention').click());await press('Prepare roof preview');
   await until(()=>fixture.uploads.length===1&&!findButton('Prepare roof preview').disabled);
   const uploaded=JSON.parse(fixture.uploads[0]);assert.equal(uploaded.options.plane.origin_enu[2],0);
   assert.equal(uploaded.options.source.spatial_precision_m,null);assert.equal(uploaded.content_base64,source.toString('base64'));
   assert.equal(height.value,raw);
   await press('Back');await act(async()=>zero.click());await press('Continue');
   assert.equal(document.querySelector('[data-import-step="1"]').hidden,false);
   assert.equal(input('height'),height);assert.equal(height.value,raw);assert.ok(height.validationMessage);
   assert.equal(fixture.uploads.length,1);
   console.log(JSON.stringify({probe:'zero-height-and-site-language',locale,rawKind,height_zero_sent_only_after_explicit_choice:true,original_raw_and_validity_retained:true,unchecked_rights_blocked:true,site_picker_and_checkbox_words:true}));
  });
 }
 test('independent preview rounding is presentation only and leaves accepted area unchanged '+locale,async(t)=>{
  const fixture=await rig(t,{intake:true,locale}),body=JSON.stringify(command());
  await fixture.journal.write(scope,body);await fixture.render({confirmedAssetIds:['f'.repeat(32)]});
  await until(()=>findButton(asset.metadata.geometry_import_options.source.label));
  await press(asset.metadata.geometry_import_options.source.label);await press('Check or retry this upload');
  await until(()=>findButton('Add roof to current design')&&!findButton('Add roof to current design').disabled);
  const dd=document.querySelector('.lp-import-review .lp-field-summary > div:first-child dd');
  const shown=dd.textContent.replace(/\s*m²$/,'').trim();
  const normalized=locale.startsWith('de')?shown.replaceAll('.','').replace(',','.'):shown.replaceAll(',','');
  assert.ok(/^\d+(?:\.\d{1,2})?$/.test(normalized));
  const exact=asset.metadata.geometry_import.area_roof_plane_m2;
  // Half of one displayed hundredth plus binary64 comparison slack; this is
  // display verification, not an engineering/source-accuracy tolerance.
  assert.ok(Math.abs(Number(normalized)-exact)<=0.0050000001);
  await press('Add roof to current design');assert.equal(fixture.attachments[0].prepared.areaM2,exact);
  console.log(JSON.stringify({probe:'area-presentation',locale,shown,accepted_area_unchanged:true}));
 });
}
