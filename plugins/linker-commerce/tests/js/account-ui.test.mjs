import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {test} from 'node:test';
const require=createRequire(import.meta.url);
const {JSDOM}=require('../../../linker-tools/node_modules/jsdom');
const script=readFileSync(new URL('../../assets/account-ui.js',import.meta.url),'utf8');

function account(){
 const dom=new JSDOM(`<div class="linker-auth"><form method="post" id="signin">
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

test('a form the browser reports invalid keeps its button untouched',()=>{
 const win=account();
 const button=win.document.querySelector('button[type="submit"]');
 const form=win.document.getElementById('signin');
 // jsdom reports an empty required field as invalid, the same as the browser.
 assert.equal(form.checkValidity(),false);
 const event=submit(form);
 assert.equal(event.defaultPrevented,false);
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


