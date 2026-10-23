const csvOriginal = () => JSON.stringify({schema_version:1,project_id:pid,content_base64:btoa('time;power\n2024-01-01T00:00Z;1\n'),mapping:{timestamp_column:'time',value_column:'power',measurement:'net_import',value_kind:'interval_average_kw',timestamp_role:'start',timezone:'Europe/Oslo',origin:'synthetic',interval_seconds:900,delimiter:';',decimal:'.',end_timestamp_column:null,fold_column:null,end_fold_column:null,offset_rule:'explicit_offset_precedes_naive_timezone',within_interval_assumption:'constant_mean_no_new_observations'},source_label:'Independent retained CSV',rights_note:'Own test original',key:crypto.randomUUID()});

test('followup: zero datum preserves rejected height through prepare, unchecking, correction and a new explicit request', async t => {
  for(const value of ['', '1,']) await t.test(value === '' ? 'required blank' : 'invalid EN decimal',async st=>{
    const app=await mount(st,{mode:'intake',locale:'en-GB',onReply:()=>refused('invalid_input')});
    await click('Import roof geometry');await upload();await click('Continue');
    await enter(field('pitch'),'30');await enter(field('bearing'),'180');await enter(field('basis'),'Declared drawing height reference');if(value)await enter(field('height'),value);
    await click('Continue');const height=field('height');assert.equal(height.validity.customError,true);
    const zero=document.querySelector('[data-import-step="1"] input[type=checkbox]');await act(async()=>zero.click());await click('Continue');
    assert.equal(height.value,value);assert.equal(height.validity.customError,true);assert.equal(field('height'),height);
    await enter(field('source'),'Independent original');await enter(field('rights'),'Private retention and derivation permitted');await act(async()=>field('retention').click());
    await click('Prepare roof preview');await until(()=>app.uploads.length===1&&!button('Prepare roof preview').disabled);
    assert.equal(JSON.parse(app.uploads[0].body).options.plane.origin_enu[2],0);assert.equal(JSON.parse(app.uploads[0].body).options.source.spatial_precision_m,null);
    await click('Back');await act(async()=>zero.click());assert.equal(height.value,value);assert.equal(height.validity.customError,true);await click('Continue');
    assert.equal(document.querySelector('[data-import-step="1"]').hidden,false);assert.equal(app.uploads.length,1,'hidden zero-datum override does not silently fix the rejected raw height');
    await enter(height,'-2.5');await click('Continue');await click('Prepare roof preview');await until(()=>app.uploads.length===2&&!button('Prepare roof preview').disabled);
    const before=JSON.parse(app.uploads[0].body),after=JSON.parse(app.uploads[1].body);assert.notEqual(before.key,after.key);assert.equal(after.options.plane.origin_enu[2],-2.5);assert.equal(field('height'),height);assert.equal(height.value,'-2.5');assert.equal(after.content_base64,before.content_base64);
  });
});

test('followup: unusable replies retain exact originals in both actual IndexedDB stores until typed correction', async t => {
  for(const mode of ['hook','csv'])for(const [status,payload]of [[200,null],[422,[]],[500,{}],[502,null]])await t.test(mode+' HTTP'+status,async st=>{
    const body=csvOriginal(),app=await mount(st,{mode,onReply:()=>response(payload,status),...(mode==='csv'?{seed:async(_journal,store)=>store.writeProfileImport(scope,body)}:{})});
    if(mode==='hook'){
      await act(async()=>app.flow.prepare(request()));assert.equal(app.flow.asset,null);assert.ok(app.flow.intent);const original=app.uploads[0].body;
      assert.equal((await readDB(new GeometryImportStore(),'list',[scope],pid))[0].body,original);
      app.reply(()=>refused('invalid_input'));await act(async()=>app.flow.retry(app.flow.intent));assert.equal(app.uploads[1].body,original);assert.equal(app.flow.intent,null);assert.deepEqual(await readDB(new GeometryImportStore(),'list',[scope],pid),[]);
    }else{
      await until(()=>button('Check or retry this import'));await click('Check or retry this import');await until(()=>app.csv.length===1&&!button('Check or retry this import').disabled);
      assert.equal(app.csv[0],body);assert.equal((await readDB(new DraftStore(),'readProfileImports',scope,pid))[0].body,body);
      app.reply(()=>refused('invalid_input'));await click('Check or retry this import');await until(()=>!button('Check or retry this import'));
      assert.equal(app.csv[1],body);assert.deepEqual(await readDB(new DraftStore(),'readProfileImports',scope,pid),[]);assert.ok(document.querySelector('input[type=file]'));
    }
  });
});

test('followup: Unicode display boundary keeps complete characters and immutable original selection',async t=>{
  for(const key of ['name','id'])for(const suffix of ['🙂','🙂Z'])await t.test(key+' '+suffix,async st=>{
    const original=JSON.parse(raw),name='a'.repeat(255)+suffix;if(key==='name')original.properties={name};else{original.properties={};original.id=name;}
    const bytes=Buffer.from(JSON.stringify(original)),app=await mount(st,{mode:'intake',locale:'de-DE',onReply:()=>refused('invalid_input')});
    await click('Import roof geometry');await upload(bytes);const shown='a'.repeat(255)+(suffix==='🙂'?'🙂':'…');
    assert.equal(field('roof').value,shown);assert.equal(field('roof').value.isWellFormed(),true);assert.equal(Array.from(field('roof').value).length,256);assert.equal(field('selection').value,'0:0');assert.equal(field('selection').selectedOptions[0].textContent,shown+' · face 1');
    await click('Continue');await fillPlane();await fillSource();await click('Prepare roof preview');await until(()=>app.uploads.length===1&&!button('Prepare roof preview').disabled);
    const sent=JSON.parse(app.uploads[0].body);assert.equal(sent.content_base64,bytes.toString('base64'));assert.equal(sent.options.feature_index,0);assert.equal(sent.options.polygon_index,0);assert.equal(sent.options.roof_name,shown);
  });
});

