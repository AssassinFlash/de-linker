import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {test} from 'node:test';
const require=createRequire(import.meta.url);
const {JSDOM}=require('../../../linker-tools/node_modules/jsdom');
const script=readFileSync(new URL('../../assets/account-ui.js',import.meta.url),'utf8');

function account(){
 const dom=new JSDOM(`<div class="linker-auth"><form method="post" id="signin" novalidate>
 <input type="text" name="username" required>
 <button type="submit" name="login">Log in</button>
 </form></div>`,{runScripts:'outside-only'});
 dom.window.eval(script);
 return dom.window;
}

function resetForm(){
 const dom=new JSDOM(`<div class="linker-auth"><form method="post" class="woocommerce-ResetPassword lost_reset_password">
 <input type="password" id="password_1" name="password_1" required>
 <input type="password" id="password_2" name="password_2" required>
 <span class="linker-auth-error" id="linker-reset-mismatch" data-password-mismatch role="alert" hidden>mismatch</span>
 <button type="submit">Save</button>
 </form></div>`,{runScripts:'outside-only'});
 dom.window.eval(script);
 return dom.window;
}

function submit(form){
 const event=form.ownerDocument.createEvent('Event');
 event.initEvent('submit',true,true);
 form.dispatchEvent(event);
 return event;
}

test('a submitted account form marks its button as loading, and never disables it',()=>{
 const win=account();
 const button=win.document.querySelector('button[type="submit"]');
 win.document.querySelector('[name="username"]').value='maria@muster-solar.de';
 submit(win.document.getElementById('signin'));
 assert.equal(button.classList.contains('is-loading'),true);
 assert.equal(button.getAttribute('aria-busy'),'true');
 // WooCommerce reads the pressed button's own name and value, and a disabled
 // control is left out of the submission.
 assert.equal(button.disabled,false);
});

test('a second submit while the first is in flight does not post again',()=>{
 const win=account();
 const form=win.document.getElementById('signin');
 form.querySelector('[name="username"]').value='maria@muster-solar.de';
 const first=submit(form);
 assert.equal(first.defaultPrevented,false);
 const second=submit(form);
 assert.equal(second.defaultPrevented,true);
 assert.equal(form.dataset.accountState,'submitting');
});

test('protected inquiry/account marks busy only on the verified native resubmit',()=>{
 const win=account();
 const form=win.document.getElementById('signin');
 form.querySelector('[name="username"]').value='fixture@example.test';
 const marker=win.document.createElement('input');
 marker.type='hidden';
 marker.dataset.linkerProtectedAction='registration';
 form.append(marker);
 win.linkerPublicProtectionConfig={mode:'enforce'};
 const pending=submit(form);
 assert.equal(pending.defaultPrevented,false,'the protection layer may wait before actual submission');
 assert.equal(form.dataset.accountState,undefined,'verification is not an account submission');
 form.dataset.linkerProtectionVerified='true';
 const verified=submit(form);
 assert.equal(verified.defaultPrevented,false,'verified native submit must not be mistaken for a duplicate');
 assert.equal(form.dataset.accountState,'submitting');
});

test('a native Woo novalidate form reports missing fields and stays on the page',()=>{
 const win=account();
 const button=win.document.querySelector('button[type="submit"]');
 const form=win.document.getElementById('signin');
 // jsdom reports an empty required field as invalid, the same as the browser.
 assert.equal(form.checkValidity(),false);
 assert.equal(form.noValidate,true,'Woo delegates its login validation to the submit path');
 let reported=false;
 form.reportValidity=()=>{reported=true;return false;};
 const event=submit(form);
 assert.equal(event.defaultPrevented,true,'invalid novalidate forms must not reach the server');
 assert.equal(reported,true,'the customer must be directed to the missing field');
 assert.equal(form.dataset.accountState,undefined);
 assert.equal(button.classList.contains('is-loading'),false);
});

