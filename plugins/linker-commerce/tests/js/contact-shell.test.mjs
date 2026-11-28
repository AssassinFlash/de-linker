import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { JSDOM } from 'jsdom';

const script = readFileSync(new URL('../../assets/contact-shell.js', import.meta.url), 'utf8');
const settled = () => new Promise(resolve => setImmediate(resolve));

function fixture(fetch) {
	const dom = new JSDOM(`<form data-linker-contact-shell="1" data-linker-contact-session-url="/session">
		<input name="linker_contact_nonce"><input name="linker_request_id">
		<input name="name" value="My draft"><p role="alert" data-contact-session-error hidden></p><button>Send</button>
	</form>`, { runScripts: 'outside-only' });
	const { window } = dom;
	window.fetch = fetch;
	window.eval(script);
	const form = window.document.querySelector('form');
	return { window, form };
}

test('focus and repeated submits await one session and replay the native submit once', async () => {
	let resolve;
	let calls = 0;
	const { window, form } = fixture((url, options) => {
		calls++;
		assert.equal(url, '/session');
		assert.equal(options.method, 'POST');
		assert.equal(options.cache, 'no-store');
		assert.equal(options.credentials, 'same-origin');
		return new Promise(ready => { resolve = ready; });
	});
	const button = form.querySelector('button');
	const submit = () => form.dispatchEvent(new window.SubmitEvent('submit', { cancelable: true, submitter: button }));
	let sends = 0;
	form.requestSubmit = submitter => {
		assert.equal(submitter, button);
		assert.equal(submit(), true);
		sends++;
	};
	assert.equal(calls, 0);
	form.dispatchEvent(new window.Event('focusin'));
	form.dispatchEvent(new window.Event('input'));
	assert.equal(submit(), false);
	assert.equal(submit(), false);
	assert.equal(calls, 1);
	resolve({ ok: true, json: async () => ({ nonce: 'native', requestId: 'unique' }) });
	await settled();
	assert.equal(sends, 1);
	assert.equal(form.elements.linker_contact_nonce.value, 'native');
	assert.equal(form.elements.linker_request_id.value, 'unique');
	assert.equal(form.dataset.linkerContactReady, '1');
	window.close();
});

test('bootstrap failure preserves the draft and lets the next interaction retry', async () => {
	let calls = 0;
	const { window, form } = fixture(async () => {
		if (++calls === 1) throw Error('offline');
		return { ok: true, json: async () => ({ nonce: 'native', requestId: 'unique' }) };
	});
	form.dispatchEvent(new window.Event('pointerdown'));
	await settled();
	const alert = form.querySelector('[role=alert]');
	assert.equal(alert.hidden, false);
	assert.equal(form.elements.name.value, 'My draft');
	assert.equal(form.dataset.linkerContactReady, undefined);
	form.dispatchEvent(new window.Event('focusin'));
	await settled();
	assert.equal(alert.hidden, true);
	assert.equal(form.dataset.linkerContactReady, '1');
	window.close();
});