const deMessages=JSON.parse(readFileSync(new URL('../../../plugins/linker-tools/languages/linker-tools-de_DE_formal-cf89287c9001d7518d0d20e58c3eb721.json',import.meta.url),'utf8')).locale_data.messages;
const de=key=>deMessages[key]?.[0]??key;
async function german(app){window.wp.i18n.__=(key)=>de(key);await app.render();}
async function germanFile(bytes=raw){
  const input=document.querySelector('.lp-geometry-intake input[type=file]');
  await act(async()=>{Object.defineProperty(input,'files',{value:[{name:'Messung original.geojson',size:bytes.length,arrayBuffer:async()=>Uint8Array.from(bytes).buffer}],configurable:true});input.dispatchEvent(new window.Event('change',{bubbles:true}));});
  await until(()=>!button(de('Close import')).disabled);
}

test('followup: fixed German catalog supplies file labels and required-retention feedback without native-language text',async t=>{
  const app=await mount(t,{mode:'intake',locale:'de-DE',onReply:()=>refused('invalid_input')});await german(app);await click(de('Import roof geometry'));
  for(const key of ['Choose file','No file selected','Roof file','Complete this field to continue.'])assert.ok(deMessages[key]?.[0],key+' has a deployed JSON message');
  const input=document.querySelector('.lp-geometry-intake input[type=file]');assert.equal(document.getElementById(input.getAttribute('aria-labelledby')).textContent,de('Roof file'));
  const descriptions=input.getAttribute('aria-describedby').split(/\s+/).map(id=>document.getElementById(id));assert.equal(descriptions.length,2);assert.ok(descriptions.every(Boolean));assert.equal(descriptions[0].textContent,de('No file selected'));assert.equal(document.querySelector('.lp-geometry-intake .lp-file-button').textContent,de('Choose file'));
  await germanFile();assert.equal(document.querySelector('.lp-geometry-intake input[type=file]'),input);assert.equal(descriptions[0].textContent,'Messung original.geojson');
  await click(de('Continue'));await enter(field('pitch'),'30,5');await enter(field('bearing'),'180');await enter(field('height'),'5');await enter(field('basis'),'Zeichnung als Höhenbezug');await click(de('Continue'));
  await enter(field('source'),'Eigene Messung');await enter(field('rights'),'Privat speichern und Dachgeometrie ableiten');await click(de('Prepare roof preview'));
  assert.equal(field('retention').validationMessage,de('Complete this field to continue.'));assert.equal(field('retention').validity.customError,true);assert.equal(app.uploads.length,0);
  await act(async()=>field('retention').click());assert.equal(field('retention').validationMessage,'');await click(de('Prepare roof preview'));await until(()=>app.uploads.length===1&&!button(de('Prepare roof preview')).disabled);
  assert.equal(JSON.parse(app.uploads[0].body).options.source.spatial_precision_m,null);
});

test('followup: accepted area and unknown precision remain exact in the prepared object',async t=>{
  const app=await mount(t);await act(async()=>app.flow.prepare(request()));await until(()=>app.flow.asset!==null&&!app.flow.busy);
  assert.equal(app.flow.asset.areaM2,accepted.metadata.geometry_import.area_roof_plane_m2);assert.equal(app.flow.asset.options.source.spatial_precision_m,null);assert.equal(app.flow.asset.geometry.sources[0].spatial_precision_m,null);assert.equal((await readDB(app.journal,'list',[scope],pid)).length,1);
});

test('followup: German preview rounds display only and retains its opening and unknown-precision detail',async t=>{
  const body=JSON.stringify(request()),app=await mount(t,{mode:'intake',locale:'de-DE',seed:async journal=>journal.write(scope,body)});await german(app);await until(()=>button(options.source.label));await click(options.source.label);await click(de('Check or retry this upload'));await until(()=>button(de('Add roof to current design'))&&!button(de('Add roof to current design')).disabled);
  const term=[...document.querySelectorAll('.lp-import-review dt')].find(el=>el.textContent===de('Roof-plane area'));assert.ok(term);assert.equal(term.parentElement.querySelector('dd').textContent.trim(),new Intl.NumberFormat('de-DE',{maximumFractionDigits:2}).format(accepted.metadata.geometry_import.area_roof_plane_m2)+' m²');
  assert.ok(document.querySelector('.lp-import-review svg path[fill-rule="evenodd"]'));assert.ok(document.querySelector('.lp-import-panel details').textContent.includes(de('Unknown')));assert.equal((await readDB(app.journal,'list',[scope],pid)).length,1);assert.equal((await readDB(app.journal,'list',[scope],pid))[0].body,body);
});
