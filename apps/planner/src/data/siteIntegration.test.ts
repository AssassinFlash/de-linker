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

test("each configurator page stays open when the customer switches language", () => {
	const id = "a".repeat(32);
	for (const step of ["project", "solar", "energy", "system", "review"]) {
		const current = `https://site.example/en/?project=${id}#sc-${step}`;
		assert.equal(
			new URL(projectLanguageUrl("/de/", current, id)).hash,
			`#sc-${step}`,
		);
	}
});

test("a guided inquiry keeps the reviewed report when the site language changes", () => {
	const project = "a".repeat(32);
	const report = "b".repeat(32);
	const current = `https://site.example/en/?project=${project}&guided=inquiry&run=${report}#sc-review`;
	const same = new URL(projectLanguageUrl("/de/", current, project));
	assert.equal(same.searchParams.get("guided"), "inquiry");
	assert.equal(same.searchParams.get("run"), report);
	assert.equal(same.hash, "#sc-review");
	const other = new URL(projectLanguageUrl("/de/", current, "c".repeat(32)));
	assert.equal(other.searchParams.has("guided"), false);
	assert.equal(other.searchParams.has("run"), false);
});

test("native guided retry keeps only its own report, revision and handle on a language switch", () => {
	const project = "a".repeat(32);
	const report = "b".repeat(32);
	const retry = "4bb5413a-1ac7-4507-bf3c-04ca4c994404";
	const current = `https://site.example/en/?project=${project}&guided=inquiry&run=${report}&retry_revision=7&linker_inquiry_retry=${retry}#sc-review`;
	const same = new URL(projectLanguageUrl("/de/", current, project));
	assert.equal(same.searchParams.get("retry_revision"), "7");
	assert.equal(same.searchParams.get("linker_inquiry_retry"), retry);
	for (const [url, id] of [
		[current, "c".repeat(32)],
		[current.replace("#sc-review", "#sc-system"), project],
		[current.replace("retry_revision=7", "retry_revision=1e3"), project],
	]) {
		const destination = new URL(projectLanguageUrl("/de/", url!, id!));
		assert.equal(destination.searchParams.has("retry_revision"), false);
		assert.equal(destination.searchParams.has("linker_inquiry_retry"), false);
	}
});

test("language switches keep only validated result/workspace references for the same project", () => {
	const project = "a".repeat(32),
		run = "b".repeat(32),
		target = "/de/native/";
	const current = `https://site.example/en/?project=${project}&run=${run}&nonce=private#sc-review`;
	const reportPage = `https://site.example/en/?project=${project}&energy_view=reports&nonce=private#sc-review`;
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
		"#sc-solar",
	);
	assert.equal(
		new URL(
			projectLanguageUrl(
				target,
				`https://site.example/?project=${project}&step=equipment&product_id=1946&nonce=private`,
				project,
			),
		).href,
		`https://site.example/de/native/?project=${project}#sc-system`,
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
				`https://site.example/?project=${project}&step=equipment&step=equipment`,
				project,
			),
		).hash,
		"",
	);
	assert.equal(
		new URL(
			projectLanguageUrl(
				target,
				current.replace("#sc-review", "#sc-system"),
				project,
			),
		).hash,
		"#sc-system",
	);
	assert.equal(
		projectLanguageUrl(target, current, project),
		`https://site.example/de/native/?project=${project}&run=${run}#sc-review`,
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
			`/de/?run=${run}#sc-review`,
			`https://site.example/en/?project=${project}&run=invalid#unknown`,
			project,
		),
		`https://site.example/de/?project=${project}`,
	);
	const pair = `${run},${"d".repeat(32)}`;
	assert.equal(
		projectLanguageUrl(
			target,
			`https://site.example/en/?project=${project}&run=${run}&compare=${pair}&nonce=private#sc-review`,
			project,
		),
		`https://site.example/de/native/?project=${project}&compare=${encodeURIComponent(pair)}#sc-review`,
	);
	assert.equal(
		projectLanguageUrl(
			`/de/?compare=old-secret`,
			`https://site.example/en/?project=${project}&compare=invalid&nonce=private#sc-review`,
			project,
		),
		`https://site.example/de/?project=${project}#sc-review`,
	);
});

test("language switches keep a product proposal and do not treat roof as a saved result", () => {
	const carried = new URL(
		projectLanguageUrl(
			"/de/",
			"https://site.example/?step=equipment&product_id=1946&nonce=private",
			null,
		),
	);
	assert.equal(carried.searchParams.get("step"), "equipment");
	assert.equal(carried.searchParams.get("product_id"), "1946");
	assert.equal(carried.searchParams.has("nonce"), false);
	const project = "a".repeat(32);
	const owned = new URL(
		projectLanguageUrl(
			"/de/",
			`https://site.example/?project=${project}&step=equipment&product_id=1946&nonce=private`,
			project,
		),
	);
	assert.equal(owned.hash, "#sc-system");
	assert.equal(owned.searchParams.has("step"), false);
	assert.equal(owned.searchParams.has("product_id"), false);
	assert.equal(owned.searchParams.has("nonce"), false);
	const duplicate = new URL(
		projectLanguageUrl(
			"/de/",
			"https://site.example/?step=equipment&product_id=1946&product_id=1947&nonce=private&unrelated=keep-out",
			null,
		),
	);
	assert.deepEqual(duplicate.searchParams.getAll("product_id"), [
		"1946",
		"1947",
	]);
	assert.equal(duplicate.searchParams.get("step"), "equipment");
	assert.equal(duplicate.searchParams.has("nonce"), false);
	assert.equal(duplicate.searchParams.has("unrelated"), false);
	const malformed = new URL(
		projectLanguageUrl(
			"/de/?pv_kwp=99",
			"https://site.example/?pv_kwp=10&pv_kwp=-1&phase=9&plz=&backup=later&step=equipment&product_id=nope&nonce=private",
			null,
		),
	);
	assert.deepEqual(malformed.searchParams.getAll("pv_kwp"), ["10", "-1"]);
	assert.equal(malformed.searchParams.get("phase"), "9");
	assert.equal(malformed.searchParams.get("plz"), "");
	assert.equal(malformed.searchParams.get("backup"), "later");
	assert.equal(malformed.searchParams.get("step"), "equipment");
	assert.equal(malformed.searchParams.get("product_id"), "nope");
	assert.equal(malformed.searchParams.has("nonce"), false);
	const saved = new URL(
		projectLanguageUrl(
			"/de/",
			"https://site.example/?saved_solution=42&step=equipment&product_id=nope&nonce=private",
			null,
		),
	);
	assert.equal(saved.searchParams.get("saved_solution"), "42");
	assert.equal(saved.searchParams.has("step"), false);
	assert.equal(saved.searchParams.has("product_id"), false);
	assert.equal(saved.searchParams.has("nonce"), false);
});
