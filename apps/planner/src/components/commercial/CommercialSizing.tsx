import { useEffect, useRef, useState } from "react";
import type { Draft } from "../../domain/draft.ts";
import { readBrief } from "../../domain/brief.ts";
import {
	profileCsv,
	profileRefusal,
	profileRows,
	readSizing,
} from "../../domain/commercial.ts";
import type { ProfileRefusal } from "../../domain/commercial.ts";
import { readCommercialDesign } from "../../data/readCommercialDesign.ts";
import type { CommercialDesign } from "../../data/readCommercialDesign.ts";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import type { Session } from "../../data/protocol.ts";
import { ApiError } from "../../data/protocol.ts";
import { wire } from "../../data/readProtocol.ts";
import { NumberField } from "../NumberField.tsx";
import { Notice } from "../Notice.tsx";
import { __, sprintf } from "../../i18n.ts";

/**
 * Commercial storage sizing: the load profile the customer already has and the
 * peak they want to hold. The engine sizes only when both arrive
 * (`services/engine` `commercial.py` `design()`); without them it answers
 * indicative ranges by design, so this panel says which input is missing
 * instead of showing a range as if it were a design.
 */

function refusalText(code: ProfileRefusal): string {
	switch (code) {
		case "profile_empty":
			return __(
				"The file has no values. Put one 15-minute value on each line.",
				"linker-tools",
			);
		case "profile_too_short":
			return sprintf(
				__(
					"The file is shorter than one week. A load profile needs at least %s 15-minute values.",
					"linker-tools",
				),
				String(96 * 7),
			);
		case "profile_negative":
			return __(
				"The file contains negative values. A load profile holds consumption only.",
				"linker-tools",
			);
		case "profile_timestamps_need_offset":
			return __(
				"The file's timestamps do not say which time zone they are in. Export them with a UTC offset such as 2026-01-15T00:15:00+01:00; a local time repeats or is skipped at a daylight-saving change.",
				"linker-tools",
			);
		default:
			return __(
				"The file's timestamps are not evenly spaced 15-minute intervals. Check the export: a daylight-saving change must keep explicit offsets so every step stays one interval.",
				"linker-tools",
			);
	}
}
function designFailure(error: unknown): string {
	if (error instanceof ApiError) {
		if (error.code === "profile_too_short")
			return refusalText("profile_too_short");
		if (error.code === "profile_negative")
			return refusalText("profile_negative");
		if (error.code === "publication_changed" || error.code === "unavailable")
			return __(
				"The product data is being updated right now. Your entries are still here; please try again in a moment.",
				"linker-tools",
			);
	}
	return __(
		"The storage calculation could not be completed. Your entries are still here; please try again.",
		"linker-tools",
	);
}

function Goals({
	value,
	onChange,
	labels,
}: {
	value: readonly string[];
	onChange: (value: readonly string[]) => void;
	labels: Readonly<Record<string, string>>;
}) {
	return (
		<fieldset className="lp-brief-fields">
			<legend>{__("Goals", "linker-tools")}</legend>
			{Object.entries(labels).map(([goal, label]) => (
				<label className="lp-field" key={goal}>
					<span>
						<input
							type="checkbox"
							checked={value.includes(goal)}
							onChange={(event) =>
								onChange(
									event.currentTarget.checked
										? [...value, goal]
										: value.filter((item) => item !== goal),
								)
							}
						/>
						{label}
					</span>
				</label>
			))}
		</fieldset>
	);
}