test('two different passwords keep the form on the page and name the mismatch',()=>{
 const win=resetForm();
 const form=win.document.querySelector('form');
 form.querySelector('#password_1').value='Muster-Solar-2026';
 form.querySelector('#password_2').value='Muster-Solar-2025';
 const event=submit(form);
 assert.equal(event.defaultPrevented,true);
 const error=win.document.getElementById('linker-reset-mismatch');
 assert.equal(error.hidden,false);
 assert.equal(form.querySelector('#password_2').getAttribute('aria-invalid'),'true');
 assert.equal(form.querySelector('#password_2').getAttribute('aria-describedby'),'linker-reset-mismatch');
 assert.equal(form.querySelector('button[type="submit"]').classList.contains('is-loading'),false);
});

test('a blocked mismatch clears the disabled state WooCommerce\'s own script leaves',async()=>{
 const win=resetForm();
 const form=win.document.querySelector('form');
 const button=form.querySelector('button[type="submit"]');
 // WooCommerce's own frontend/lost-password.js disables the reset form's
 // button on every submit, assuming the page is leaving.
 form.addEventListener('submit',()=>{button.disabled=true;});
 form.querySelector('#password_1').value='Muster-Solar-2026';
 form.querySelector('#password_2').value='Muster-Solar-2025';
 const event=submit(form);
 assert.equal(event.defaultPrevented,true);
 assert.equal(button.disabled,true,'the third-party handler ran after this file');
 await new Promise((resolve)=>win.setTimeout(resolve,0));
 assert.equal(button.disabled,false,'the corrected attempt can post again');
});

test('the mismatch line follows the typing and clears when they agree',()=>{
 const win=resetForm();
 const first=win.document.querySelector('#password_1');
 const second=win.document.querySelector('#password_2');
 const error=win.document.getElementById('linker-reset-mismatch');
 first.value='Muster-Solar-2026';
 second.value='Muster-Solar-2025';
 second.dispatchEvent(new win.Event('input',{bubbles:true}));
 assert.equal(error.hidden,false);
 second.value='Muster-Solar-2026';
 second.dispatchEvent(new win.Event('input',{bubbles:true}));
 assert.equal(error.hidden,true);
 assert.equal(second.hasAttribute('aria-invalid'),false);
});

test('agreeing passwords post the form',()=>{
 const win=resetForm();
 const form=win.document.querySelector('form');
 form.querySelector('#password_1').value='Muster-Solar-2026';
 form.querySelector('#password_2').value='Muster-Solar-2026';
 const event=submit(form);
 assert.equal(event.defaultPrevented,false);
 assert.equal(form.querySelector('button[type="submit"]').classList.contains('is-loading'),true);
});

function inquiryDraft({saved=[],context='same-auth-session',nonce='first-nonce-tick',retained=false,storageUnavailable=false,closed=false,defaultName='',defaultEmail=''}={}){
 const dom=new JSDOM(`<div class="linker-inquiry">
 <form class="linker-inquiry-form" data-inquiry-context="${context}"><input type="hidden" name="linker_inquiry_nonce" value="${nonce}"><input type="hidden" name="linker_inquiry_retained" value="${retained?'1':'0'}">
 <textarea name="message"></textarea><details class="linker-inquiry-details" ${closed?'':'open'}><summary><small>${defaultName} · ${defaultEmail}</small></summary><input name="name" value="${defaultName}"><input name="email" type="email" value="${defaultEmail}"><input name="company"></details><input type="checkbox" name="consent">
 <p data-inquiry-draft-pending hidden role="status">Update the solution draft before sending your inquiry.</p>
 <p data-inquiry-retention-error hidden role="alert" tabindex="-1">Your browser could not keep your entries.</p>
 <button type="submit">Send inquiry</button></form>
 <aside><form class="woocommerce-cart-form"><input class="qty" name="cart[line][qty]" type="number" min="0" step="1" value="1"><button type="submit" name="update_cart">Update solution draft</button></form>
 <a data-inquiry-edit href="/cart/">Edit solution draft</a></aside></div><nav><a lang="de" href="/de/proforma-anfrage/">DE</a></nav>`,{runScripts:'outside-only',url:'https://example.test/proforma-request/'});
 const win=dom.window;
 for(const [key,value] of saved)win.sessionStorage.setItem(key,value);
 if(storageUnavailable)Object.defineProperty(win,'sessionStorage',{get(){throw new Error('Storage unavailable');}});
 win.eval(script);
 const form=win.document.querySelector('.linker-inquiry-form');
 return {win,form,draft:win.document.querySelector('.woocommerce-cart-form'),send:form.querySelector('button'),field:(name)=>form.querySelector(`[name="${name}"]`)};
}

