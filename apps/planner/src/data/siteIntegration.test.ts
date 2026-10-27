import assert from "node:assert/strict";
import test from "node:test";
import { projectLanguageUrl } from "./useSiteIntegration.ts";
import { initialEnergyView } from "./plannerLocation.ts";

test("native language destinations retain the current project without inventing a route", () => {
	const id = "a".repeat(32);
	assert.equal(
		projectLanguageUrl(
			"/de/native-paired-slug/?view=plan#roof",
			"https://site.example/en/",
			id,
		),
		`https://site.example/de/native-paired-slug/?view=plan&project=${id}`,
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
	const carried = new URL(
		projectLanguageUrl(
			"/de/",
			"https://site.example/?pv_kwp=10&annual_kwh=4500&step=roof&nonce=private",
			null,
		),
	);
	assert.equal(carried.searchParams.get("pv_kwp"), "10");
	assert.equal(carried.searchParams.get("annual_kwh"), "4500");
	assert.equal(carried.searchParams.get("step"), "roof");
	assert.equal(carried.searchParams.has("nonce"), false);
});

test("language switches keep only validated result/workspace references for the same project", () => {
	const project = "a".repeat(32),
		run = "b".repeat(32),
		target = "/de/native/";
	const current = `https://site.example/en/?project=${project}&run=${run}&nonce=private#lp-calculations`;
	const reportPage = `https://site.example/en/?project=${project}&energy_view=reports&nonce=private#lp-calculations`;
	const reportDestination = new URL(
		projectLanguageUrl(target, reportPage, project),
	);
	assert.equal(initialEnergyView(reportDestination), "reports");
	assert.equal(reportDestination.searchParams.has("nonce"), false);
	assert.equal(
		new URL(
			projectLanguageUrl(target, reportPage, "c".repeat(32)),
		).searchParams.has("energy_view"),
		false,
	);
	assert.equal(
		initialEnergyView(
			new URL(current.replace("&nonce=private", "&energy_view=reports")),
		),
		"runs",
	);
	assert.equal(
		initialEnergyView(new URL(reportPage.replace("=reports", "=unknown"))),
		"scenario",
	);
	assert.equal(
		new URL(
			projectLanguageUrl(
				target,
				`https://site.example/?project=${project}&step=roof`,
				project,
			),
		).hash,
		"#lp-design",
	);
	assert.equal(
		new URL(
			projectLanguageUrl(
				target,
				`https://site.example/?project=${project}&step=roof&step=roof`,
				project,
			),
		).hash,
		"",
	);
	assert.equal(
		new URL(
			projectLanguageUrl(
				target,
				current.replace("#lp-calculations", "#lp-equipment"),
				project,
			),
		).hash,
		"#lp-equipment",
	);
	assert.equal(
		projectLanguageUrl(target, current, project),
		`https://site.example/de/native/?project=${project}&run=${run}#lp-calculations`,
	);
	assert.equal(
		projectLanguageUrl(target, current, null),
		"https://site.example/de/native/",
	);
	assert.equal(
		projectLanguageUrl(target, current, "c".repeat(32)),
		`https://site.example/de/native/?project=${"c".repeat(32)}`,
	);
	assert.equal(
		projectLanguageUrl(
			`/de/?run=${run}#lp-calculations`,
			`https://site.example/en/?project=${project}&run=invalid#unknown`,
			project,
		),
		`https://site.example/de/?project=${project}`,
	);
	const pair = `${run},${"d".repeat(32)}`;
	assert.equal(
		projectLanguageUrl(
			target,
			`https://site.example/en/?project=${project}&run=${run}&compare=${pair}&nonce=private#lp-calculations`,
			project,
		),
		`https://site.example/de/native/?project=${project}&compare=${encodeURIComponent(pair)}#lp-calculations`,
	);
	assert.equal(
		projectLanguageUrl(
			`/de/?compare=old-secret`,
			`https://site.example/en/?project=${project}&compare=invalid&nonce=private#lp-calculations`,
			project,
		),
		`https://site.example/de/?project=${project}#lp-calculations`,
	);
});
