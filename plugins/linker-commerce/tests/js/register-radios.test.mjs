/**
 * The register card's business-type radios against the real auth.css (#351).
 *
 * The markup contract (input nested in its option label) is asserted by the
 * PHP suites; what only a stylesheet can break is the input's own hit area.
 * The defect was a rule that parked the input absolutely at 1px with
 * pointer-events:none, so only the wrapping label answered — this file loads
 * the volume's real stylesheet and fails if that rule comes back. The
 * selected and focused pill looks ride :has(), which jsdom's engine does not
 * cascade; the e2e suite (tests/e2e/specs/registration-two-step.spec.ts)
 * asserts those in a real browser.
 */

/**
 * External dependencies
 */
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {test} from 'node:test';

const require = createRequire(import.meta.url);
const {JSDOM} = require('../../../linker-tools/node_modules/jsdom');
const css = readFileSync(
	new URL('../../content/windpress/auth.css', import.meta.url),
	'utf8'
);

/** The business types of the card (CustomerRole::options). */
const OPTIONS = [
	['installer', 'Installer'],
	['epc', 'EPC contractor'],
	['distributor', 'Distributor'],
];

/** The row as RoleField renders it (the unit suite asserts the same shape). */
function registerCard() {
	const options = OPTIONS.map(
		([key, label]) =>
			`<label for="linker_customer_role_${key}" class="radio required_field"><input type="radio" class="input-radio" value="${key}" name="linker_customer_role" aria-required="true" id="linker_customer_role_${key}">${label}</label>`
	).join('');
	const dom = new JSDOM(
		`<div class="linker-auth"><form><p class="form-row form-row-wide validate-required" id="linker_customer_role_field"><label for="linker_customer_role_installer" class="required_field">Business type&nbsp;<span class="required" aria-hidden="true">*</span></label><span class="woocommerce-input-wrapper">${options}</span></p></form></div>`,
		{runScripts: 'outside-only'}
	);
	const style = dom.window.document.createElement('style');
	style.textContent = css;
	dom.window.document.head.appendChild(style);
	return dom.window;
}

test('the business-type input keeps its own hit area under the real auth.css', () => {
	const win = registerCard();
	const input = win.document.getElementById('linker_customer_role_epc');

	// pointer-events:none was the declaration that swallowed the input's
	// clicks: Playwright's actionability check refuses page.check() on it, and
	// a pointer on the pill only ever reached the label.
	assert.notEqual(
		win.getComputedStyle(input).pointerEvents,
		'none',
		'auth.css must not switch the radio input off pointer events'
	);
	assert.equal(
		input.disabled,
		false,
		'the input stays an enabled native control'
	);
	assert.equal(
		input.closest('label.radio') !== null,
		true,
		'the input sits inside its pill label, so its box is the pill'
	);
});

test('activating the input itself drives the radio group', () => {
	const win = registerCard();
	const epc = win.document.getElementById('linker_customer_role_epc');
	const installer = win.document.getElementById(
		'linker_customer_role_installer'
	);

	// A click on the input toggles its own checked state and, as a native
	// group under one name, unchecks the rest.
	epc.click();
	assert.equal(epc.checked, true, 'the input carries its own checked state');
	assert.equal(installer.checked, false);

	// The input is a focus target in the DOM order, not a bystander: focusing
	// it moves document.activeElement onto the radio a keyboard user lands on.
	epc.focus();
	assert.equal(
		win.document.activeElement,
		epc,
		'focus lands on the input itself'
	);
});