test('standalone draft blocks stale continuation until native readback, preserving the inquiry edit bridge',async()=>{
 const dom=new JSDOM(`<div id="tv-storefront-cart">
 <p id="draft-pending" data-inquiry-draft-pending role="status" tabindex="-1" hidden>Update the solution draft before sending your inquiry.</p>
 <form class="woocommerce-cart-form"><input class="qty" name="cart[line][qty]" type="number" min="0" step="1" value="1"><button name="update_cart">Update solution draft</button></form>
 <div class="wc-proceed-to-checkout"><a href="/proforma-request/">Send inquiry</a></div></div>`,{runScripts:'outside-only',url:'https://example.test/cart/'});
 const win=dom.window;const kept='existing inquiry entries';win.sessionStorage.setItem('linker-inquiry-edit',kept);win.eval(script);
 const draft=win.document.querySelector('form'),quantity=draft.querySelector('.qty'),link=win.document.querySelector('a'),notice=win.document.querySelector('[role="status"]');
 const activate=()=>{const event=new win.MouseEvent('click',{bubbles:true,cancelable:true});link.dispatchEvent(event);return event;};
 assert.equal(win.sessionStorage.getItem('linker-inquiry-edit'),kept);
 assert.equal(link.getAttribute('aria-disabled'),'false');
 for(const value of ['2','0','']){
  quantity.value=value;quantity.dispatchEvent(new win.Event('input',{bubbles:true}));
  assert.equal(link.getAttribute('aria-disabled'),'true');assert.equal(notice.hidden,false);
  assert.equal(activate().defaultPrevented,true);assert.equal(win.document.activeElement.name,'update_cart');
 }
 quantity.value='1';quantity.dispatchEvent(new win.Event('change',{bubbles:true}));
 assert.equal(link.getAttribute('aria-disabled'),'false');assert.equal(notice.hidden,true);
 draft.classList.add('processing');draft.querySelector('button').disabled=true;await Promise.resolve();assert.equal(activate().defaultPrevented,true,'native processing also blocks continuation');assert.equal(notice.hidden,false);assert.equal(win.document.activeElement,notice,'a disabled update action focuses its visible status instead');draft.querySelector('button').disabled=false;
 quantity.value='2';draft.classList.remove('processing');await Promise.resolve();assert.equal(link.getAttribute('aria-disabled'),'true','a failed native update keeps the edit blocked');
 const replacement=draft.cloneNode(true);replacement.querySelector('.qty').setAttribute('value','2');draft.replaceWith(replacement);await Promise.resolve();
 assert.equal(link.getAttribute('aria-disabled'),'false');assert.equal(notice.hidden,true);assert.equal(link.getAttribute('aria-describedby'),'draft-pending');
 // Avoid jsdom navigation while proving that the release guard allows the saved readback.
 let allowed=false;win.document.addEventListener('click',event=>{allowed=!event.defaultPrevented;event.preventDefault();});activate();assert.equal(allowed,true);
 win.close();
});

test('unsaved inquiry quantities block sending, and reverting them restores sending',()=>{
 const {win,form,draft,send}=inquiryDraft();
 const quantity=draft.querySelector('.qty');
 assert.equal(send.disabled,false);
 quantity.value='0';quantity.dispatchEvent(new win.Event('input',{bubbles:true}));
 assert.equal(send.disabled,true,'the inquiry must not send the previous server quantity');
 assert.equal(submit(form).defaultPrevented,true);
 assert.equal(form.querySelector('[data-inquiry-draft-pending]').hidden,false);
 quantity.value='1';quantity.dispatchEvent(new win.Event('change',{bubbles:true}));
 assert.equal(send.disabled,false,'reverting is not a pending edit');
 assert.equal(form.querySelector('[data-inquiry-draft-pending]').hidden,true);
});

