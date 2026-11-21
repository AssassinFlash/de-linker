import type { JsonObject } from "../../data/protocol.ts";
import { readObject } from "../../data/readProtocol.ts";
import { readGridConnection } from "../../domain/gridConnection.ts";
import { __, sprintf } from "../../i18n.ts";
import { CountryRuleResult } from "./CountryRuleResult.tsx";

interface CountryEntry {
	readonly en: string;
	readonly de: string;
	readonly bundled: boolean;
	readonly framework?: string;
	readonly euRfg?: boolean;
}

const COUNTRY_CATALOG: Record<string, CountryEntry> = {
	AD: { en: "Andorra", de: "Andorra", bundled: false },
	AL: { en: "Albania", de: "Albanien", bundled: false },
	AT: {
		en: "Austria",
		de: "Österreich",
		bundled: true,
		framework: "TOR Stromerzeugungsanlagen Typ A v1.4; ElWG",
	},
	AX: { en: "Åland Islands", de: "Åland", bundled: false },
	BE: {
		en: "Belgium",
		de: "Belgien",
		bundled: false,
		framework: "Synergrid C10/11 & regional DSO rules",
	},
	BG: { en: "Bulgaria", de: "Bulgarien", bundled: false, euRfg: true },
	BY: { en: "Belarus", de: "Belarus", bundled: false },
	CH: {
		en: "Switzerland",
		de: "Schweiz",
		bundled: false,
		framework: "VSE NA/EEA-CH & ESTI / DSO rules",
	},
	CY: { en: "Cyprus", de: "Zypern", bundled: false, euRfg: true },
	CZ: {
		en: "Czechia",
		de: "Tschechien",
		bundled: false,
		framework: "PPDS Annex 4 (Příloha č. 4)",
	},
	DE: {
		en: "Germany",
		de: "Deutschland",
		bundled: true,
		framework: "EnWG §19; VDE-AR-N 4110:2023-09; EEG 2023 § 9",
	},
	DK: {
		en: "Denmark",
		de: "Dänemark",
		bundled: false,
		framework: "Green Power Denmark TR 3.2.1 / TR 3.3.1",
	},
	EE: { en: "Estonia", de: "Estland", bundled: false, euRfg: true },
	ES: {
		en: "Spain",
		de: "Spanien",
		bundled: false,
		framework: "RD 244/2019; RD 1183/2020; UNE 217002",
	},
	FI: {
		en: "Finland",
		de: "Finnland",
		bundled: false,
		framework: "Fingrid VJV & local DSO rules",
	},
	FO: { en: "Faroe Islands", de: "Färöer", bundled: false },
	FR: {
		en: "France",
		de: "Frankreich",
		bundled: true,
		framework: "Arrêté du 9 juin 2020 (Art. 35); Enedis CACSI",
	},
	GB: {
		en: "United Kingdom",
		de: "Vereinigtes Königreich",
		bundled: false,
		framework: "ENA ER G98 / G99 & DNO application",
	},
	GG: { en: "Guernsey", de: "Guernsey", bundled: false },
	GI: { en: "Gibraltar", de: "Gibraltar", bundled: false },
	GR: { en: "Greece", de: "Griechenland", bundled: false, euRfg: true },
	HR: { en: "Croatia", de: "Kroatien", bundled: false, euRfg: true },
	HU: { en: "Hungary", de: "Ungarn", bundled: false, euRfg: true },
	IE: {
		en: "Ireland",
		de: "Irland",
		bundled: false,
		framework: "ESB Networks NC6 / NC7 & Distribution Code",
	},
	IM: { en: "Isle of Man", de: "Isle of Man", bundled: false },
	IS: { en: "Iceland", de: "Island", bundled: false },
	IT: {
		en: "Italy",
		de: "Italien",
		bundled: false,
		framework: "CEI 0-21 / CEI 0-16 & DSO TICA",
	},
	JE: { en: "Jersey", de: "Jersey", bundled: false },
	LI: { en: "Liechtenstein", de: "Liechtenstein", bundled: false },
	LT: { en: "Lithuania", de: "Litauen", bundled: false, euRfg: true },
	LU: { en: "Luxembourg", de: "Luxemburg", bundled: false, euRfg: true },
	LV: { en: "Latvia", de: "Lettland", bundled: false, euRfg: true },
	MC: { en: "Monaco", de: "Monaco", bundled: false },
	MD: { en: "Moldova", de: "Republik Moldau", bundled: false },
	MK: { en: "North Macedonia", de: "Nordmazedonien", bundled: false },
	MT: { en: "Malta", de: "Malta", bundled: false, euRfg: true },
	NL: {
		en: "Netherlands",
		de: "Niederlande",
		bundled: true,
		framework: "Systeemcode elektriciteit 2026 (Art. 2.9)",
	},
	NO: {
		en: "Norway",
		de: "Norwegen",
		bundled: false,
		framework: "FoL / REN & local DSO rules",
	},
	PL: {
		en: "Poland",
		de: "Polen",
		bundled: false,
		framework: "EU 2016/631 (RfG) & PTPiREE IRiESD",
	},
	PT: {
		en: "Portugal",
		de: "Portugal",
		bundled: false,
		framework: "DGEG & E-Redes technical rules",
	},
	RO: { en: "Romania", de: "Rumänien", bundled: false, euRfg: true },
	RS: { en: "Serbia", de: "Serbien", bundled: false },
	RU: { en: "Russia", de: "Russland", bundled: false },
	SE: {
		en: "Sweden",
		de: "Schweden",
		bundled: true,
		framework: "EIFS 2018:2; EU 2016/631 (RfG); Ellagen (1997:857)",
	},
	SI: { en: "Slovenia", de: "Slowenien", bundled: false, euRfg: true },
	SJ: {
		en: "Svalbard and Jan Mayen",
		de: "Spitzbergen und Jan Mayen",
		bundled: false,
	},
	SK: { en: "Slovakia", de: "Slowakei", bundled: false, euRfg: true },
	SM: { en: "San Marino", de: "San Marino", bundled: false },
	UA: { en: "Ukraine", de: "Ukraine", bundled: false },
	VA: { en: "Vatican City", de: "Vatikanstadt", bundled: false },
};

