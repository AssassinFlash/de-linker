const mobileWorkspace=()=>document.querySelector('select.lp-mobile-workspace');
const currentWorkspace=()=>document.querySelector('.lp-project').dataset.workspace;
async function mobileChoose(value){
 await act(async()=>{const select=mobileWorkspace();select.value=value;select.dispatchEvent(new window.Event('change',{bubbles:true}));});
}
test('independent mobile selector shares workspace/hash/input nodes and reveals the first Site section',async(t)=>{
 const app=await workspaceFixture(t,'available');
 const annual=app.annual();
 assert.equal(mobileWorkspace().value,'overview');
 const targets={site:'lp-brief-use',design:'lp-design',energy:'lp-load',overview:'lp-overview'};
 for(const [value,target] of Object.entries(targets)){
  await mobileChoose(value);
  assert.equal(currentWorkspace(),value);
  assert.equal(mobileWorkspace().value,value);
  assert.equal(document.activeElement.id,target);
  assert.equal(app.annual(),annual);
  assert.equal(document.querySelectorAll('nav[aria-label="Project sections"] [aria-current="page"]').length,1);
 }
 await mobileChoose('site');assert.equal(location.hash,'#lp-site');assert.equal(document.activeElement.id,'lp-brief-use');
});
test('independent mobile selector refuses invalid annual raw value and follows correction without losing it',async(t)=>{
 const app=await workspaceFixture(t,'available');
 await mobileChoose('energy');const annual=app.annual();await enter(annual,'1,');
 const beforeHash=location.hash;
 await mobileChoose('site');
 assert.equal(currentWorkspace(),'energy');assert.equal(mobileWorkspace().value,'energy');
 assert.equal(annual.value,'1,');assert.equal(app.annual(),annual);assert.equal(location.hash,beforeHash);
 await enter(annual,'21');await mobileChoose('site');
 assert.equal(currentWorkspace(),'site');assert.equal(annual.value,'21');assert.equal(document.activeElement.id,'lp-brief-use');
});
test('independent mobile selector cannot hide an unapplied roof form and resumes after cancel',async(t)=>{
 await workspaceFixture(t,'available');await mobileChoose('design');
 await act(async()=>[...document.querySelectorAll('button')].find(x=>x.textContent.trim()==='Add roof face').click());
 const name=document.querySelector('[name="name"]');await enter(name,'Retained staged synthetic name');
 await mobileChoose('overview');
 assert.equal(currentWorkspace(),'design');assert.equal(mobileWorkspace().value,'design');
 assert.equal(name.value,'Retained staged synthetic name');assert.equal(document.querySelector('[name="name"]'),name);
 await act(async()=>[...document.querySelectorAll('button')].find(x=>x.textContent.trim()==='Cancel properties').click());
 await mobileChoose('overview');assert.equal(currentWorkspace(),'overview');
});
test('independent mobile selector obeys immediate native scope fence before a React recheck render',async(t)=>{
 const app=await workspaceFixture(t,'available');
 const beforeHash=location.hash;const beforeWorkspace=currentWorkspace();const annual=app.annual();
 app.client.invalidate();
 await mobileChoose('energy');
 assert.equal(currentWorkspace(),beforeWorkspace);assert.equal(location.hash,beforeHash);
 assert.equal(app.annual(),annual);assert.equal(mobileWorkspace().value,beforeWorkspace);
});