test('native draft failure stays blocked until retry replaces the quantity fragment',async()=>{
 const {win,form,draft,send}=inquiryDraft();
 const quantity=draft.querySelector('.qty');
 quantity.value='2';quantity.dispatchEvent(new win.Event('input',{bubbles:true}));
 draft.classList.add('processing');await Promise.resolve();
 assert.equal(send.disabled,true);
 draft.classList.remove('processing');await Promise.resolve();
 assert.equal(send.disabled,true,'a failed update must not make old lines sendable');
 const replacement=draft.cloneNode(true);replacement.querySelector('.qty').setAttribute('value','2');
 draft.replaceWith(replacement);await Promise.resolve();
 assert.equal(send.disabled,false,'Woo now returned the saved quantity');
 assert.equal(form.querySelector('[data-inquiry-draft-pending]').hidden,true);
});

test('editing the draft preserves fields once across nonce ticks, within the authentication context',()=>{
 const first=inquiryDraft();
 const values={name:'Local UX Check',email:'draft-ux@example.test',company:'Local fixture',message:'Quotes "A" & B.\nPath \\keep\\text.'};
 for(const [name,value] of Object.entries(values))first.field(name).value=value;
 first.field('consent').checked=true;
 first.win.document.addEventListener('click',event=>event.preventDefault());
 first.win.document.querySelector('[data-inquiry-edit]').click();
 const saved=Object.entries(first.win.sessionStorage);
 const returned=inquiryDraft({saved,nonce:'next-nonce-tick',closed:true,defaultName:'Account name',defaultEmail:'account@example.test'});
 for(const [name,value] of Object.entries(values))assert.equal(returned.field(name).value,value);
 assert.equal(returned.field('consent').checked,true);
 assert.equal(returned.field('linker_inquiry_retained').value,'1','the existing Genie handoff must not replace retained empty entries');
 assert.equal(returned.form.querySelector('details').open,true,'changed reply details must be visible');
 assert.equal(returned.form.querySelector('summary small').textContent,'Local UX Check · draft-ux@example.test');
 assert.equal(returned.win.sessionStorage.length,0,'the bridge is consumed on return');
 const different=inquiryDraft({saved,context:'different-auth-session'});
 assert.equal(different.field('message').value,'','another authenticated context must not inherit a message');
 assert.equal(different.win.sessionStorage.length,0);
 const serverRetained=inquiryDraft({saved,retained:true});
 assert.equal(serverRetained.field('message').value,'','server-retained error fields take precedence');
 returned.field('message').value='Keep this when changing language';
 returned.win.document.addEventListener('click',event=>event.preventDefault());
 returned.win.document.querySelector('a[lang]').click();
 const translated=inquiryDraft({saved:Object.entries(returned.win.sessionStorage)});
 assert.equal(translated.field('message').value,'Keep this when changing language');
});

test('unavailable tab storage keeps the inquiry open and explains the edit failure',()=>{
 const current=inquiryDraft({storageUnavailable:true});
 current.field('message').value='Do not lose this message';
 let prevented=false;
 current.win.document.addEventListener('click',event=>{prevented=event.defaultPrevented;event.preventDefault();});
 current.win.document.querySelector('[data-inquiry-edit]').click();
 assert.equal(prevented,true,'navigation must stop when filled entries cannot be kept');
 assert.equal(current.form.querySelector('[data-inquiry-retention-error]').hidden,false);
 assert.equal(current.field('message').value,'Do not lose this message');
});

