/** Isolated visual consumer fixture. Not a production build entry or WP proof. */
import { useState } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PreparationResult } from "../src/components/energy/PreparationResult.tsx";
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
			return format.replace(/%[sd]/g, () => String(values[index++]));
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
const run = readRun(raw, project.id),
	session = { query_scope: scope } as Session;
const client = {
	isCurrentScope: (value: string) => value === scope,
	async query(path: string) {
		if (path === "projects/read") return project;
		if (path === "assets/read") return raw.result.prepared_asset;
		if (path === "runs/weather/status") return status;
		throw new Error("unexpected_fixture_query");
	},
	send() {
		throw new Error("fixture_has_no_mutation_transport");
	},
} as unknown as PlannerClient;
let inputs: JsonObject = structuredClone(project.inputs);
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
createRoot(target).render(
	<QueryClientProvider
		client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
	>
		<Fixture />
	</QueryClientProvider>,
);
