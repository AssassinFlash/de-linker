import assert from "node:assert/strict";
import test from "node:test";
import React, { act, useCallback, useState } from "react";
import { setupDom, enter } from "./dom-fixture.mjs";
import { CountryRuleForm } from "../src/components/CountryRuleForm.tsx";
import { GridConnectionForm } from "../src/components/GridConnectionForm.tsx";
import { GridConnectionResult } from "../src/components/equipment/GridConnectionResult.tsx";
import { readCountryAssessment } from "../src/data/readCountryAssessment.ts";
import {
	readCountryRuleInputs,
	replaceCountryRuleInputs,
} from "../src/domain/countryRules.ts";
import {
	readGridConnection,
	replaceGridConnection,
} from "../src/domain/gridConnection.ts";
import { beginDraft, editDraft, undoDraft } from "../src/domain/draft.ts";
import native from "./fixtures/country-rule-assessments.json" with { type: "json" };
import german from "../../../plugins/linker-tools/languages/linker-tools-de_DE_formal-cf89287c9001d7518d0d20e58c3eb721.json" with { type: "json" };

async function mount(t, element, de) {
	const dom = setupDom();
	if (de)
		window.wp.i18n.__ = (message) =>
			german.locale_data.messages[message]?.[0] ?? message;
	const { createRoot } = await import("react-dom/client");
	const root = createRoot(dom.element);
	t.after(() => dom.dispose(root));
	await act(async () => root.render(element));
	return root;
}
function field(label, kind = "input") {
	return [...document.querySelectorAll("label")]
		.find((item) => item.querySelector("span")?.textContent?.trim() === label)
		?.querySelector(kind);
}
async function select(label, value) {
	const node = field(label, "select");
	assert.ok(node, label);
	await act(async () => {
		node.value = value;
		node.dispatchEvent(new window.Event("change", { bubbles: true }));
	});
}

test("native rule reviews preserve source, country and declared quantities", () => {
	for (const row of Object.values(native)) {
		assert.equal(readCountryAssessment(row.assessment), row.assessment);
		assert.deepEqual(
			readCountryRuleInputs(row.inputs.country_rule_inputs),
			row.inputs.country_rule_inputs,
		);
	}
	for (const change of [
		(v) => (v.rule_review.country_code = "NL"),
		(v) => (v.rule_review.checks[0].actual.power_kw = 99),
		(v) => (v.rule_review.checks[0].status = "approved"),
		(v) => (v.rule_review.sources[0].source_url = "javascript:alert(1)"),
		(v) =>
			(v.rule_review.checks[0].source_id = "fr_enedis_total_self_consumption"),
	]) {
		const result = structuredClone(native.fr.assessment);
		change(result);
		assert.throws(() => readCountryAssessment(result));
	}
});

