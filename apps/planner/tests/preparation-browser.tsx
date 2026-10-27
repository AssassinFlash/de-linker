/** Isolated visual consumer fixture. Not a production build entry or WP proof. */
import { __ } from "../src/i18n.ts";
import { useState } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PreparationResult } from "../src/components/energy/PreparationResult.tsx";
import { EnergyWorkspace } from "../src/components/energy/EnergyWorkspace.tsx";
import {
	beginDraft,
	editDraft,
	isDirty,
	prepareSave,
	acknowledgeSave,
} from "../src/domain/draft.ts";
import { ToolIdentity } from "../src/components/ToolIdentity.tsx";
import { readRun } from "../src/data/planningProtocol.ts";
import type { JsonObject, Session } from "../src/data/protocol.ts";
import type { PlannerClient } from "../src/data/PlannerClient.ts";
import fixture from "./fixtures/preparation-flow.json";
import german from "../../../plugins/linker-tools/languages/linker-tools-de_DE_formal-cf89287c9001d7518d0d20e58c3eb721.json";
import "../../../plugins/linker-commerce/content/windpress/tokens.css";
import "../../../plugins/linker-commerce/content/windpress/planner.css";

const options = new URLSearchParams(window.location.search),
	de = options.get("lang") === "de",
	weather = options.get("task") === "weather",
	raw = structuredClone(weather ? fixture.weather_run : fixture.pv_run),
	project = weather ? fixture.weather_project : fixture.pv_project,
	scope = "a".repeat(64),
	status = structuredClone(fixture.weather_status);
const setupMode = options.get("view") === "setup";
const dictionary = german.locale_data.messages as Record<string, unknown>;
document.documentElement.lang = de ? "de" : "en";
window.wp = {
	i18n: {
		__(message) {
			const entry = dictionary[message];
			return de && Array.isArray(entry) && typeof entry[0] === "string"
				? entry[0]
				: message;
		},
		sprintf(format, ...values) {
			let index = 0;
			return format.replace(
				/%(?:(\d+)\$)?[sd]/g,
				(_match, position: string | undefined) =>
					String(
						values[position === undefined ? index++ : Number(position) - 1],
					),
			);
		},
	},
};
for (const weight of [400, 600] as const) {
	const font = new FontFace(
		"Plus Jakarta Sans",
		`url(${new URL(`../../../plugins/linker-commerce/assets/fonts/plus-jakarta-sans-${weight}.ttf`, import.meta.url).href})`,
		{ weight: String(weight) },
	);
	document.fonts.add(await font.load());
}
const unknown = weather && options.get("status") === "unknown";
const response: JsonObject = unknown
	? { ...raw, state: "failed", result: null, result_sha256: null }
	: raw;
const observed = unknown
	? {
			...status,
			task_state: "failed",
			acquisition_state: "fetching",
			observation: null,
			capture_sha256: null,
		}
	: status;
const run = readRun(response, project.id),
	session = {
		query_scope: scope,
		runtime: {
			limits: {
				max_json_depth: 32,
				max_body_bytes: 16777216,
				max_page_size: 100,
			},
		},
	} as Session;
let setupRun: JsonObject | null = null;
const client = {
	isCurrentScope: (value: string) => value === scope,
	async query(path: string, body: JsonObject) {
		if (setupMode && path === "projects/runs")
			return {
				items: setupRun
					? [
							{
								id: setupRun.id,
								project_id: project.id,
								revision: setupRun.revision,
								manifest_sha256: setupRun.manifest_sha256,
								result_sha256: null,
								state: "queued",
								is_current: true,
								created_at: 1700000000,
								task_kind: weather
									? "acquire_pvgis_tmy_weather_v1"
									: "prepare_roof_pv_reference_v1",
							},
						]
					: [],
				next: null,
			};
		if (setupMode && path === "runs/read") return setupRun;
		if (path === "projects/read") return project;
		if (path === "assets/read")
			return body.asset_id === fixture.weather_run.result.prepared_asset.id
				? fixture.weather_run.result.prepared_asset
				: raw.result.prepared_asset;
		if (path === "runs/weather/status")
			return setupMode
				? {
						...observed,
						task_state: "queued",
						acquisition_state: "not_started",
						observation: null,
						capture_sha256: null,
					}
				: observed;
		throw new Error("unexpected_fixture_query");
	},
	send(path: string, serialized: string) {
		if (setupMode && path === (weather ? "runs/weather" : "runs/pv")) {
			const body = JSON.parse(serialized) as JsonObject;
			const template = weather ? fixture.weather_run : fixture.pv_run;
			setupRun = {
				...template,
				state: "queued",
				result: null,
				result_sha256: null,
				revision: body.expected_revision!,
				manifest: {
					...template.manifest,
					revision: body.expected_revision!,
				},
			};
			return Promise.resolve(setupRun);
		}
		throw new Error("fixture_has_no_mutation_transport");
	},
} as unknown as PlannerClient;
let inputs: JsonObject = structuredClone(project.inputs);
function SetupFixture() {
	const initial = {
		...project,
		inputs:
			options.get("blank") === "1"
				? { geometry: project.inputs.geometry }
				: project.inputs,
	};
	const [draft, setDraft] = useState(() => beginDraft(initial)),
		[valid, setValid] = useState(true);
	return (
		<>
			<main className="lp-editor-main">
				<button
					type="button"
					className="lp-button"
					disabled={!valid || !isDirty(draft)}
					onClick={() =>
						setDraft((current) => {
							const next = prepareSave(current, crypto.randomUUID(), {
									maxDepth: 32,
									maxBytes: 16777216,
								}),
								intent = next.pending!;
							return acknowledgeSave(next, intent, {
								...project,
								revision: intent.expectedRevision + 1,
								input_sha256: "e".repeat(64),
								inputs: intent.inputs,
							});
						})
					}
				>
					{__("Save project", "linker-tools")}
				</button>
				<EnergyWorkspace
					draft={draft}
					edit={(operation) => {
						try {
							const next = editDraft(draft, operation(draft.history.current));
							setDraft(next);
							return true;
						} catch {
							return false;
						}
					}}
					flush={async () => true}
					session={session}
					client={client}
					recheck={() => {
						throw new Error("fixture_identity_changed");
					}}
					locale={de ? "de-DE" : "en-GB"}
					blocked={false}
					active={true}
					onValidity={setValid}
					openProfiles={() => {}}
				/>
			</main>
			<ToolIdentity />
		</>
	);
}
function Fixture() {
	const [value, setValue] = useState(inputs);
	return (
		<>
			<main className="lp-editor-main">
				<PreparationResult
					run={run}
					inputs={value}
					edit={(operation) => {
						inputs = operation(inputs);
						setValue(inputs);
						return true;
					}}
					session={session}
					client={client}
					recheck={() => {
						throw new Error("fixture_identity_failure");
					}}
					locale={de ? "de-DE" : "en-GB"}
					blocked={false}
					active={true}
				/>
			</main>
			<ToolIdentity />
		</>
	);
}
const target = document.querySelector<HTMLElement>("[data-linker-planner]");
if (!target) throw new Error("missing_fixture_root");
const fixtureRoot = createRoot(target);
fixtureRoot.render(
	<QueryClientProvider
		client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
	>
		{setupMode ? <SetupFixture /> : <Fixture />}
	</QueryClientProvider>,
);
// The standalone development entry can be replaced before Vite reloads it.
// Release its former React root before a refreshed module mounts another one.
import.meta.hot?.dispose(() => fixtureRoot.unmount());
