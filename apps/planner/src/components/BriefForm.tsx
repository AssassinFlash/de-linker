import { useCallback, useEffect, useId, useMemo, useState } from "react";
import type { Brief } from "../domain/brief.ts";
import type { Configuration } from "../data/config.ts";
import { __ } from "../i18n.ts";
import { NumberField } from "./NumberField.tsx";

export function BriefForm({
	brief,
	config,
	onChange,
	onValidity,
	workspace,
}: {
	brief: Brief;
	config: Configuration;
	onChange: (brief: Brief) => void;
	onValidity: (valid: boolean) => void;
	workspace?:
		"overview" | "site" | "energy" | "design" | "calculations" | "equipment";
}) {
	const id = useId();
	const [invalid, setInvalid] = useState<Readonly<Record<string, boolean>>>({});
	const validity = useCallback(
		(field: string, valid: boolean) => {
			setInvalid((previous) => {
				if (previous[field] === !valid) return previous;
				const next = { ...previous, [field]: !valid };
				return next;
			});
		},
		[onValidity],
	);
	useEffect(
		() => onValidity(!Object.values(invalid).some(Boolean)),
		[invalid, onValidity],
	);
	const annualValidity = useCallback(
		(value: boolean) => validity("annual", value),
		[validity],
	);
	const latitudeValidity = useCallback(
		(value: boolean) => validity("latitude", value),
		[validity],
	);
	const longitudeValidity = useCallback(
		(value: boolean) => validity("longitude", value),
		[validity],
	);
	const zones = useMemo(
		() => ["UTC", ...Intl.supportedValuesOf("timeZone")],
		[],
	);
	const countries = useMemo(
		() =>
			Object.entries(config.countries).sort((a, b) =>
				a[1].localeCompare(b[1], config.locale),
			),
		[config],
	);
	return (
		<div className="lp-brief">
			<section
				className="lp-section"
				id="lp-brief-use"
				hidden={workspace !== undefined && workspace !== "site"}
				tabIndex={-1}
				aria-labelledby="lp-brief-use-heading"
			>
				<div className="lp-section-heading">
					<span className="lp-index">01</span>
					<div>
						<h2 id="lp-brief-use-heading">
							{__("Project brief", "linker-tools")}
						</h2>
						<p>
							{__(
								"Available information can be saved now and completed as the design develops.",
								"linker-tools",
							)}
						</p>
					</div>
				</div>
				<div className="grid gap-5 md:grid-cols-2">
					<label className="lp-field">
						<span id={id + "-use"}>{__("Site use", "linker-tools")}</span>
						<select
							aria-labelledby={id + "-use"}
							value={brief.project_use ?? ""}
							onChange={(event) =>
								onChange({
									...brief,
									project_use:
										(event.currentTarget.value as Brief["project_use"]) || null,
								})
							}
						>
							<option value="">{__("Not specified", "linker-tools")}</option>
							<option value="residential">
								{__("Residential", "linker-tools")}
							</option>
							<option value="commercial">
								{__("Commercial", "linker-tools")}
							</option>
							<option value="industrial">
								{__("Industrial", "linker-tools")}
							</option>
						</select>
					</label>
					<label className="lp-field">
						<span id={id + "-system"}>
							{__("Planned system", "linker-tools")}
						</span>
						<select
							aria-labelledby={id + "-system"}
							value={brief.system_scope ?? ""}
							onChange={(event) =>
								onChange({
									...brief,
									system_scope:
										(event.currentTarget.value as Brief["system_scope"]) ||
										null,
								})
							}
						>
							<option value="">{__("Not specified", "linker-tools")}</option>
							<option value="new_pv_storage">
								{__("New PV and storage", "linker-tools")}
							</option>
							<option value="storage_addition">
								{__("Storage for existing PV", "linker-tools")}
							</option>
							<option value="pv_only">
								{__("PV without storage", "linker-tools")}
							</option>
						</select>
					</label>
				</div>
			</section>
			<section
				className="lp-section"
				id="lp-site"
				hidden={workspace !== undefined && workspace !== "site"}
				tabIndex={-1}
				aria-labelledby="lp-site-heading"
			>
				<div className="lp-section-heading">
					<span className="lp-index">02</span>
					<div>
						<h2 id="lp-site-heading">
							{__("Project location", "linker-tools")}
						</h2>
						<p>
							{__(
								"The project location and time zone are independent of the interface language.",
								"linker-tools",
							)}
						</p>
					</div>
				</div>
				<div className="grid gap-5 md:grid-cols-2">
					<label className="lp-field">
						<span id={id + "-country"}>{__("Country", "linker-tools")}</span>
						<select
							aria-labelledby={id + "-country"}
							value={brief.site.country_code ?? ""}
							onChange={(event) =>
								onChange({
									...brief,
									site: {
										...brief.site,
										country_code: event.currentTarget.value || null,
									},
								})
							}
						>
							<option value="">{__("Not specified", "linker-tools")}</option>
							{countries.map(([code, label]) => (
								<option key={code} value={code}>
									{label}
								</option>
							))}
						</select>
					</label>
					<label className="lp-field">
						<span>{__("Address or location reference", "linker-tools")}</span>
						<input
							value={brief.site.location_label}
							maxLength={4096}
							autoComplete="off"
							onChange={(event) =>
								onChange({
									...brief,
									site: {
										...brief.site,
										location_label: event.currentTarget.value,
									},
								})
							}
						/>
					</label>
					<NumberField
						locale={config.locale}
						label={__("Latitude", "linker-tools")}
						unit="°"
						value={brief.site.latitude}
						min={-90}
						max={90}
						onValidity={latitudeValidity}
						onChange={(latitude) =>
							onChange({
								...brief,
								site: {
									...brief.site,
									latitude,
									coordinate_basis:
										latitude === null && brief.site.longitude === null
											? "not_provided"
											: "user_entered",
								},
							})
						}
					/>
					<NumberField
						locale={config.locale}
						label={__("Longitude", "linker-tools")}
						unit="°"
						value={brief.site.longitude}
						min={-180}
						max={180}
						onValidity={longitudeValidity}
						onChange={(longitude) =>
							onChange({
								...brief,
								site: {
									...brief.site,
									longitude,
									coordinate_basis:
										longitude === null && brief.site.latitude === null
											? "not_provided"
											: "user_entered",
								},
							})
						}
					/>
					<label className="lp-field">
						<span id={id + "-zone"}>
							{__("Project time zone", "linker-tools")}
						</span>
						<select
							aria-labelledby={id + "-zone"}
							aria-describedby={id + "-zone-help"}
							value={brief.site.timezone ?? ""}
							onChange={(event) =>
								onChange({
									...brief,
									site: {
										...brief.site,
										timezone: event.currentTarget.value || null,
									},
								})
							}
						>
							<option value="">{__("Not specified", "linker-tools")}</option>
							{brief.site.timezone && !zones.includes(brief.site.timezone) && (
								<option>{brief.site.timezone}</option>
							)}
							{zones.map((zone) => (
								<option key={zone}>{zone}</option>
							))}
						</select>
						<small id={id + "-zone-help"}>
							{__(
								"Used to interpret timestamps in project data.",
								"linker-tools",
							)}
						</small>
					</label>
				</div>
			</section>
			<section
				className="lp-section"
				id="lp-load"
				hidden={workspace !== undefined && workspace !== "energy"}
				tabIndex={-1}
				aria-labelledby="lp-load-heading"
			>
				<div className="lp-section-heading">
					<span className="lp-index">03</span>
					<div>
						<h2 id="lp-load-heading">
							{__("Electricity consumption", "linker-tools")}
						</h2>
						<p>
							{__(
								"Annual consumption provides an initial overview. Interval data is needed to assess peaks and battery operation.",
								"linker-tools",
							)}
						</p>
					</div>
				</div>
				<div className="grid gap-5 md:grid-cols-2">
					<NumberField
						locale={config.locale}
						label={__("Annual consumption", "linker-tools")}
						unit="kWh"
						value={brief.annual_load.kwh}
						min={0}
						onValidity={annualValidity}
						onChange={(kwh) =>
							onChange({ ...brief, annual_load: { ...brief.annual_load, kwh } })
						}
					/>
					<label className="lp-field">
						<span id={id + "-basis"}>
							{__("Basis for the annual figure", "linker-tools")}
						</span>
						<select
							aria-labelledby={id + "-basis"}
							value={brief.annual_load.basis ?? ""}
							onChange={(event) =>
								onChange({
									...brief,
									annual_load: {
										...brief.annual_load,
										basis:
											(event.currentTarget
												.value as Brief["annual_load"]["basis"]) || null,
									},
								})
							}
						>
							<option value="">{__("Not specified", "linker-tools")}</option>
							<option value="bill_total">
								{__("Electricity bills", "linker-tools")}
							</option>
							<option value="user_estimate">
								{__("Project estimate", "linker-tools")}
							</option>
						</select>
					</label>
					<label className="lp-field md:col-span-2">
						<span id={id + "-source"}>
							{__("Source and period", "linker-tools")}
						</span>
						<input
							aria-labelledby={id + "-source"}
							aria-describedby={id + "-source-help"}
							value={brief.annual_load.source_note}
							maxLength={4096}
							onChange={(event) =>
								onChange({
									...brief,
									annual_load: {
										...brief.annual_load,
										source_note: event.currentTarget.value,
									},
								})
							}
						/>
						<small id={id + "-source-help"}>
							{__(
								"For example, the billing period or the basis of an estimate.",
								"linker-tools",
							)}
						</small>
					</label>
				</div>
			</section>
			<section
				className="lp-section"
				id="lp-notes"
				hidden={workspace !== undefined && workspace !== "site"}
				tabIndex={-1}
				aria-labelledby="lp-notes-heading"
			>
				<div className="lp-section-heading">
					<span className="lp-index">04</span>
					<div>
						<h2 id="lp-notes-heading">{__("Project notes", "linker-tools")}</h2>
					</div>
				</div>
				<label className="lp-field">
					<span>{__("Requirements and site constraints", "linker-tools")}</span>
					<textarea
						rows={4}
						maxLength={4096}
						value={brief.project_note}
						onChange={(event) =>
							onChange({ ...brief, project_note: event.currentTarget.value })
						}
					/>
				</label>
			</section>
		</div>
	);
}
