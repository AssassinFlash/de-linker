const translated=(message)=>window.wp.i18n.__(message,'linker-tools');
const warningPresent=(message)=>document.body.textContent.includes(translated(message));
const stateText=()=>document.querySelector('.lp-save-state').textContent;
async function warningChoose(value){await act(async()=>{const field=document.querySelector('select.lp-mobile-workspace');field.value=value;field.dispatchEvent(new window.Event('change',{bubbles:true}));});}
async function warningClick(message){const button=[...document.querySelectorAll('button')].find(x=>x.textContent.trim()===translated(message));assert.ok(button,'Missing '+message);await act(async()=>button.click());}
for(const locale of ['en-US','de-DE']){
 test('independent stale refusal stays cleared and staged roof/module wording remains accurate '+locale,async(t)=>{
  independentLocale=locale;
  const app=await workspaceFixture(t,'available',()=>{
   if(locale.startsWith('de'))window.wp.i18n.__=(message)=>independentCatalog[message]?.[0]||message;
  });
  await warningChoose('energy');const annual=app.annual();await enter(annual,locale.startsWith('de')?'1,,':'1,');
  await warningChoose('overview');
  assert.equal(document.querySelector('.lp-project').dataset.workspace,'energy');
  assert.ok(warningPresent('Correct the highlighted input before leaving this project.'));
  await act(async()=>annual.dispatchEvent(new window.KeyboardEvent('keydown',{key:'Escape',bubbles:true})));
  assert.equal(annual.value,'10');
  assert.ok(!warningPresent('Correct the highlighted input before leaving this project.'));
  await enter(annual,'20');
  const undo=[...document.querySelectorAll('button')].find(x=>x.getAttribute('aria-label')===translated('Undo'));
  assert.ok(undo);await act(async()=>undo.click());assert.equal(annual.value,'10');
  await warningChoose('design');
  await warningClick('Add roof face');
  assert.equal(stateText(),translated('Roof editing in progress'));
  assert.ok(!warningPresent('Correct the highlighted input before leaving this project.'));
  assert.ok(!warningPresent('Finish or cancel roof editing before leaving this workspace.'));
  const name=document.querySelector('[name="name"]');await enter(name,'Staged original synthetic roof name');
  await warningChoose('overview');
  assert.equal(document.querySelector('.lp-project').dataset.workspace,'design');
  assert.ok(warningPresent('Finish or cancel roof editing before leaving this workspace.'));
  assert.equal(name.value,'Staged original synthetic roof name');
  await warningClick('Cancel properties');
  assert.ok(!warningPresent('Finish or cancel roof editing before leaving this workspace.'));
  assert.ok(!warningPresent('Correct the highlighted input before leaving this project.'));
  await warningChoose('overview');assert.equal(document.querySelector('.lp-project').dataset.workspace,'overview');
  await warningChoose('design');await warningClick('Add module specification');
  assert.equal(stateText(),translated('Roof editing in progress'));
  assert.ok(!warningPresent('Correct the highlighted input before leaving this project.'));
  await warningChoose('site');assert.ok(warningPresent('Finish or cancel roof editing before leaving this workspace.'));
  await warningClick('Cancel properties');
  assert.ok(!warningPresent('Finish or cancel roof editing before leaving this workspace.'));
  await warningChoose('site');assert.equal(document.activeElement.id,'lp-brief-use');
 });
}
