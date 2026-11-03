import test from "node:test";
import assert from "node:assert/strict";
import { readBrief } from "./brief.ts";
import { readEntryHints } from "./entryHints.ts";
import {
	installerEntryHref,
	projectBriefId,
	projectBriefInputs,
	readProjectBriefSource,
} from "./projectBrief.ts";

const BRIEF_ID = "0123456789abcdef0123456789abcdef";
const REVISION = "a".repeat(64);

test("the customer note is carried verbatim and no sizing value is inferred from it", () => {
	const note = "SAJ H2-10K, -40 °C, 6000 W. Two roofs, no backup.";
	const inputs = projectBriefInputs(note, null, "Carried from link");
	const brief = readBrief(inputs.brief);
	assert.equal(brief.project_note, note);
	// Numbers inside the customer's own sentence stay text, not sizing inputs.
	assert.equal(brief.annual_load.kwh, null);
	assert.equal(brief.site.location_label, "");
	assert.equal(inputs.equipment_setup, undefined);
});

test("a note survives even when no structured link hints exist", () => {
	const bare = projectBriefInputs("Only a note", null, "Carried from link");
	assert.equal(readBrief(bare.brief).project_note, "Only a note");
});

test("structured hints add inputs without rewriting the customer note", () => {
	const hints = readEntryHints(
		new URLSearchParams("annual_kwh=4500&phase=3&backup=needed_accessory_ok"),
	)!;
	const inputs = projectBriefInputs(
		"Roof faces west",
		hints,
		"Carried from link",
	);
	const brief = readBrief(inputs.brief);
	assert.equal(brief.project_note, "Roof faces west");
	assert.equal(brief.annual_load.kwh, 4500);
	// The backup hint is a structured operating mode, never a sentence in the note.
	assert.equal(
		(inputs.equipment_setup as Record<string, unknown>).operating_mode,
		"backup",
	);
});

test("only a same-origin path without query is accepted as the brief source", () => {
	assert.equal(
		projectBriefId(new URLSearchParams(`brief=${BRIEF_ID}`)),
		BRIEF_ID,
	);
	// A project or saved-solution reference outranks the brief selector such a URL
	// came from elsewhere, and an unreadable id is reported as unavailable.
	assert.equal(
		projectBriefId(new URLSearchParams(`brief=${BRIEF_ID}&project=abc`)),
		null,
	);
	assert.equal(projectBriefId(new URLSearchParams("brief=not-a-brief")), "");
	assert.equal(projectBriefId(new URLSearchParams("")), null);
});

test("staged briefs are validated before any customer text is rendered", () => {
	const record = {
		schema_version: 1,
		brief_id: BRIEF_ID,
		revision: REVISION,
		text: "Verbatim <svg/onload=alert(1)> & \\ newline\nend",
		source_path: "/for-installer/",
	};
	assert.equal(readProjectBriefSource(record, BRIEF_ID).text, record.text);
	assert.throws(() =>
		readProjectBriefSource({ ...record, brief_id: "b".repeat(32) }, BRIEF_ID),
	);
	assert.throws(() =>
		readProjectBriefSource({ ...record, text: "   " }, BRIEF_ID),
	);
	assert.throws(() =>
		readProjectBriefSource({ ...record, revision: "short" }, BRIEF_ID),
	);
	assert.throws(() =>
		readProjectBriefSource(
			{ ...record, source_path: "//evil.example" },
			BRIEF_ID,
		),
	);
});

test("returning to the entry keeps the page language and refuses foreign paths", () => {
	assert.equal(
		installerEntryHref("/for-installer/", "de"),
		"/de/fuer-installateur/",
	);
	assert.equal(
		installerEntryHref("/de/fuer-installateur/", "en"),
		"/for-installer/",
	);
	assert.equal(installerEntryHref("/for-installer/", "en"), "/for-installer/");
	assert.equal(
		installerEntryHref("https://evil.example/", "en"),
		"/for-installer/",
	);
	assert.equal(installerEntryHref(null, "de"), "/de/fuer-installateur/");
});
