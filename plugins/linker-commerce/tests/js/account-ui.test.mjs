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
