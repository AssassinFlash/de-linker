const independentNav=(label)=>[...document.querySelectorAll('nav[aria-label="Project sections"] a')].find(link=>link.textContent.trim()===label);
for(const [hash,expected] of [['#lp-brief-use','site'],['#lp-notes','site'],['#lp-profiles','energy'],['#lp-design','design'],['#unrecognised','overview']]){
 test('independent existing URL alias opens its workspace '+hash,async(t)=>{
  await workspaceFixture(t,'available',()=>history.replaceState(null,'',hash));
  assert.equal(document.querySelector('.lp-project').dataset.workspace,expected);
  assert.equal(document.querySelectorAll('nav[aria-label="Project sections"] [aria-current="page"]').length,1);
 });
}
test('independent unapplied roof form blocks navigation and cancellation restores it',async(t)=>{
 await workspaceFixture(t,'available');
 await act(async()=>independentNav('Roof design').click());
 assert.equal(document.activeElement.id,'lp-design');
 const add=[...document.querySelectorAll('button')].find(x=>x.textContent.trim()==='Add roof face');
 await act(async()=>add.click());
 const name=document.querySelector('[name="name"]');await enter(name,'Independent unapplied roof');
 await act(async()=>independentNav('Project overview').click());
 assert.equal(document.querySelector('.lp-project').dataset.workspace,'design');
 assert.equal(document.querySelector('[name="name"]'),name);
 assert.equal(name.value,'Independent unapplied roof');
 const cancel=[...document.querySelectorAll('button')].find(x=>x.textContent.trim()==='Cancel properties');
 assert.ok(cancel);await act(async()=>cancel.click());
 await act(async()=>independentNav('Project overview').click());
 assert.equal(document.querySelector('.lp-project').dataset.workspace,'overview');
 assert.equal(document.activeElement.id,'lp-overview');
});
