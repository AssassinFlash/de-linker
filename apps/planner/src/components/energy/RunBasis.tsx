import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { EnergyRun } from "../../data/energyProtocol.ts";
import { readBatteryAsset } from "../../data/energyProtocol.ts";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import type { Session, JsonObject } from "../../data/protocol.ts";
import { ApiError } from "../../data/protocol.ts";
import { readObject, readProject } from "../../data/readProtocol.ts";
import {
	readEnergyInputs,
	BATTERY_FIELDS,
} from "../../domain/energyScenario.ts";
import { readAsset } from "../../domain/profiles.ts";
import type { Measurement } from "../../domain/profiles.ts";
import { __ } from "../../i18n.ts";
import { measurementLabel } from "../ProfileLabels.ts";
import { Notice } from "../Notice.tsx";

export function RunBasis({
	run,
	session,
	client,
	recheck,
	locale,
}: {
	run: EnergyRun;
	session: Session;
	client: PlannerClient;
	recheck: () => void;
	locale: string;
}) {
	const [open, setOpen] = useState(false);
	const sources = useQuery({
		queryKey: [
			session.query_scope,
			"run-sources",
			run.project_id,
			run.id,
			run.manifest_sha256,
		],
		enabled:
			open && run.result !== null && client.isCurrentScope(session.query_scope),
		retry: false,
		queryFn: async ({ signal }) => {
			try {
				const historical = readProject(
					await client.query(
						"projects/read",
						{
							schema_version: 1,
							project_id: run.project_id,
							revision: run.revision,
						},
						session.query_scope,
						signal,
					),
				);
				if (
					historical.id !== run.project_id ||
					historical.revision !== run.revision ||
					historical.input_sha256 !== run.manifest.input_sha256
				)
					throw new ApiError(502, "run_source_mismatch");
				const selected = readEnergyInputs(historical.inputs.energy_replay),
					pins = readObject(readObject(run.manifest.context).assets);
				const profiles: [Measurement, string][] = [
					["gross_load", selected.gross_load_asset_id],
					["pv_available_ac", selected.pv_available_asset_id],
					["aux_ac", selected.aux_ac_asset_id],
				];
				if (selected.critical_load_asset_id)
					profiles.push(["critical_load", selected.critical_load_asset_id]);
				const entries = await Promise.all(
					profiles.map(async ([role, id]) => {
						const asset = readAsset(
							await client.query(
								"assets/read",
								{ schema_version: 1, project_id: run.project_id, asset_id: id },
								session.query_scope,
								signal,
							),
							run.project_id,
						);
						if (
							asset.id !== id ||
							asset.content_sha256 !== pins[role + ".raw"] ||
							asset.metadata_sha256 !== pins[role + ".metadata"]
						)
							throw new ApiError(502, "run_source_mismatch");
						const label = readObject(asset.metadata.provenance).label;
						if (typeof label !== "string" || !label.trim())
							throw new ApiError(502, "run_source_mismatch");
						return { role, asset, label };
					}),
				);
				const provenance = readObject(
					readObject(run.result?.battery_parameter_provenance).provenance,
				);
				if (typeof provenance.label !== "string")
					throw new ApiError(502, "run_source_mismatch");
				const battery = readBatteryAsset(
					await client.query(
						"assets/read",
						{
							schema_version: 1,
							project_id: run.project_id,
							asset_id: selected.battery_parameters_asset_id,
						},
						session.query_scope,
						signal,
					),
					run.project_id,
					provenance.label,
				);
				if (
					battery.id !== selected.battery_parameters_asset_id ||
					battery.content_sha256 !== pins["battery.raw"] ||
					battery.metadata_sha256 !== pins["battery.metadata"]
				)
					throw new ApiError(502, "run_source_mismatch");
				return { selected, entries, battery, note: provenance.label };
			} catch (error) {
				if (
					error instanceof ApiError &&
					([401, 403].includes(error.status) ||
						error.code === "session_changed")
				)
					recheck();
				throw error;
			}
		},
	});
	if (!run.result) return null;
	const model = readObject(run.result.model),
		periods = readObject(run.result.profile_interpretation)
			.operating_periods as readonly JsonObject[];
	const number = (value: unknown) =>
		typeof value === "number"
			? new Intl.NumberFormat(locale, { maximumFractionDigits: 9 }).format(
					value,
				)
			: "—";
	const parameterLabels = {
		usable_window_kwh: __("Usable stored energy", "linker-tools"),
		charge_ac_kw: __("AC charging power", "linker-tools"),
		discharge_ac_kw: __("AC discharging power", "linker-tools"),
		eta_charge: __("Charging efficiency", "linker-tools"),
		eta_discharge: __("Discharging efficiency", "linker-tools"),
		internal_aux_kw: __("Internal auxiliary power", "linker-tools"),
		standing_loss_rate_per_hour: __(
			"Standing-loss coefficient",
			"linker-tools",
		),
	};
	return (
		<details
			className="lp-comparison lp-run-basis"
			onToggle={(e) => setOpen(e.currentTarget.open)}
		>
			<summary>
				{__("Sources, period and storage model", "linker-tools")}
			</summary>
			{open && (
				<>
					{sources.isFetching && !sources.data && (
						<p role="status">
							{__("Reading the sources used for this result…", "linker-tools")}
						</p>
					)}
					{sources.error && (
						<Notice error>
							<p>
								{__(
									"The sources used for this result could not be read. The saved result still refers to its original sources.",
									"linker-tools",
								)}
							</p>
							<button
								type="button"
								className="lp-text-button"
								onClick={() => void sources.refetch()}
							>
								{__("Retry reading sources", "linker-tools")}
							</button>
						</Notice>
					)}
					{sources.data && (
						<>
							<p>{sources.data.note}</p>
							<ul className="lp-run-source-list">
								{sources.data.entries.map(({ role, asset, label }) => (
									<li key={role}>
										<strong>{measurementLabel(role)}</strong>
										<p>{label}</p>
										<dl className="lp-run-records">
											<div>
												<dt>
													{__("Original content SHA-256", "linker-tools")}
												</dt>
												<dd>
													<code>{asset.content_sha256}</code>
												</dd>
											</div>
											<div>
												<dt>{__("Source metadata SHA-256", "linker-tools")}</dt>
												<dd>
													<code>{asset.metadata_sha256}</code>
												</dd>
											</div>
										</dl>
									</li>
								))}
							</ul>
						</>
					)}
					<dl className="lp-field-summary">
						{BATTERY_FIELDS.map((field) => {
							const efficiency =
								field === "eta_charge" || field === "eta_discharge";
							return (
								<div key={field}>
									<dt>{parameterLabels[field]}</dt>
									<dd>
										{efficiency
											? number(Number(model[field]) * 100)
											: number(model[field])}{" "}
										{efficiency
											? "%"
											: field === "usable_window_kwh"
												? "kWh"
												: field === "standing_loss_rate_per_hour"
													? "1/h"
													: "kW"}
									</dd>
								</div>
							);
						})}
					</dl>
					<p>
						{__(
							"The model uses a fixed internal energy window and separate AC conversion efficiencies. Battery export, temperature effects, ageing and switching behaviour are outside this energy calculation.",
							"linker-tools",
						)}
					</p>
					<div className="lp-table-scroll" tabIndex={0}>
						<table>
							<caption>
								{__("Calculated operating periods (UTC)", "linker-tools")}
							</caption>
							<thead>
								<tr>
									<th>{__("Start", "linker-tools")}</th>
									<th>{__("End", "linker-tools")}</th>
									<th>{__("Grid condition", "linker-tools")}</th>
									<th>{__("Source resolution", "linker-tools")}</th>
								</tr>
							</thead>
							<tbody>
								{periods.map((period, index) => (
									<tr key={index}>
										<td>{String(period.start_utc)}</td>
										<td>{String(period.end_utc)}</td>
										<td>
											{period.mode === "outage"
												? __("Grid outage", "linker-tools")
												: __("Grid connected", "linker-tools")}
										</td>
										<td>
											{Object.entries(readObject(period.profiles)).map(
												([role, raw]) => {
													const p = readObject(raw),
														source = readObject(p.source);
													return (
														<p key={role}>
															{measurementLabel(role as Measurement)}:{" "}
															{number(source.native_max_interval_seconds)} s →{" "}
															{number(p.effective_max_interval_seconds)} s
															{p.reconstructed_means === true
																? " · " +
																	__(
																		"Reconstructed interval means",
																		"linker-tools",
																	)
																: ""}
														</p>
													);
												},
											)}
										</td>
									</tr>
								))}
							</tbody>
						</table>
					</div>
					<p>
						{__(
							"Time alignment preserves interval energy under a constant-mean assumption. A finer display or operating boundary does not create new measured peaks.",
							"linker-tools",
						)}
					</p>
				</>
			)}
		</details>
	);
}