// Public inquiries use the same in-flight submission protection as account forms.
test('a public inquiry cannot submit twice while navigation is in flight',()=>{
 const dom=new JSDOM(`<div class="linker-inquiry"><form class="linker-inquiry-form"><input name="name" value="Maria" required><button type="submit">Send inquiry</button></form></div>`,{runScripts:'outside-only'});
 dom.window.eval(script);
 const form=dom.window.document.querySelector('form');
 assert.equal(submit(form).defaultPrevented,false);
 assert.equal(submit(form).defaultPrevented,true);
 assert.equal(form.querySelector('button').getAttribute('aria-busy'),'true');
});

// ── The two-step register card (ticket #225) ──────────────────────────────
const registerMarkup=()=>`<div class="linker-auth"><form method="post" data-linker-register data-active-step="1">
 <div data-progress hidden role="progressbar" aria-valuemin="1" aria-valuemax="2" aria-valuenow="1" aria-label="Registration step"><span data-progress-segment="1"></span><span data-progress-segment="2"></span></div>
 <p data-stepnote="1" hidden>step one</p><p data-stepnote="2" hidden>step two</p>
 <div data-pane="1">
  <div class="form-row validate-required"><input name="billing_company" aria-required="true"></div>
  <div class="form-row validate-required">
   <input type="radio" name="linker_customer_role" value="installer" aria-required="true"><label class="radio">Installer</label>
   <input type="radio" name="linker_customer_role" value="epc" aria-required="true"><label class="radio">EPC contractor</label>
  </div>
  <div class="form-row validate-required"><select name="billing_country" aria-required="true"><option value="DE">Germany</option><option value="AT">Austria</option></select></div>
  <div class="form-row"><input name="linker_company_website"></div>
  <div class="form-row"><input name="billing_vat_id"></div>
  <p data-oneof-error hidden>one of them</p>
  <p data-client-error hidden>complete the fields</p>
  <button type="button" data-next hidden>Continue</button>
 </div>
 <div data-pane="2">
  <div class="form-row validate-required"><input name="billing_first_name" aria-required="true"></div>
  <input type="email" name="email" required>
  <button type="submit" name="register">Register</button>
  <button type="button" data-back hidden>Back</button>
 </div>
</form></div>`;

function registerForm(){
 const dom=new JSDOM(registerMarkup(),{runScripts:'outside-only'});
 dom.window.eval(script);
 const form=dom.window.document.querySelector('form');
 const field=(name)=>form.querySelector(`[name="${name}"]`);
 return {win:dom.window,form,field};
}

function completeCompany(form,{site='example.com',vat=''}={}){
 form.querySelector('[name="billing_company"]').value='Solarbau GmbH';
 form.querySelector('[name="linker_customer_role"][value="installer"]').checked=true;
 form.querySelector('[name="billing_country"]').value='DE';
 form.querySelector('[name="linker_company_website"]').value=site;
 form.querySelector('[name="billing_vat_id"]').value=vat;
}

test('the register card opens on the company step and disables the hidden sign-in step',()=>{
 const {form,field}=registerForm();
 assert.equal(form.classList.contains('is-split'),true);
 assert.equal(form.dataset.activeStep,'1');
 assert.equal(form.querySelector('[data-stepnote="1"]').hidden,false);
 assert.equal(form.querySelector('[data-stepnote="2"]').hidden,true);
 assert.equal(form.querySelector('[data-progress]').hidden,false);
 assert.equal(form.querySelector('[data-progress]').getAttribute('role'),'progressbar');
 assert.equal(form.querySelector('[data-progress]').getAttribute('aria-valuenow'),'1');
 assert.equal(form.querySelector('[data-next]').hidden,false);
 assert.equal(form.querySelector('[data-back]').hidden,true);
 assert.equal(field('billing_company').disabled,false);
 assert.equal(field('billing_first_name').disabled,true);
 assert.equal(field('email').disabled,true);
 assert.equal(form.querySelector('button[type="submit"]').disabled,true);
});