function countryDisplayName(code: string, locale: string): string {
	const entry = COUNTRY_CATALOG[code];
	if (!entry) return code;
	return locale.toLowerCase().startsWith("de") ? entry.de : entry.en;
}

function countryFrameworkLabel(
	code: string,
	ruleGap: JsonObject | null,
): string {
	const entry = COUNTRY_CATALOG[code];
	if (entry?.framework) return entry.framework;
	if (entry?.euRfg)
		return __(
			"EU Regulation 2016/631 (RfG) national implementation and local DSO conditions",
			"linker-tools",
		);
	if (typeof ruleGap?.framework === "string" && ruleGap.framework && entry)
		return __(
			"National electricity network code and local grid operator conditions",
			"linker-tools",
		);
	return __(
		"National electricity network code and local grid operator conditions",
		"linker-tools",
	);
}

export function GridConnectionResult({
	assessment,
	locale,
}: {
	assessment: JsonObject | undefined;
	locale: string;
}) {
	const countryCode =
		typeof assessment?.country_code === "string" && assessment.country_code
			? assessment.country_code.toUpperCase()
			: null;
	const countryEntry = countryCode ? COUNTRY_CATALOG[countryCode] : undefined;
	const ruleGap = assessment?.rule_gap ? readObject(assessment.rule_gap) : null;
	if (
		!assessment ||
		assessment.model !== "declared_grid_connection_evidence_v1"
	) {
		if (!countryCode)
			return (
				<p>
					{__(
						"Country requirements: not assessed by this calculation.",
						"linker-tools",
					)}
				</p>
			);
		const name = countryDisplayName(countryCode, locale);
		const framework = countryFrameworkLabel(countryCode, ruleGap);
		return (
			<section>
				<h4>{__("Grid connection information", "linker-tools")}</h4>
				<p>
					{countryEntry?.bundled
						? sprintf(
								__(
									"A versioned national rule reading is bundled for %1$s (%2$s). Enter grid connection details and national rule inputs to run the conditional checks; local operator territory and connection permission still require project-specific verification.",
									"linker-tools",
								),
								name,
								framework,
							)
						: sprintf(
								__(
									"No automated grid-connection rule pack is bundled for %1$s (%2$s). Local grid operator connection rules are checked during project engineering and inquiry handling.",
									"linker-tools",
								),
								name,
								framework,
							)}
				</p>
				{countryCode !== "DE" && (
					<p>
						{__(
							"Country-specific connection rules have not been assessed. German TAB requirements are not assumed for this project.",
							"linker-tools",
						)}
					</p>
				)}
			</section>
		);
	}
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
	const countryLabel = countryCode
		? `${countryDisplayName(countryCode, locale)} (${countryCode})`
		: __("Not specified", "linker-tools");
	return (
		<section>
			<h4>{__("Grid connection information", "linker-tools")}</h4>
			{!assessment.rule_review && (
				<p>
					{__(
						"These are project-provided details. Operator territory, connection voltage and the applicable edition still need independent verification. Grid connection permission has not been established.",
						"linker-tools",
					)}
				</p>
			)}
			{countryCode !== "DE" && !assessment.rule_review && (
				<>
					<p>
						{__(
							"Country-specific connection rules have not been assessed. German TAB requirements are not assumed for this project.",
							"linker-tools",
						)}
					</p>
					<p>
						{countryCode === null
							? __(
									"No site country was specified, so national grid-connection rules could not be checked.",
									"linker-tools",
								)
							: countryEntry?.bundled
								? sprintf(
										__(
											"A versioned national rule reading is bundled for %1$s (%2$s). Enter national rule inputs to run the conditional checks.",
											"linker-tools",
										),
										countryDisplayName(countryCode, locale),
										countryFrameworkLabel(countryCode, ruleGap),
									)
								: sprintf(
										__(
											"No automated grid-connection rule pack is bundled for %1$s (%2$s). Local grid operator connection rules are checked during project engineering and inquiry handling.",
											"linker-tools",
										),
										countryDisplayName(countryCode, locale),
										countryFrameworkLabel(countryCode, ruleGap),
									)}
					</p>
				</>
			)}
			<dl className="sc-profile-facts">
				<div>
					<dt>{labels.country_code}</dt>
					<dd>{countryLabel}</dd>
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
			{assessment.rule_review && (
				<CountryRuleResult
					review={assessment.rule_review as JsonObject}
					locale={locale}
				/>
			)}
		</section>
	);
}
