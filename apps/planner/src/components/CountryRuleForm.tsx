import { useCallback, useEffect, useId, useRef, useState } from "react";
import { __, sprintf } from "../i18n.ts";
import { calendarDate } from "../domain/gridConnection.ts";
import {
	emptyCountryRuleInputs,
	type CountryRuleInputs,
	type RuleBasis,
} from "../domain/countryRules.ts";
import { ScenarioNumber } from "./energy/ScenarioNumber.tsx";

const countries: Record<RuleBasis, string> = {
	fr_generation_pmax: "FR",
	nl_storage_max_active: "NL",
	de_pv_installed: "DE",
	at_tor_typ_a_max_capacity: "AT",
};
// Source-reading dates: docs/research/2026-10-23-modern-workbench/COUNTRY-EVIDENCE.md.
const CHECKED_SOURCE_DATES: Record<RuleBasis, string> = {
	fr_generation_pmax: "2026-11-04",
	nl_storage_max_active: "2026-11-04",
	de_pv_installed: "2026-11-04",
	at_tor_typ_a_max_capacity: "2026-11-11",
};
function checkedSourceDate(basis: RuleBasis, locale: string): string {
	return new Intl.DateTimeFormat(locale, {
		dateStyle: "long",
		timeZone: "UTC",
	}).format(new Date(CHECKED_SOURCE_DATES[basis] + "T00:00:00Z"));
}