test('continue refuses an incomplete company step and names the missing verification value',()=>{
 const {form}=registerForm();
 form.querySelector('[data-next]').click();
 assert.equal(form.dataset.activeStep,'1');
 assert.equal(form.querySelector('[data-client-error]').hidden,false);
 assert.equal(form.querySelector('[data-oneof-error]').hidden,false);
 assert.equal(form.querySelector('[name="billing_company"]').getAttribute('aria-invalid'),'true');
 assert.equal(form.querySelector('[name="linker_customer_role"]').getAttribute('aria-invalid'),'true');
 // Germany is preselected, so the country is never empty on the card.
 assert.equal(form.querySelector('[name="billing_country"]').getAttribute('aria-invalid'),null);
});

test('a complete company step opens the sign-in step and enables its controls',()=>{
 const {win,form,field}=registerForm();
 completeCompany(form);
 form.querySelector('[data-next]').click();
 assert.equal(form.dataset.activeStep,'2');
 assert.equal(form.querySelector('[data-stepnote="2"]').hidden,false);
 assert.equal(form.querySelector('[data-stepnote="1"]').hidden,true);
 assert.equal(form.querySelector('[data-progress]').getAttribute('aria-valuenow'),'2');
 assert.equal(form.querySelector('[data-progress-segment="2"]').classList.contains('is-on'),true);
 assert.equal(form.querySelector('[data-next]').hidden,true);
 assert.equal(form.querySelector('[data-back]').hidden,false);
 assert.equal(field('billing_first_name').disabled,false);
 assert.equal(field('email').disabled,false);
 assert.equal(form.querySelector('button[type="submit"]').disabled,false);
 assert.equal(win.document.activeElement,field('billing_first_name'));
});

test('back returns to the company step and disables the sign-in controls again',()=>{
 const {form,field}=registerForm();
 completeCompany(form);
 form.querySelector('[data-next]').click();
 form.querySelector('[data-back]').click();
 assert.equal(form.dataset.activeStep,'1');
 assert.equal(field('email').disabled,true);
 assert.equal(form.querySelector('[data-back]').hidden,true);
});

test('submitting on the company step opens the sign-in step instead of posting',()=>{
 const {form}=registerForm();
 completeCompany(form);
 const event=submit(form);
 assert.equal(event.defaultPrevented,true);
 assert.equal(form.dataset.activeStep,'2');
 assert.equal(form.dataset.accountState,undefined);
});

test('a malformed website keeps the company step open; a VAT ID alone satisfies the pair',()=>{
 const bad=registerForm();
 completeCompany(bad.form,{site:'not a site'});
 bad.form.querySelector('[data-next]').click();
 assert.equal(bad.form.dataset.activeStep,'1');
 assert.equal(bad.field('linker_company_website').getAttribute('aria-invalid'),'true');

 const vatOnly=registerForm();
 completeCompany(vatOnly.form,{site:'',vat:'DE143454214'});
 vatOnly.form.querySelector('[data-next]').click();
 assert.equal(vatOnly.form.dataset.activeStep,'2');
});

for(const eventType of ['input','change']) for(const [name,value] of [['linker_company_website','example.test'],['billing_vat_id','DE123456789']]){
 test(`correcting ${name} by ${eventType} clears the empty alternative's stale error`,()=>{
  const {win,form,field}=registerForm();
  completeCompany(form,{site:'',vat:''});
  form.querySelector('[data-next]').click();
  assert.equal(field('linker_company_website').getAttribute('aria-invalid'),'true');
  assert.equal(field('billing_vat_id').getAttribute('aria-invalid'),'true');
  field(name).value=value;
  field(name).dispatchEvent(new win.Event(eventType,{bubbles:true}));
  for(const other of ['linker_company_website','billing_vat_id']) assert.equal(field(other).hasAttribute('aria-invalid'),false);
  form.querySelector('[data-next]').click();
  assert.equal(form.dataset.activeStep,'2');
  form.querySelector('[data-back]').click();
  for(const other of ['linker_company_website','billing_vat_id']) assert.equal(field(other).hasAttribute('aria-invalid'),false);
  assert.equal(field(name).value,value);
 });
}