export function CommercialSizing({
	draft,
	client,
	session,
	locale,
	active,
	disabled,
	onError,
}: {
	draft: Draft;
	client: PlannerClient;
	session: Session;
	locale: string;
	active: boolean;
	disabled: boolean;
	onError: (error: unknown) => void;
}) {
	const scope = session.query_scope;
	const brief = readBrief(draft.history.current.brief);
	// The postcode is the one field the brief already carries; it follows the
	// brief until the customer types their own, so a brief saved while this
	// panel is open still fills it.
	const briefPlz = /\b(\d{5})\b/.exec(brief.site.location_label)?.[1] ?? "";
	const [plz, setPlz] = useState(briefPlz);
	const typedPlz = useRef(false);
	useEffect(() => {
		if (typedPlz.current || !briefPlz) return;
		setPlz((current) => (current === briefPlz ? current : briefPlz));
	}, [briefPlz]);
	const [gridKva, setGridKva] = useState<number | null>(null);
	const [annualKwh, setAnnualKwh] = useState<number | null>(
		brief.annual_load.kwh,
	);
	const typedAnnual = useRef(false);
	useEffect(() => {
		if (typedAnnual.current) return;
		setAnnualKwh((current) =>
			current === brief.annual_load.kwh ? current : brief.annual_load.kwh,
		);
	}, [brief.annual_load.kwh]);
	const [peakKw, setPeakKw] = useState<number | null>(null);
	const [targetKw, setTargetKw] = useState<number | null>(null);
	const [pvKwp, setPvKwp] = useState<number | null>(null);
	const [backupLoad, setBackupLoad] = useState<number | null>(null);
	const [backupHours, setBackupHours] = useState<number | null>(null);
	const [goals, setGoals] = useState<readonly string[]>(["peak_shaving"]);
	const [unit, setUnit] = useState<"kW" | "kWh">("kW");
	const [profile, setProfile] = useState<{
		readonly name: string;
		readonly text: string;
	} | null>(null);
	const [fields, setFields] = useState<Record<string, boolean>>({});
	const [failure, setFailure] = useState<string | null>(null);
	const [result, setResult] = useState<CommercialDesign | null>(null);
	const [busy, setBusy] = useState(false);
	const lifetime = useRef(0);
	useEffect(() => {
		lifetime.current++;
		return () => {
			lifetime.current++;
		};
	}, []);

	const rows = profile ? profileRows(profile.text) : [];
	const profileIssue = profile ? profileRefusal(rows) : null;
	const accepted = profile !== null && profileIssue === null;
	const valid = Object.values(fields).every(Boolean);
	const wantsPeak = goals.includes("peak_shaving");
	// What the engine requires before it can size anything. The button stays
	// disabled rather than sending a request that would be refused, and the
	// panel names what is still missing.
	const missing: string[] = [];
	if (!/^\d{5}$/.test(plz))
		missing.push(__("the site postcode", "linker-tools"));
	if (!(gridKva !== null && gridKva > 0))
		missing.push(__("the grid connection capacity", "linker-tools"));
	if (!(annualKwh !== null && annualKwh > 0))
		missing.push(__("the annual consumption", "linker-tools"));
	if (!goals.length) missing.push(__("at least one goal", "linker-tools"));
	if (wantsPeak && !(targetKw !== null && targetKw > 0))
		missing.push(__("the target peak", "linker-tools"));
	const ready = missing.length === 0 && accepted && valid;

	async function size() {
		if (disabled || busy || !ready || !client.isCurrentScope(scope)) return;
		setFailure(null);
		const instance = lifetime.current;
		setBusy(true);
		try {
			const sizing = readSizing({
				plz,
				grid_connection_kva: gridKva,
				annual_kwh: annualKwh,
				goals,
				peak_kw: peakKw,
				target_peak_kw: wantsPeak ? targetKw : null,
				pv_kwp: pvKwp,
				backup_load_kw: backupLoad,
				backup_hours: backupHours,
				load_profile_unit: unit,
				load_profile_csv: profileCsv(rows),
				locale: locale.toLowerCase().startsWith("de") ? "de" : "en",
			});
			const answer = readCommercialDesign(
				await client.send(
					"design/commercial",
					wire(
						sizing,
						session.runtime.limits.max_json_depth,
						session.runtime.limits.max_body_bytes,
					),
					scope,
				),
			);
			if (instance !== lifetime.current) return;
			setResult(answer);
			onError(null);
		} catch (error) {
			if (instance !== lifetime.current) return;
			setResult(null);
			setFailure(designFailure(error));
		} finally {
			if (instance === lifetime.current) setBusy(false);
		}
	}

	if (!active) return null;

	return (
		<section className="lp-section" aria-labelledby="lp-commercial-title">
			<div className="lp-section-heading">
				<span className="lp-index">06</span>
				<div>
					<h3 id="lp-commercial-title">
						{__("Commercial storage sizing", "linker-tools")}
					</h3>
					<p>
						{__(
							"Sized from your own 15-minute load profile and the peak you want to hold. Without both, the calculation can only give indicative ranges.",
							"linker-tools",
						)}
					</p>
				</div>
			</div>
			<form
				onSubmit={(event) => {
					event.preventDefault();
					void size();
				}}
			>
				<fieldset className="lp-brief-fields">
					<legend>{__("Site and demand", "linker-tools")}</legend>
					<label className="lp-field">
						<span>{__("Postcode of the site", "linker-tools")}</span>
						<input
							inputMode="numeric"
							maxLength={5}
							value={plz}
							onChange={(event) => {
								typedPlz.current = true;
								setPlz(event.currentTarget.value.trim());
							}}
						/>
					</label>
					<NumberField
						label={__("Grid connection capacity", "linker-tools")}
						unit="kVA"
						value={gridKva}
						locale={locale}
						min={1}
						max={10000}
						onChange={setGridKva}
						onValidity={(ok) =>
							setFields((state) =>
								state.grid === ok ? state : { ...state, grid: ok },
							)
						}
					/>
					<NumberField
						label={__("Annual consumption", "linker-tools")}
						unit="kWh"
						value={annualKwh}
						locale={locale}
						min={1}
						max={100000000}
						onChange={(value) => {
							typedAnnual.current = true;
							setAnnualKwh(value);
						}}
						onValidity={(ok) =>
							setFields((state) =>
								state.annual === ok ? state : { ...state, annual: ok },
							)
						}
					/>
				</fieldset>
				<Goals
					value={goals}
					onChange={setGoals}
					labels={{
						peak_shaving: __("Peak shaving", "linker-tools"),
						self_consumption: __("Self-consumption of PV", "linker-tools"),
						backup: __("Backup supply", "linker-tools"),
					}}
				/>
				{wantsPeak ? (
					<fieldset className="lp-brief-fields">
						<legend>{__("Peak", "linker-tools")}</legend>
						<NumberField
							label={__("Peak from the bill", "linker-tools")}
							unit="kW"
							value={peakKw}
							locale={locale}
							min={1}
							max={10000}
							onChange={setPeakKw}
							onValidity={(ok) =>
								setFields((state) =>
									state.peak === ok ? state : { ...state, peak: ok },
								)
							}
						/>
						<NumberField
							label={__("Target peak", "linker-tools")}
							unit="kW"
							value={targetKw}
							locale={locale}
							min={1}
							max={10000}
							onChange={setTargetKw}
							onValidity={(ok) =>
								setFields((state) =>
									state.target === ok ? state : { ...state, target: ok },
								)
							}
						/>
						<p className="lp-profile-help">
							{__(
								"The target is the highest demand you want to keep importing. The storage covers everything above it.",
								"linker-tools",
							)}
						</p>
					</fieldset>
				) : null}
				{goals.includes("self_consumption") ? (
					<fieldset className="lp-brief-fields">
						<legend>{__("PV", "linker-tools")}</legend>
						<NumberField
							label={__("PV array, existing or planned", "linker-tools")}
							unit="kWp"
							value={pvKwp}
							locale={locale}
							min={0.1}
							max={10000}
							onChange={setPvKwp}
							onValidity={(ok) =>
								setFields((state) =>
									state.pv === ok ? state : { ...state, pv: ok },
								)
							}
						/>
					</fieldset>
				) : null}
				{goals.includes("backup") ? (
					<fieldset className="lp-brief-fields">
						<legend>{__("Backup", "linker-tools")}</legend>
						<NumberField
							label={__("Load to keep running", "linker-tools")}
							unit="kW"
							value={backupLoad}
							locale={locale}
							min={0.1}
							max={10000}
							onChange={setBackupLoad}
							onValidity={(ok) =>
								setFields((state) =>
									state.backup === ok ? state : { ...state, backup: ok },
								)
							}
						/>
						<NumberField
							label={__("For how long", "linker-tools")}
							unit="h"
							value={backupHours}
							locale={locale}
							min={0.1}
							max={72}
							onChange={setBackupHours}
							onValidity={(ok) =>
								setFields((state) =>
									state.hours === ok ? state : { ...state, hours: ok },
								)
							}
						/>
					</fieldset>
				) : null}
				<fieldset className="lp-brief-fields">
					<legend>{__("Load profile", "linker-tools")}</legend>
					<label className="lp-field">
						<span>{__("15-minute load profile (CSV)", "linker-tools")}</span>
						<span className="lp-file-picker">
							<span className="lp-file-button">
								{__("Choose file", "linker-tools")}
							</span>
							<span className="lp-file-name">
								{profile?.name ?? __("No file chosen", "linker-tools")}
							</span>
							<input
								type="file"
								accept=".csv,text/csv,text/plain"
								onChange={(event) => {
									const file = event.currentTarget.files?.[0];
									// Clearing the field lets the customer pick the same
									// file again after a failed read, which a retained
									// value would swallow as a "no change" event.
									event.currentTarget.value = "";
									setResult(null);
									setFailure(null);
									if (!file) {
										setProfile(null);
										return;
									}
									void file
										.text()
										.then((text) => setProfile({ name: file.name, text }))
										.catch(() => {
											setProfile(null);
											setFailure(
												__(
													"The file could not be read. Choose it again or export a fresh copy.",
													"linker-tools",
												),
											);
										});
								}}
							/>
						</span>
						<small>
							{__(
								"One value per line, optionally after a timestamp; the last number of each line counts.",
								"linker-tools",
							)}{" "}
							{__(
								"Timestamps must carry a UTC offset, so the series stays unambiguous when the clocks change.",
								"linker-tools",
							)}
						</small>
					</label>
					<label className="lp-field">
						<span>{__("Values in the file", "linker-tools")}</span>
						<select
							value={unit}
							onChange={(event) =>
								setUnit(event.currentTarget.value === "kWh" ? "kWh" : "kW")
							}
						>
							<option value="kW">
								{__("Average power in kW", "linker-tools")}
							</option>
							<option value="kWh">
								{__("Energy per 15 minutes in kWh", "linker-tools")}
							</option>
						</select>
					</label>
					{profile && profileIssue ? (
						<Notice error>
							<p>{refusalText(profileIssue)}</p>
						</Notice>
					) : null}
					{profile && !profileIssue ? (
						<p className="lp-profile-help" role="status">
							{sprintf(
								__("%s intervals read from the file.", "linker-tools"),
								new Intl.NumberFormat(locale).format(rows.length),
							)}
						</p>
					) : null}
				</fieldset>
				<div className="lp-inline-actions">
					{ready || !missing.length ? null : (
						<p className="lp-profile-help" role="status">
							{sprintf(
								__("Still needed: %s.", "linker-tools"),
								missing.join(", "),
							)}
						</p>
					)}
					<button
						type="submit"
						className="lp-button"
						disabled={disabled || busy || !ready}
						aria-busy={busy}
					>
						{busy
							? __("Calculating…", "linker-tools")
							: __("Size the storage", "linker-tools")}
					</button>
				</div>
			</form>
			{failure ? (
				<Notice error>
					<p>{failure}</p>
				</Notice>
			) : null}
			{result ? <CommercialOutcome result={result} locale={locale} /> : null}
		</section>
	);
}

