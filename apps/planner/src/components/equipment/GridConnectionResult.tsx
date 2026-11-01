import type { JsonObject } from "../../data/protocol.ts";
import { readGridConnection } from "../../domain/gridConnection.ts";
import { __ } from "../../i18n.ts";
export function GridConnectionResult({
	assessment,
}: {
	assessment: JsonObject | undefined;
}) {
	if (
		!assessment ||
		assessment.model !== "declared_grid_connection_evidence_v1"
	)
		return (
			<p>
				{__(
					"Country requirements: not assessed by this calculation.",
					"linker-tools",
				)}
			</p>
		);
	const facts = readGridConnection(assessment.project_facts)!;
	const labels: Record<string, string> = {
		country_code: __("Country", "linker-tools"),
		responsible_dso: __(
			"Responsible distribution system operator (DSO)",
			"linker-tools",
		),
		connection_voltage: __(
			"Voltage level at the grid connection point",
			"linker-tools",
		),
		applicable_tab: __(
			"Technical connection requirements (TAB or local equivalent)",
			"linker-tools",
		),
		independent_dso_tab_verification: __(
			"Independent verification of operator and requirements",
			"linker-tools",
		),
		connection_permission: __("Grid connection permission", "linker-tools"),
		dso_name: __("Operator name", "linker-tools"),
		dso_source_url: __("DSO source URL", "linker-tools"),
		voltage_level: __(
			"Voltage level at the grid connection point",
			"linker-tools",
		),
		"tab.source_url": __("Requirements source URL", "linker-tools"),
		"tab.edition_or_date": __("Requirements edition or date", "linker-tools"),
	};
	const voltage =
		facts.voltage_level === "low"
			? __("Low voltage", "linker-tools")
			: facts.voltage_level === "medium"
				? __("Medium voltage", "linker-tools")
				: facts.voltage_level === "high"
					? __("High voltage", "linker-tools")
					: "—";
	return (
		<section>
			<h4>{__("Grid connection information", "linker-tools")}</h4>
			<p>
				{__(
					"These are project-provided details. Operator territory, connection voltage and the applicable edition still need independent verification. Grid connection permission has not been established.",
					"linker-tools",
				)}
			</p>
			{assessment.country_code !== "DE" && (
				<p>
					{__(
						"Country-specific connection rules have not been assessed. German TAB requirements are not assumed for this project.",
						"linker-tools",
					)}
				</p>
			)}
			<dl className="lp-profile-facts">
				<div>
					<dt>{labels.country_code}</dt>
					<dd>
						{typeof assessment.country_code === "string"
							? assessment.country_code
							: __("Not specified", "linker-tools")}
					</dd>
				</div>
				<div>
					<dt>{labels.dso_name}</dt>
					<dd>{facts.dso_name ?? "—"}</dd>
				</div>
				<div>
					<dt>{labels.dso_source_url}</dt>
					<dd>
						{facts.dso_source_url ? (
							<a
								href={facts.dso_source_url}
								target="_blank"
								rel="noopener noreferrer"
							>
								{facts.dso_source_url}
							</a>
						) : (
							"—"
						)}
					</dd>
				</div>
				<div>
					<dt>{labels.connection_voltage}</dt>
					<dd>{voltage}</dd>
				</div>
				<div>
					<dt>{__("Document title", "linker-tools")}</dt>
					<dd>{facts.tab.title ?? "—"}</dd>
				</div>
				<div>
					<dt>{labels["tab.source_url"]}</dt>
					<dd>
						{facts.tab.source_url ? (
							<a
								href={facts.tab.source_url}
								target="_blank"
								rel="noopener noreferrer"
							>
								{facts.tab.source_url}
							</a>
						) : (
							"—"
						)}
					</dd>
				</div>
				<div>
					<dt>{__("Edition or version", "linker-tools")}</dt>
					<dd>{facts.tab.edition ?? "—"}</dd>
				</div>
				<div>
					<dt>{__("Document date (YYYY-MM-DD)", "linker-tools")}</dt>
					<dd>{facts.tab.date ?? "—"}</dd>
				</div>
			</dl>
			<ul>
				{(assessment.checks as JsonObject[]).map((check) => (
					<li key={String(check.id)}>
						{labels[String(check.id)]}:{" "}
						<strong>
							{check.status === "provided"
								? __(
										"Information provided; verification pending",
										"linker-tools",
									)
								: __("Evidence still required", "linker-tools")}
						</strong>
					</li>
				))}
			</ul>
			{(assessment.missing_inputs as string[]).length > 0 && (
				<>
					<h5>{__("Information still missing", "linker-tools")}</h5>
					<ul>
						{(assessment.missing_inputs as string[]).map((key) => (
							<li key={key}>{labels[key]}</li>
						))}
					</ul>
				</>
			)}
			{(assessment.rule_sources as JsonObject[]).length > 0 && (
				<>
					<h5>{__("Background rule sources", "linker-tools")}</h5>
					<p>
						{__(
							"These references are background evidence, not a verification of this project's requirements or current technical thresholds.",
							"linker-tools",
						)}
					</p>
					<ul>
						{(assessment.rule_sources as JsonObject[]).map((source) => (
							<li key={String(source.id)}>
								<a
									href={String(source.source_url)}
									target="_blank"
									rel="noopener noreferrer"
								>
									{String(source.title)}
								</a>
								{source.edition && <> · {String(source.edition)}</>}
								<p>
									{__("Evidence snapshot date", "linker-tools")}:{" "}
									{String(source.evidence_snapshot_date)}
								</p>
							</li>
						))}
					</ul>
				</>
			)}
		</section>
	);
}
