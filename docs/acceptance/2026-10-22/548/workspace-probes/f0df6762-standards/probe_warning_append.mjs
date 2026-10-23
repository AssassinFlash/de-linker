const translated=(message)=>window.wp.i18n.__(message,'linker-tools');
const warningPresent=(message)=>document.body.textContent.includes(translated(message));

function assertStickyRefusal(message) {
 const rows=[...document.querySelectorAll('.lp-navigation-refusal')];
 assert.equal(rows.length,1,'one refusal, without a stale main-content duplicate');
 const bar=document.querySelector('.lp-project-bar');
 assert.ok(bar.contains(rows[0]));
 assert.ok(bar.querySelector('select.lp-mobile-workspace'));
 assert.equal(rows[0].querySelector('.lp-notice').getAttribute('role'),'alert');
 assert.equal(rows[0].textContent.trim(),translated(message));
 assert.equal(document.querySelector('.lp-project-layout .lp-navigation-refusal'),null);
}
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
  assertStickyRefusal('Correct the highlighted input before leaving this project.');
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
  assertStickyRefusal('Finish or cancel roof editing before leaving this workspace.');
  assert.equal(name.value,'Staged original synthetic roof name');
  await warningClick('Cancel properties');
  assert.ok(!warningPresent('Finish or cancel roof editing before leaving this workspace.'));
  assert.ok(!warningPresent('Correct the highlighted input before leaving this project.'));
  await warningChoose('overview');assert.equal(document.querySelector('.lp-project').dataset.workspace,'overview');
  await warningChoose('design');await warningClick('Add module specification');
  assert.equal(stateText(),translated('Roof editing in progress'));
  assert.ok(!warningPresent('Correct the highlighted input before leaving this project.'));
  await warningChoose('site');assertStickyRefusal('Finish or cancel roof editing before leaving this workspace.');
  await warningClick('Cancel properties');
  assert.ok(!warningPresent('Finish or cancel roof editing before leaving this workspace.'));
  await warningChoose('site');assert.equal(document.activeElement.id,'lp-brief-use');
 });
}


test('independent sticky refusal belongs to the observed header and participates in measured height',async(t)=>{
 independentLocale='en-US';
 const observers=new Set();
 const app=await workspaceFixture(t,'available',(fixture)=>{
  // Deliberate synthetic layout values: this proves observer targeting and state,
  // not a browser geometry or touch result.
  Object.defineProperty(fixture.dom.window.HTMLElement.prototype,'offsetHeight',{
   configurable:true,get(){return this.classList.contains('lp-project-bar')?(this.querySelector('.lp-navigation-refusal')?137:72):0;}
  });
  globalThis.ResizeObserver=class {
   constructor(callback){this.callback=callback;this.targets=new Set();observers.add(this);}
   observe(target){this.targets.add(target);}
   disconnect(){this.targets.clear();observers.delete(this);}
  };
 });
 const root=app.fixture.element;
 const resizeBar=()=>{
  const bar=document.querySelector('.lp-project-bar');
  const live=[...observers].filter(observer=>observer.targets.has(bar));
  assert.equal(live.length,1,'exactly the live header is observed');
  live[0].callback();
 };
 assert.equal(root.style.getPropertyValue('--lp-project-bar-height'),'72px');
 await warningChoose('energy');const annual=app.annual();await enter(annual,'1,');
 await warningChoose('overview');
 assertStickyRefusal('Correct the highlighted input before leaving this project.');
 assert.equal(app.annual(),annual);assert.equal(annual.value,'1,');
 resizeBar();assert.equal(root.style.getPropertyValue('--lp-project-bar-height'),'137px');
 await act(async()=>annual.dispatchEvent(new window.KeyboardEvent('keydown',{key:'Escape',bubbles:true})));
 assert.equal(document.querySelector('.lp-navigation-refusal'),null);
 resizeBar();assert.equal(root.style.getPropertyValue('--lp-project-bar-height'),'72px');
});

test('independent failed-recovery refusal uses the same single sticky row and preserves valid edits',async(t)=>{
 independentLocale='en-US';
 const app=await workspaceFixture(t,'unavailable');
 const note=document.querySelector('textarea');await enter(note,'UNSAVED SYNTHETIC STICKY RECOVERY NOTE');
 await until(()=>document.body.textContent.includes('Browser recovery is unavailable'));
 assert.equal(document.querySelector('.lp-navigation-refusal'),null,'storage failure alone is not a refused departure');
 await warningClick('Projects');
 await until(()=>warningPresent('Save the project before leaving. Browser recovery could not be stored.'));
 assertStickyRefusal('Save the project before leaving. Browser recovery could not be stored.');
 assert.equal(document.querySelector('textarea'),note);assert.equal(note.value,'UNSAVED SYNTHETIC STICKY RECOVERY NOTE');
 assert.ok(document.querySelector('.lp-project'));
});
