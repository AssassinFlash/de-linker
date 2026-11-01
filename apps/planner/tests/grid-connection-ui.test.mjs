import assert from "node:assert/strict";
import test from "node:test";
import React, { act, useState } from "react";
import { setupDom, enter } from "./dom-fixture.mjs";
import { GridConnectionForm } from "../src/components/GridConnectionForm.tsx";
import { EquipmentResult } from "../src/components/equipment/EquipmentResult.tsx";
import {
	readGridConnection,
	replaceGridConnection,
} from "../src/domain/gridConnection.ts";
import { readCountryAssessment } from "../src/data/readCountryAssessment.ts";
import {
	beginDraft,
	editDraft,
	prepareSave,
	projectInputContract,
} from "../src/domain/draft.ts";
import native from "./fixtures/grid-connection-assessments.json" with { type: "json" };
import german from "../../../plugins/linker-tools/languages/linker-tools-de_DE_formal-cf89287c9001d7518d0d20e58c3eb721.json" with { type: "json" };

async function mount(t, element, de = false) {
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
const click = async (text) => {
	const button = [...document.querySelectorAll("button")].find(
		(b) => b.textContent === text,
	);
	assert.ok(button, text);
	await act(async () => button.click());
};
const field = (label) =>
	[...document.querySelectorAll("label")]
		.find((l) => l.querySelector("span")?.textContent === label)
		?.querySelector("input");

test("native grid declarations retain partial and historical inputs, reject malformed data and elevated permission", () => {
	for (const value of Object.values(native))
		assert.equal(readCountryAssessment(value.assessment), value.assessment);
	assert.equal(readGridConnection(undefined), undefined);
	assert.equal(
		readGridConnection({
			...native.complete_de.inputs.grid_connection,
			dso_source_url: "HTTPS://example.invalid/operator",
		}).dso_source_url,
		"HTTPS://example.invalid/operator",
	);
	assert.throws(() =>
		readGridConnection({
			...native.complete_de.inputs.grid_connection,
			dso_source_url: "https://@example.invalid/operator",
		}),
	);
	for (const value of [
		null,
		{},
		{ ...native.complete_de.inputs.grid_connection, extra: true },
		{
			...native.complete_de.inputs.grid_connection,
			dso_source_url: "https://user:password@example.invalid/x",
		},
		{
			...native.complete_de.inputs.grid_connection,
			dso_source_url: "javascript:alert(1)",
		},
		{
			...native.complete_de.inputs.grid_connection,
			tab: {
				...native.complete_de.inputs.grid_connection.tab,
				date: "2026-02-30",
			},
		},
	])
		assert.throws(() => readGridConnection(value));
	for (const mutate of [
		(v) => (v.connection_permission = "established"),
		(v) => (v.checks[4].status = "provided"),
		(v) => (v.checks[1].id = v.checks[0].id),
		(v) => (v.project_facts.tab.date = "2026-02-30"),
		(v) => {
			v.country_code = "AT";
		},
		(v) => (v.rule_sources[0].source_url = "javascript:alert(1)"),
	]) {
		const value = structuredClone(native.complete_de.assessment);
		mutate(value);
		assert.throws(() => readCountryAssessment(value));
	}
});

for (const de of [false, true]) {
	test(`${de ? "DE" : "EN"}: optional project inputs support partial save, correction and whole-group removal`, async (t) => {
		const original = {
			brief: { retained: "country-independent" },
			arbitrary_future: { keep: [1, "x"] },
		};
		let current,
			valid = true;
		function Harness() {
			const [inputs, setInputs] = useState(original);
			current = inputs;
			return React.createElement(GridConnectionForm, {
				value: readGridConnection(inputs.grid_connection),
				onValidity: (v) => {
					valid = v;
				},
				onChange: (value) =>
					setInputs((old) => replaceGridConnection(old, value)),
			});
		}
		await mount(t, React.createElement(Harness), de);
		assert.deepEqual(current, original);
		assert.equal(document.querySelectorAll("input").length, 0);
		await click(
			de
				? "Angaben zum Netzanschluss ergänzen"
				: "Add grid connection information",
		);
		assert.equal(current.grid_connection.voltage_level, null);
		await enter(
			field(
				de
					? "Zuständiger Verteilnetzbetreiber (VNB)"
					: "Responsible distribution system operator (DSO)",
			),
			"Synthetic DSO",
		);
		assert.equal(valid, true);
		const draft = prepareSave(
			editDraft(
				beginDraft({ id: "a".repeat(32), revision: 1, inputs: original }),
				current,
			),
			"12345678-1234-4234-8234-123456789abc",
			{ maxDepth: 32, maxBytes: 100000 },
		);
		assert.equal(
			JSON.parse(draft.pending.body).input_contract,
			projectInputContract,
		);
		assert.equal(
			draft.pending.inputs.grid_connection.dso_name,
			"Synthetic DSO",
		);
		assert.equal(draft.pending.inputs.grid_connection.dso_source_url, null);
		const source = field(
			de ? "Quellen-URL zum Netzbetreiber" : "DSO source URL",
		);
		await enter(source, "https://user:password@example.invalid/private");
		assert.equal(valid, false);
		assert.ok(document.querySelector('[role="alert"]'));
		assert.equal(source.value, "https://user:password@example.invalid/private");
		assert.equal(current.grid_connection.dso_source_url, null);
		await enter(source, "https://example.invalid/dso");
		assert.equal(valid, true);
		assert.equal(
			current.grid_connection.dso_source_url,
			"https://example.invalid/dso",
		);
		const date = field(
			de ? "Dokumentdatum (JJJJ-MM-TT)" : "Document date (YYYY-MM-DD)",
		);
		await enter(date, "2026-02-30");
		assert.equal(valid, false);
		assert.equal(date.value, "2026-02-30");
		await enter(date, "2028-02-29");
		assert.equal(valid, true);
		assert.equal(current.grid_connection.tab.date, "2028-02-29");
		await enter(source, "https://user:password@example.invalid/private");
		assert.equal(valid, false);
		await click(
			de
				? "Angaben zum Netzanschluss entfernen"
				: "Remove grid connection information",
		);
		assert.deepEqual(current, original);
		assert.equal(valid, true);
	});
	test(`${de ? "DE" : "EN"}: single and multi-system results keep declaration, verification and permission separate`, async (t) => {
		const root = await mount(t, React.createElement("div"), de);
		for (const model of ["woo_equipment_v1", "woo_multi_converter_plant_v1"]) {
			const assessment = {
				model,
				checks: [],
				systems: [],
				selected_products: [],
				provisional_bill_of_materials: [],
				overall_status: "unresolved",
				country_assessment: native.complete_de.assessment,
			};
			await act(async () =>
				root.render(
					React.createElement(EquipmentResult, {
						run: { state: "succeeded", revision: 1 },
						locale: de ? "de-DE" : "en-GB",
						dirty: false,
						confirmedRevision: 1,
						assessmentOverride: assessment,
						embedded: true,
					}),
				),
			);
			const text = document.body.textContent;
			assert.ok(
				text.includes(
					de
						? "Angaben vorhanden; Prüfung ausstehend"
						: "Information provided; verification pending",
				),
			);
			assert.ok(
				text.includes(
					de
						? "Eine Anschlussgenehmigung ist nicht belegt."
						: "Grid connection permission has not been established.",
				),
			);
			assert.ok(text.includes(de ? "Mittelspannung" : "Medium voltage"));
			assert.equal(
				document.querySelector('a[href="https://example.invalid/requirements"]')
					.href,
				"https://example.invalid/requirements",
			);
			assert.ok(text.includes("EnWG §19"));
			await act(async () =>
				root.render(
					React.createElement(EquipmentResult, {
						run: { state: "succeeded", revision: 1 },
						locale: "en",
						dirty: false,
						confirmedRevision: 1,
						assessmentOverride: {
							...assessment,
							country_assessment: native.complete_at.assessment,
						},
						embedded: true,
					}),
				),
			);
			assert.equal(document.body.textContent.includes("EnWG §19"), false);
			assert.ok(
				document.body.textContent.includes(
					de
						? "Deutsche TAB werden für dieses Projekt nicht vorausgesetzt."
						: "German TAB requirements are not assumed for this project.",
				),
			);
			await act(async () =>
				root.render(
					React.createElement(EquipmentResult, {
						run: { state: "succeeded", revision: 1 },
						locale: "en",
						dirty: false,
						confirmedRevision: 1,
						assessmentOverride: {
							...assessment,
							country_assessment: native.partial_de.assessment,
						},
						embedded: true,
					}),
				),
			);
			assert.ok(
				document.body.textContent.includes(
					de ? "Noch fehlende Angaben" : "Information still missing",
				),
			);
			await act(async () =>
				root.render(
					React.createElement(EquipmentResult, {
						run: { state: "succeeded", revision: 1 },
						locale: de ? "de-DE" : "en-GB",
						dirty: false,
						confirmedRevision: 1,
						assessmentOverride: {
							...assessment,
							country_assessment: native.complete_unknown.assessment,
						},
						embedded: true,
					}),
				),
			);
			assert.ok(
				document.body.textContent.includes(
					de ? "Nicht angegeben" : "Not specified",
				),
			);
			assert.ok(document.body.textContent.includes(de ? "Land" : "Country"));
			assert.equal(document.body.textContent.includes("EnWG §19"), false);
		}
	});
}