function kW(value: number, locale: string): string {
	return sprintf(
		__("%s kW", "linker-tools"),
		new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(value),
	);
}

function kWh(value: number, locale: string): string {
	return sprintf(
		__("%s kWh", "linker-tools"),
		new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(value),
	);
}

function CommercialOutcome({
	result,
	locale,
}: {
	result: CommercialDesign;
	locale: string;
}) {
	const sized = result.status === "sized";
	return (
		<div className="lp-commercial-outcome">
			<h4>
				{sized
					? __("Sized storage", "linker-tools")
					: __("Indicative ranges", "linker-tools")}
			</h4>
			{result.load ? (
				<dl className="lp-profile-facts">
					<div>
						<dt>{__("Peak in the profile", "linker-tools")}</dt>
						<dd>{kW(result.load.peak_kw, locale)}</dd>
					</div>
					<div>
						<dt>{__("Annual consumption in the profile", "linker-tools")}</dt>
						<dd>{kWh(result.load.annual_kwh, locale)}</dd>
					</div>
					<div>
						<dt>{__("Intervals read", "linker-tools")}</dt>
						<dd>
							{new Intl.NumberFormat(locale).format(result.load.intervals)}
						</dd>
					</div>
					<div>
						<dt>{__("Days covered", "linker-tools")}</dt>
						<dd>
							{new Intl.NumberFormat(locale, {
								maximumFractionDigits: 1,
							}).format(result.load.days)}
						</dd>
					</div>
				</dl>
			) : null}
			{result.power_kw_range ? (
				<p>
					{__("Battery power:", "linker-tools")}{" "}
					<strong>
						{kW(result.power_kw_range.low, locale)}
						{result.power_kw_range.low === result.power_kw_range.high
							? ""
							: " – " + kW(result.power_kw_range.high, locale)}
					</strong>
				</p>
			) : null}
			{result.energy_kwh_range ? (
				<p>
					{__("Usable energy:", "linker-tools")}{" "}
					<strong>
						{kWh(result.energy_kwh_range.low, locale)}
						{result.energy_kwh_range.low === result.energy_kwh_range.high
							? ""
							: " – " + kWh(result.energy_kwh_range.high, locale)}
					</strong>
				</p>
			) : null}
			{sized && result.systems.length ? (
				<div className="lp-table-scroll">
					<table className="lp-data-table">
						<caption>
							{__(
								"Systems from the current range that reach this power and energy",
								"linker-tools",
							)}
						</caption>
						<thead>
							<tr>
								<th scope="col">{__("Inverter", "linker-tools")}</th>
								<th scope="col">{__("Units", "linker-tools")}</th>
								<th scope="col">{__("Battery", "linker-tools")}</th>
								<th scope="col">{__("Power", "linker-tools")}</th>
							</tr>
						</thead>
						<tbody>
							{result.systems.map((system) => (
								<tr key={String(system.inverter.id) + system.inverter_units}>
									<td>{String(system.inverter.model)}</td>
									<td>
										{new Intl.NumberFormat(locale).format(
											system.inverter_units,
										)}
									</td>
									<td>
										{system.battery
											? String(system.battery.model)
											: __("None", "linker-tools")}
									</td>
									<td>{kW(system.power_kw, locale)}</td>
								</tr>
							))}
						</tbody>
					</table>
				</div>
			) : null}
			{!sized ? (
				<Notice>
					<p>
						{__(
							"Add the load profile and the target peak to turn this into a sized system.",
							"linker-tools",
						)}
					</p>
				</Notice>
			) : null}
			{result.warnings.length ? (
				<ul className="lp-profile-help">
					{result.warnings.map((warning) => (
						<li key={warning}>{warning}</li>
					))}
				</ul>
			) : null}
			{result.basis.length ? (
				<ul className="lp-profile-help">
					{result.basis.map((line) => (
						<li key={line}>{line}</li>
					))}
				</ul>
			) : null}
		</div>
	);
}
