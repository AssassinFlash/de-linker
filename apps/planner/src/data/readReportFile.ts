import type { PlannerClient } from "./PlannerClient.ts";
import type { PlanningRun } from "./planningProtocol.ts";
import { readObject } from "./readProtocol.ts";

export async function readReportFile(
	client: PlannerClient,
	run: PlanningRun,
	scope: string,
	locale: string,
	format: "pdf" | "materials" | "rules" | "series",
	signal: AbortSignal,
) {
	const attachments = run.result?.prepared_attachments;
	const keys = {
		materials: "bill_of_materials_csv",
		rules: "country_rule_review_csv",
		series: "pv_series_csv",
	} as const;
	const file = readObject(
		format === "pdf"
			? run.result?.prepared_asset
			: readObject(attachments)[keys[format]],
	);
	const id = String(file.id),
		digest = String(file.content_sha256);
	const blob =
		format === "pdf"
			? await client.reportPdf(run.project_id, id, scope, signal, digest)
			: await client.reportCsv(
					run.project_id,
					id,
					scope,
					digest,
					signal,
					format === "series",
				);
	const suffix =
		format === "rules"
			? "-country-rules"
			: format === "series"
				? "-pv-strings"
				: "";
	return {
		blob,
		filename: `linker-planning-${run.project_id}-r${run.revision}-${locale}${suffix}.${format === "pdf" ? "pdf" : "csv"}`,
	};
}
