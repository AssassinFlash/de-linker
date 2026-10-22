import assert from "node:assert/strict";
import test from "node:test";
import { projectLanguageUrl } from "./useSiteIntegration.ts";

test("native language destinations retain the current project without inventing a route", () => {
	const id = "a".repeat(32);
	assert.equal(
		projectLanguageUrl(
			"/de/native-paired-slug/?view=plan#roof",
			"https://site.example/en/",
			id,
		),
		`https://site.example/de/native-paired-slug/?view=plan&project=${id}#roof`,
	);
	assert.equal(
		projectLanguageUrl(`/de/?project=${id}`, "https://site.example/en/", null),
		"https://site.example/de/",
	);
	assert.equal(
		projectLanguageUrl(
			"https://other.example/de/",
			"https://site.example/",
			id,
		),
		"https://other.example/de/",
	);
	assert.throws(() =>
		projectLanguageUrl("/de/", "https://site.example/", "not-a-project"),
	);
});
