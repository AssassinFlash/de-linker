import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { JsonObject, Session } from "../../data/protocol.ts";
import { ApiError } from "../../data/protocol.ts";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import type { PlanningRun } from "../../data/planningProtocol.ts";
import { readObject, readProject } from "../../data/readProtocol.ts";
import { selectPreparation } from "../../domain/preparationSelection.ts";
import {
	readPvgisReference,
	referenceRoof,
} from "../../domain/pvgisReference.ts";
import { panelPoses } from "../../domain/panelPoses.ts";
import { readSelections } from "../../domain/profiles.ts";
import { __, sprintf } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";
import { runStateLabel, taskLabel } from "./planningLabels.ts";
import { PVGIS_REFERENCE_TASK } from "../../domain/pvgisReference.ts";
import { PvgisRoofFacts } from "./PvgisRoofFacts.tsx";

export function PvgisReferenceResult({
	run,
	inputs,
	edit,
	session,
	client,
	recheck,
	locale,
	blocked,
	active,
}: {
	run: PlanningRun;
	inputs: JsonObject;
	edit: (operation: (inputs: JsonObject) => JsonObject) => boolean;
	session: Session;
	client: PlannerClient;
	recheck: () => void;
	locale: string;
	blocked: boolean;
	active: boolean;
}) {
	const [error, setError] = useState<unknown>(null);
	const asset = run.result ? readObject(run.result.prepared_asset) : null;
	const source = useQuery({
		queryKey: [
			session.query_scope,
			"pvgis-reference-selection",
			run.project_id,
			run.id,
			run.result_sha256,
		],
		enabled: active && !!asset && client.isCurrentScope(session.query_scope),
		retry: false,
		queryFn: async ({ signal }) => {
			try {
				const [projectValue, assetValue] = await Promise.all([
					client.query(
						"projects/read",
						{
							schema_version: 1,
							project_id: run.project_id,
							revision: run.revision,
						},
						session.query_scope,
						signal,
					),
					client.query(
						"assets/read",
						{
							schema_version: 1,
							project_id: run.project_id,
							asset_id: asset!.id!,
						},
						session.query_scope,
						signal,
					),
				]);
				const project = readProject(projectValue),
					owned = readObject(assetValue),
					parameters = readPvgisReference(project.inputs.pvgis_reference),
					roof = referenceRoof(project.inputs);
				try {
					selectPreparation(project.inputs, run, project, owned);
				} catch (cause) {
					if (!(
						cause instanceof ApiError &&
						cause.code === "pvgis_reference_dc_conflict"
					))
						throw cause;
				}
				return { project, asset: owned, parameters, roof };
			} catch (cause) {
				if (
					cause instanceof ApiError &&
					([401, 403].includes(cause.status) ||
						cause.code === "session_changed")
				)
					recheck();
				throw cause;
			}
		},
	});
	const sourceData = client.isCurrentScope(session.query_scope)
		? source.data
		: undefined;
	let changed = false,
		dcConflict = false;
	if (sourceData)
		try {
			selectPreparation(inputs, run, sourceData.project, sourceData.asset);
		} catch (cause) {
			if (
				cause instanceof ApiError &&
				cause.code === "pvgis_reference_dc_conflict"
			)
				dcConflict = true;
			else changed = true;
		}
	const selected =
		!!asset &&
		readSelections(inputs.profile_selections).selected.pv_available_ac ===
			asset.id;
	const summary = run.result ? readObject(run.result.profile_summary) : null;
	const format = (value: unknown) =>
		typeof value === "number"
			? new Intl.NumberFormat(locale, { maximumFractionDigits: 3 }).format(
					value,
				)
			: "—";
	const parameters = sourceData?.parameters;
	const poses = sourceData
		? panelPoses(sourceData.roof.geometry).filter((p) => p.included)
		: [];
	return (
		<div className="lp-run-result">
			<div className="lp-run-heading">
				<h3 tabIndex={-1}>{taskLabel(PVGIS_REFERENCE_TASK)}</h3>
				<span role="status">
					{runStateLabel(run.state, PVGIS_REFERENCE_TASK)}
				</span>
			</div>
			<p>{sprintf(__("Revision %d", "linker-tools"), run.revision)}</p>
			{!run.is_current && (
				<Notice>
					{__(
						"This result belongs to an earlier saved revision. Its original inputs remain available.",
						"linker-tools",
					)}
				</Notice>
			)}
			{run.state === "failed" && (
				<Notice error>
					{__(
						"This source could not be prepared. Your project inputs remain unchanged.",
						"linker-tools",
					)}
				</Notice>
			)}
			{summary && (
				<>
					<dl className="lp-run-facts">
						<dt>{__("Modelled annual AC generation", "linker-tools")}</dt>
						<dd>{format(summary.energy_kwh)} kWh</dd>
						<dt>{__("Calculation period (UTC)", "linker-tools")}</dt>
						<dd>
							{String(summary.start_utc)} – {String(summary.end_utc)}
						</dd>
					</dl>
					<p>
						{__(
							"This PVGIS reference includes its selected system loss setting. Device-specific inverter behavior, nearby obstacles, shading between module rows, electrical design and grid acceptance remain outside this result.",
							"linker-tools",
						)}
					</p>
					<p>
						{__(
							"ERA5 uses hourly averages. In this reference, each SARAH3 sample is treated as representative of its containing UTC hour.",
							"linker-tools",
						)}
					</p>
					{source.isPending && (
						<p role="status">
							{__("Checking the saved source…", "linker-tools")}
						</p>
					)}
					{source.error && (
						<Notice error>
							<p>
								{__(
									"The saved source could not be checked. Existing project inputs remain unchanged.",
									"linker-tools",
								)}
							</p>
							<button
								type="button"
								className="lp-text-button"
								onClick={() => void source.refetch()}
							>
								{__("Try again", "linker-tools")}
							</button>
						</Notice>
					)}
					{parameters && (
						<dl className="lp-run-facts">
							<dt>{__("Calendar year", "linker-tools")}</dt>
							<dd>{parameters.year}</dd>
							<dt>{__("Radiation database", "linker-tools")}</dt>
							<dd>{parameters.radiation_database}</dd>
							<dt>{__("PV reference technology", "linker-tools")}</dt>
							<dd>{parameters.pv_technology}</dd>
							<dt>{__("PVGIS mounting type", "linker-tools")}</dt>
							<dd>
								{parameters.mounting_place === "free"
									? __("Free-standing (free)", "linker-tools")
									: __("Building-integrated (building)", "linker-tools")}
							</dd>
							<dt>{__("PVGIS system loss setting", "linker-tools")}</dt>
							<dd>{format(parameters.system_loss_percent)} %</dd>
							<dt>{__("Terrain horizon", "linker-tools")}</dt>
							<dd>
								{parameters.use_terrain_horizon
									? __("Included", "linker-tools")
									: __("Omitted", "linker-tools")}
							</dd>
							<dt>{__("Included modules", "linker-tools")}</dt>
							<dd>{format(poses.length)}</dd>
							<dt>{__("Module nameplate power", "linker-tools")}</dt>
							<dd>
								{format(
									poses.reduce((sum, p) => sum + p.stc_power_w, 0) / 1000,
								)}{" "}
								kWp
							</dd>
							{parameters.source_note && (
								<>
									<dt>
										{__("Private assumption note (optional)", "linker-tools")}
									</dt>
									<dd>{parameters.source_note}</dd>
								</>
							)}
						</dl>
					)}
					{changed && (
						<Notice>
							{__(
								"The source request, roof or model has changed. A source matching the current inputs is required.",
								"linker-tools",
							)}
						</Notice>
					)}
					{dcConflict && (
						<Notice>
							{__(
								"This whole-roof reference can be used only for an AC scenario for this roof. Change the topology or explicitly remove its DC PV input before selecting it. Your existing selections remain unchanged.",
								"linker-tools",
							)}
						</Notice>
					)}
					{sourceData && (
						<PvgisRoofFacts
							geometry={sourceData.roof.geometry}
							locale={locale}
						/>
					)}
					{Boolean(error) && (
						<Notice error>
							{__(
								"This project cannot be edited right now. The source has not been selected.",
								"linker-tools",
							)}
						</Notice>
					)}
					<p>
						{__(
							"Use this result only as an AC generation profile. It cannot supply the DC or detailed PV model role. Selecting it updates the open draft; Save project records the selection.",
							"linker-tools",
						)}
					</p>
					<button
						type="button"
						className="lp-button"
						disabled={
							blocked ||
							!active ||
							selected ||
							!sourceData ||
							changed ||
							dcConflict ||
							!client.isCurrentScope(session.query_scope)
						}
						onClick={() => {
							if (
								!sourceData ||
								blocked ||
								!active ||
								!client.isCurrentScope(session.query_scope)
							)
								return;
							try {
								if (
									!edit((current) =>
										selectPreparation(
											current,
											run,
											sourceData.project,
											sourceData.asset,
										),
									)
								)
									throw new ApiError(409, "project_edit_unavailable");
								setError(null);
							} catch (cause) {
								setError(cause);
							}
						}}
					>
						{selected
							? __("Selected in the current draft", "linker-tools")
							: __("Use as AC profile", "linker-tools")}
					</button>
					{sourceData && (
						<details className="lp-comparison">
							<summary>
								{__("Source and task checksums", "linker-tools")}
							</summary>
							<dl className="lp-run-facts">
								<dt>{__("Input SHA-256", "linker-tools")}</dt>
								<dd>{String(run.manifest.input_sha256)}</dd>
								<dt>{__("Result SHA-256", "linker-tools")}</dt>
								<dd>{run.result_sha256}</dd>
								<dt>{__("Source content SHA-256", "linker-tools")}</dt>
								<dd>{String(asset!.content_sha256)}</dd>
							</dl>
						</details>
					)}
				</>
			)}
		</div>
	);
}
