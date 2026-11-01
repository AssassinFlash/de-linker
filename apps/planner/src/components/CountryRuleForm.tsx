import { useCallback, useEffect, useId, useRef, useState } from "react";
import { __ } from "../i18n.ts";
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
};
// All three retained source readings were checked on this date; changing this
// choice never changes a project or connection date.
const CHECKED_SOURCE_DATE = "2026-11-01";

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
		field: "power_kw" | "connection_voltage_kv",
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
								: __(
										"Enter installed solar power calculated for EEG section 9, including its aggregation conditions. A single inverter rating is not that calculation.",
										"linker-tools",
									)}
					</p>
					<p>
						{value.basis === "fr_generation_pmax"
							? __(
									"Source version: 26 June 2020, checked 1 November 2026.",
									"linker-tools",
								)
							: value.basis === "nl_storage_max_active"
								? __(
										"Source version: 1 October 2026, checked 1 November 2026.",
										"linker-tools",
									)
								: __(
										"German source text checked 1 November 2026; earlier transition rules are not established here.",
										"linker-tools",
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
						onClick={() => changeDate(CHECKED_SOURCE_DATE)}
					>
						{__("Use the source checked on 1 November 2026", "linker-tools")}
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