export function CountryRuleForm({
	value,
	country,
	locale,
	onChange,
	onValidity,
}: {
	value: CountryRuleInputs | undefined;
	country: string | null;
	locale: string;
	onChange: (value: CountryRuleInputs | undefined) => void;
	onValidity: (valid: boolean) => void;
}) {
	const id = useId();
	const [dateText, setDateText] = useState(value?.rule_date ?? "");
	const validity = useRef<Record<string, boolean>>({});
	const report = useCallback(
		(field: string, valid: boolean) => {
			validity.current[field] = valid;
			onValidity(Object.values(validity.current).every(Boolean));
		},
		[onValidity],
	);
	useEffect(
		() => () => {
			validity.current = {};
			onValidity(true);
		},
		[onValidity],
	);
	useEffect(() => {
		setDateText(value?.rule_date ?? "");
		report("date", true);
	}, [value?.rule_date, value?.basis, report]);
	function changeDate(raw: string) {
		setDateText(raw);
		const date = raw.trim() || null;
		const valid =
			date === null || (/^\d{4}-\d{2}-\d{2}$/.test(date) && calendarDate(date));
		report("date", valid);
		if (valid && value) onChange({ ...value, rule_date: date });
	}
	function number(
		field:
			| "power_kw"
			| "connection_voltage_kv"
			| "apparent_power_kva"
			| "net_active_power_kw"
			| "at_change_previous_power_kw",
		next: number | null,
	) {
		if (!value) return;
		if (next !== null && next <= 0) {
			report(field, false);
			return;
		}
		onChange({ ...value, [field]: next });
	}
	return (
		<section className="lp-section" aria-labelledby={id + "-title"}>
			<h3 id={id + "-title"}>{__("National rule inputs", "linker-tools")}</h3>
			<p>
				{__(
					"These inputs select a dated rule reading. They are project declarations; operator requirements, device evidence and grid permission still require separate verification.",
					"linker-tools",
				)}
			</p>
			<label className="lp-field">
				<span>{__("Rule scope and power basis", "linker-tools")}</span>
				<select
					value={value?.basis ?? ""}
					onChange={(event) => {
						const basis = event.currentTarget.value as RuleBasis | "";
						onChange(basis ? emptyCountryRuleInputs(basis) : undefined);
					}}
				>
					<option value="">
						{__("Do not assess a national rule", "linker-tools")}
					</option>
					<option value="fr_generation_pmax">
						{__("France: generation-unit Pmax", "linker-tools")}
					</option>
					<option value="nl_storage_max_active">
						{__("Netherlands: grid-feeding storage unit", "linker-tools")}
					</option>
					<option value="de_pv_installed">
						{__("Germany: EEG solar installed power", "linker-tools")}
					</option>
					<option value="at_tor_typ_a_max_capacity">
						{__("Austria: TOR Erzeuger Typ A maximum capacity", "linker-tools")}
					</option>
				</select>
			</label>
			{value && (
				<>
					{country !== countries[value.basis] && (
						<p role="status">
							{__(
								"The selected rule does not match this project's country. No rule result will be added until they match.",
								"linker-tools",
							)}
						</p>
					)}
					<p>
						{value.basis === "fr_generation_pmax"
							? __(
									"Enter Pmax for the generation unit under Regulation (EU) 2016/631, not a device rating or Article 3 installed power by assumption.",
									"linker-tools",
								)
							: value.basis === "nl_storage_max_active"
								? __(
										"Enter the storage unit's maximum deliverable active power. Confirm the unit boundary separately; do not automatically add units.",
										"linker-tools",
									)
								: value.basis === "de_pv_installed"
									? __(
											"Enter installed solar power calculated for EEG section 9, including its aggregation conditions. A single inverter rating is not that calculation.",
											"linker-tools",
										)
									: __(
											"Enter the maximum capacity Pmax of the whole installation at one connection point, as TOR Erzeuger Typ A section 4.1 defines it. Several generating units at one connection point count as one installation.",
											"linker-tools",
										)}
					</p>
					<p>
						{value.basis === "fr_generation_pmax"
							? sprintf(
									__(
										"Source version: 26 June 2020, checked %s.",
										"linker-tools",
									),
									checkedSourceDate(value.basis, locale),
								)
							: value.basis === "nl_storage_max_active"
								? sprintf(
										__(
											"Source version: 1 October 2026, checked %s.",
											"linker-tools",
										),
										checkedSourceDate(value.basis, locale),
									)
								: value.basis === "de_pv_installed"
									? sprintf(
											__(
												"German source text checked %s; earlier transition rules are not established here.",
												"linker-tools",
											),
											checkedSourceDate(value.basis, locale),
										)
									: sprintf(
											__(
												"TOR Erzeuger Typ A, version 1.4 in force from 1 June 2026, checked %s.",
												"linker-tools",
											),
											checkedSourceDate(value.basis, locale),
										)}
					</p>
					<p>
						{__(
							"The rule date selects a documented source reading. It does not change the project connection date or establish whether the rule applies today.",
							"linker-tools",
						)}
					</p>
					<button
						type="button"
						className="lp-button"
						onClick={() => changeDate(CHECKED_SOURCE_DATES[value.basis])}
					>
						{sprintf(
							__("Use the source checked on %s", "linker-tools"),
							checkedSourceDate(value.basis, locale),
						)}
					</button>
					<div className="grid gap-5 md:grid-cols-2">
						<label className="lp-field">
							<span>
								{__("Date for this rule reading (YYYY-MM-DD)", "linker-tools")}
							</span>
							<input
								type="text"
								value={dateText}
								maxLength={10}
								aria-invalid={validity.current.date === false || undefined}
								onChange={(event) => changeDate(event.currentTarget.value)}
							/>
						</label>
						<ScenarioNumber
							field="power_kw"
							label={__("Declared power", "linker-tools")}
							value={value.power_kw}
							unit="kW"
							locale={locale}
							min={0}
							report={report}
							onChange={(next) => number("power_kw", next)}
						/>
						{value.basis === "fr_generation_pmax" && (
							<ScenarioNumber
								field="connection_voltage_kv"
								label={__(
									"Voltage at the grid connection point",
									"linker-tools",
								)}
								value={value.connection_voltage_kv}
								unit="kV"
								locale={locale}
								min={0}
								report={report}
								onChange={(next) => number("connection_voltage_kv", next)}
							/>
						)}
						{value.basis === "at_tor_typ_a_max_capacity" && (
							<>
								<ScenarioNumber
									field="connection_voltage_kv"
									label={__(
										"Nominal voltage at the network connection point",
										"linker-tools",
									)}
									value={value.connection_voltage_kv}
									unit="kV"
									locale={locale}
									min={0}
									report={report}
									onChange={(next) => number("connection_voltage_kv", next)}
								/>
								<ScenarioNumber
									field="apparent_power_kva"
									label={__(
										"Apparent power at the connection point",
										"linker-tools",
									)}
									value={value.apparent_power_kva ?? null}
									unit="kVA"
									locale={locale}
									min={0}
									report={report}
									onChange={(next) => number("apparent_power_kva", next)}
								/>
								<ScenarioNumber
									field="net_active_power_kw"
									label={__(
										"Agreed net active power at the connection point",
										"linker-tools",
									)}
									value={value.net_active_power_kw ?? null}
									unit="kW"
									locale={locale}
									min={0}
									report={report}
									onChange={(next) => number("net_active_power_kw", next)}
								/>
								<label className="lp-field">
									<span>
										{__(
											"Is this a change to an existing installation?",
											"linker-tools",
										)}
									</span>
									<select
										value={
											value.at_existing_installation_change === null ||
											value.at_existing_installation_change === undefined
												? ""
												: String(value.at_existing_installation_change)
										}
										onChange={(event) =>
											onChange({
												...value,
												at_existing_installation_change:
													event.currentTarget.value === ""
														? null
														: event.currentTarget.value === "true",
											})
										}
									>
										<option value="">
											{__("Not specified", "linker-tools")}
										</option>
										<option value="false">
											{__("No, a new installation", "linker-tools")}
										</option>
										<option value="true">
											{__("Yes, an existing installation", "linker-tools")}
										</option>
									</select>
								</label>
								{value.at_existing_installation_change === true && (
									<ScenarioNumber
										field="at_change_previous_power_kw"
										label={__(
											"Maximum capacity before the change",
											"linker-tools",
										)}
										value={value.at_change_previous_power_kw ?? null}
										unit="kW"
										locale={locale}
										min={0}
										report={report}
										onChange={(next) =>
											number("at_change_previous_power_kw", next)
										}
									/>
								)}
								<label className="lp-field">
									<span>
										{__(
											"Which conformity evidence is available?",
											"linker-tools",
										)}
									</span>
									<select
										value={value.at_conformity_basis ?? ""}
										onChange={(event) =>
											onChange({
												...value,
												at_conformity_basis: (event.currentTarget.value ||
													null) as Exclude<
													CountryRuleInputs["at_conformity_basis"],
													undefined
												>,
											})
										}
									>
										<option value="">
											{__("Not specified", "linker-tools")}
										</option>
										<option value="austrian_inverter_list">
											{__(
												"Entry in the Austrian inverter list",
												"linker-tools",
											)}
										</option>
										<option value="accredited_r25_report">
											{__(
												"Accredited test report under OVE-Richtlinie R 25 with Austrian settings",
												"linker-tools",
											)}
										</option>
										<option value="vde_4105_with_r25_properties">
											{__(
												"VDE-AR-N 4105 report with the additional R 25 properties and Austrian parameters",
												"linker-tools",
											)}
										</option>
									</select>
									<small>
										{__(
											"The declared path is a project declaration. Whether a specific device and software version is covered still needs the registry and document read-back.",
											"linker-tools",
										)}
									</small>
								</label>
							</>
						)}
						{value.basis === "fr_generation_pmax" && (
							<label className="lp-field">
								<span>
									{__(
										"Will all PV generation be consumed on site without any public-grid injection?",
										"linker-tools",
									)}
								</span>
								<select
									value={
										value.fr_enedis_full_self_consumption === null
											? ""
											: String(value.fr_enedis_full_self_consumption)
									}
									onChange={(event) =>
										onChange({
											...value,
											fr_enedis_full_self_consumption:
												event.currentTarget.value === ""
													? null
													: event.currentTarget.value === "true",
										})
									}
								>
									<option value="">
										{__("Not specified", "linker-tools")}
									</option>
									<option value="true">{__("Yes", "linker-tools")}</option>
									<option value="false">{__("No", "linker-tools")}</option>
								</select>
								<small>
									{__(
										"The Enedis declaration route is shown only when Enedis is the project-declared operator. Its service area and the project conditions still need verification.",
										"linker-tools",
									)}
								</small>
							</label>
						)}
						{value.basis === "de_pv_installed" && (
							<>
								<label className="lp-field">
									<span>
										{__(
											"Is the smart meter or control equipment not yet installed, or is the first successful operator control test still pending?",
											"linker-tools",
										)}
									</span>
									<select
										value={
											value.de_before_control_test === null
												? ""
												: String(value.de_before_control_test)
										}
										onChange={(event) =>
											onChange({
												...value,
												de_before_control_test:
													event.currentTarget.value === ""
														? null
														: event.currentTarget.value === "true",
											})
										}
									>
										<option value="">
											{__("Not specified", "linker-tools")}
										</option>
										<option value="true">{__("Yes", "linker-tools")}</option>
										<option value="false">{__("No", "linker-tools")}</option>
									</select>
								</label>
								<label className="lp-field">
									<span>
										{__(
											"EEG remuneration for this installation",
											"linker-tools",
										)}
									</span>
									<select
										value={value.de_remuneration ?? ""}
										onChange={(event) =>
											onChange({
												...value,
												de_remuneration: (event.currentTarget.value ||
													null) as CountryRuleInputs["de_remuneration"],
											})
										}
									>
										<option value="">
											{__("Not specified", "linker-tools")}
										</option>
										<option value="feed_in_or_tenant">
											{__(
												"Feed-in tariff or tenant-electricity supplement",
												"linker-tools",
											)}
										</option>
										<option value="other">
											{__("Other or none", "linker-tools")}
										</option>
									</select>
								</label>
								<label className="lp-field">
									<span>
										{__(
											"Does the complete plug-in solar exception apply?",
											"linker-tools",
										)}
									</span>
									<select
										value={
											value.de_plug_in_exception === null
												? ""
												: String(value.de_plug_in_exception)
										}
										onChange={(event) =>
											onChange({
												...value,
												de_plug_in_exception:
													event.currentTarget.value === ""
														? null
														: event.currentTarget.value === "true",
											})
										}
									>
										<option value="">
											{__("Not specified", "linker-tools")}
										</option>
										<option value="true">{__("Yes", "linker-tools")}</option>
										<option value="false">{__("No", "linker-tools")}</option>
									</select>
									<small>
										{__(
											"All conditions include a plug-in solar device behind the consumer's withdrawal point, up to 2 kW installed power and up to 800 VA inverter power.",
											"linker-tools",
										)}
									</small>
								</label>
							</>
						)}
					</div>
					{Object.values(validity.current).some((valid) => !valid) && (
						<p role="alert">
							{__(
								"Enter a valid date and positive numbers, or leave them empty. Your entries remain available for correction.",
								"linker-tools",
							)}
						</p>
					)}
				</>
			)}
		</section>
	);
}