test('revalidation clears proof errors even when corrected values have no input event',()=>{
 const {form,field}=registerForm();
 completeCompany(form,{site:'',vat:''});
 form.querySelector('[data-next]').click();
 completeCompany(form);
 form.querySelector('[data-next]').click();
 assert.equal(form.dataset.activeStep,'2');
 assert.equal(field('linker_company_website').hasAttribute('aria-invalid'),false);
 assert.equal(field('billing_vat_id').hasAttribute('aria-invalid'),false);
});

test('editing the website does not clear an untouched nonempty VAT error',()=>{
 const {win,field}=registerForm();
 field('billing_vat_id').value='existing invalid value';
 field('billing_vat_id').setAttribute('aria-invalid','true');
 field('linker_company_website').value='example.test';
 field('linker_company_website').dispatchEvent(new win.Event('input',{bubbles:true}));
 assert.equal(field('billing_vat_id').getAttribute('aria-invalid'),'true');
});

for(const short of [false,true]){
 test(`step changes retain native focus and ${short?'prioritize a short viewport':'show the step heading when it fits'}`,()=>{
  const dom=new JSDOM(registerMarkup().replace('<div class="linker-auth">','<div class="linker-auth"><h1 id="linker-auth-register-heading">Create account</h1>'),{runScripts:'outside-only'});
  const {window:win}=dom,form=win.document.querySelector('form'),heading=win.document.querySelector('h1');
  const calls=[];
  heading.scrollIntoView=(options)=>calls.push(options);
  heading.getBoundingClientRect=()=>({top:0,bottom:30});
  Object.defineProperty(win,'visualViewport',{value:{height:short?200:800},configurable:true});
  for(const name of ['billing_first_name','billing_company']) form.querySelector(`[name="${name}"]`).getBoundingClientRect=()=>({top:270,bottom:320});
  win.eval(script);
  assert.equal(calls.length,0,'initialization must not scroll');
  completeCompany(form);
  form.querySelector('[data-next]').click();
  assert.equal(win.document.activeElement,form.querySelector('[name="billing_first_name"]'));
  assert.equal(calls.length,short?0:1);
  form.querySelector('[data-back]').click();
  assert.equal(win.document.activeElement,form.querySelector('[name="billing_company"]'));
  assert.equal(calls.length,short?0:2);
  for(const options of calls) assert.equal(options.block,'start');
 });
}

test('a required row whose control lost aria-required is still checked',()=>{
 const dom=new JSDOM(`<div class="linker-auth"><form method="post" data-linker-register data-active-step="1">
  <div data-progress hidden><span data-progress-segment="1"></span><span data-progress-segment="2"></span></div>
  <div data-pane="1">
   <div class="form-row validate-required"><input name="billing_company"></div>
   <div class="form-row"><input name="linker_company_website"></div>
   <p data-oneof-error hidden>one of them</p>
   <p data-client-error hidden>complete the fields</p>
   <button type="button" data-next hidden>Continue</button>
  </div>
  <div data-pane="2"></div>
 </form></div>`,{runScripts:'outside-only'});
 dom.window.eval(script);
 const form=dom.window.document.querySelector('form');
 form.querySelector('[data-next]').click();
 assert.equal(form.dataset.activeStep,'1');
 assert.equal(form.querySelector('[name="billing_company"]').getAttribute('aria-invalid'),'true');
});

test('a pasted password triggers the strength meter before the field is left',()=>{
 const dom=new JSDOM(`<div class="linker-auth"><form method="post" data-linker-register data-active-step="1">
  <div data-pane="1"></div><div data-pane="2"><input type="password" id="reg_password" name="password"></div>
 </form></div>`,{runScripts:'outside-only'});
 dom.window.eval(script);
 const field=dom.window.document.getElementById('reg_password');
 let keyups=0;
 field.addEventListener('keyup',()=>{keyups+=1;});
 field.value='Muster-Solar-2026!';
 field.dispatchEvent(new dom.window.Event('input',{bubbles:true}));
 // WooCommerce's meter handler is a keyup listener; the synthetic event lets
 // it run while the visitor is still in the field, not on blur.
 assert.equal(keyups,1);
});