for (const de of [false, true]) {
	test(`${de ? "DE" : "EN"}: selecting the checked source date preserves the project's own date`, async (t) => {
		const original = {
			...native.de.inputs,
			connection_date: "2027-05-14",
			country_rule_inputs: {
				...native.de.inputs.country_rule_inputs,
				rule_date: null,
			},
		};
		let current;
		function Harness() {
			const [inputs, setInputs] = useState(original);
			const onValidity = useCallback(() => {}, []);
			current = inputs;
			return React.createElement(CountryRuleForm, {
				value: readCountryRuleInputs(inputs.country_rule_inputs),
				country: "DE",
				locale: de ? "de-DE" : "en-GB",
				onValidity,
				onChange: (value) =>
					setInputs((old) => replaceCountryRuleInputs(old, value)),
			});
		}
		await mount(t, React.createElement(Harness), de);
		const label = de
			? "Am 1. November 2026 geprüften Quellenstand verwenden"
			: "Use the source checked on 1 November 2026";
		const button = [...document.querySelectorAll("button")].find(
			(item) => item.textContent === label,
		);
		assert.ok(button);
		await act(async () => button.click());
		assert.equal(current.country_rule_inputs.rule_date, "2026-11-01");
		assert.equal(current.connection_date, "2027-05-14");
	});
	test(`${de ? "DE" : "EN"}: removing the grid information names its dependent rule inputs and can be undone`, async (t) => {
		const original = native.enedis.inputs;
		let current;
		function Harness() {
			const [inputs, setInputs] = useState(original);
			current = inputs;
			return React.createElement(GridConnectionForm, {
				value: readGridConnection(inputs.grid_connection),
				hasRules: Boolean(inputs.country_rule_inputs),
				onValidity: () => {},
				onChange: (value) =>
					setInputs((old) => replaceGridConnection(old, value)),
			});
		}
		await mount(t, React.createElement(Harness), de);
		const label = de
			? "Netzanschlussangaben und Eingaben zu Landesregeln entfernen"
			: "Remove grid connection information and national rule inputs";
		const button = [...document.querySelectorAll("button")].find(
			(item) => item.textContent === label,
		);
		assert.ok(button);
		await act(async () => button.click());
		assert.equal(current.grid_connection, undefined);
		assert.equal(current.country_rule_inputs, undefined);
		const draft = beginDraft({
			id: "p",
			revision: 1,
			input_sha256: "a".repeat(64),
			title: "Test",
			inputs: original,
		});
		assert.deepEqual(
			undoDraft(editDraft(draft, current)).history.current,
			original,
		);
	});
	test(`${de ? "DE" : "EN"}: project rule input supports localized decimals and preserves invalid edits`, async (t) => {
		let current, valid;
		function Harness() {
			const [value, setValue] = useState(undefined);
			const onValidity = useCallback((state) => {
				valid = state;
			}, []);
			current = value;
			return React.createElement(CountryRuleForm, {
				value,
				country: "FR",
				locale: de ? "de-DE" : "en-GB",
				onChange: setValue,
				onValidity,
			});
		}
		await mount(t, React.createElement(Harness), de);
		await select(
			de ? "Regelungsbereich und Leistungsbezug" : "Rule scope and power basis",
			"fr_generation_pmax",
		);
		const date = field(
			de
				? "Datum dieser Regelbetrachtung (JJJJ-MM-TT)"
				: "Date for this rule reading (YYYY-MM-DD)",
		);
		assert.ok(date);
		await enter(date, "2026-02-30");
		assert.equal(valid, false);
		assert.equal(date.value, "2026-02-30");
		assert.equal(current.rule_date, null);
		await enter(date, "2026-11-01");
		const power = field(de ? "Angegebene Leistung kW" : "Declared power kW");
		assert.ok(power);
		await enter(power, de ? "10,5" : "10.5");
		assert.equal(current.power_kw, 10.5);
		assert.equal(current.rule_date, "2026-11-01");
		assert.equal(valid, true);
	});
	test(`${de ? "DE" : "EN"}: rule results display the correct frozen source and scoped outcome`, async (t) => {
		await mount(
			t,
			React.createElement(GridConnectionResult, {
				assessment: native.nl.assessment,
				locale: de ? "de-DE" : "en-GB",
			}),
			de,
		);
		assert.match(document.body.textContent, /0[,.]8 kW/);
		assert.match(document.body.textContent, /Type A|Typ A/);
		assert.match(
			document.body.textContent,
			de ? /Grenze von 0,8 kW/ : /0\.8 kW boundary/,
		);
		assert.ok(
			[...document.querySelectorAll("a")].some((link) =>
				link.href.includes("BWBR0052336/2026-10-01"),
			),
		);
		assert.doesNotMatch(
			document.body.textContent,
			de ? /Anschluss ist genehmigt/ : /connection is approved/,
		);
	});
	test(`${de ? "DE" : "EN"}: Enedis route keeps the conditional process and its source`, async (t) => {
		await mount(
			t,
			React.createElement(GridConnectionResult, {
				assessment: native.enedis.assessment,
				locale: de ? "de-DE" : "en-GB",
			}),
			de,
		);
		assert.match(document.body.textContent, /Enedis-Connect/);
		assert.match(document.body.textContent, /CACSI/);
		assert.match(document.body.textContent, /Consuel/);
		assert.ok(
			[...document.querySelectorAll("a")].some(
				(link) => link.hostname === "www.enedis.fr",
			),
		);
	});
}
