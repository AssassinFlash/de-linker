import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { JsonObject, Session } from "../../data/protocol.ts";
import { ApiError } from "../../data/protocol.ts";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import type { PlanningRun } from "../../data/planningProtocol.ts";
import { runTask } from "../../data/planningProtocol.ts";
import { WEATHER_TASK } from "../../data/readPreparationResult.ts";
import { readObject, readProject } from "../../data/readProtocol.ts";
import {
	selectPreparation,
	preparationPvRole,
} from "../../domain/preparationSelection.ts";
import { readPreparationWeather } from "../../data/preparationBasis.ts";
import { __, sprintf } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";
import { runStateLabel, taskLabel } from "./planningLabels.ts";
import { WeatherProgress } from "./WeatherProgress.tsx";
import { PreparationBasis } from "./PreparationBasis.tsx";

export function PreparationResult({
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
	const kind = runTask(run),
		weather = kind === WEATHER_TASK,
		asset = run.result ? readObject(run.result.prepared_asset) : null;
	const assetId = asset && typeof asset.id === "string" ? asset.id : null;
	const source = useQuery({
		queryKey: [
			session.query_scope,
			"preparation-selection",
			run.project_id,
			run.id,
			run.result_sha256,
		],
		enabled:
			active && assetId !== null && client.isCurrentScope(session.query_scope),
		retry: false,
		queryFn: async ({ signal }) => {
			try {
				if (!assetId) throw new ApiError(502, "invalid_preparation_result");
				const [rawProject, rawAsset] = await Promise.all([
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
							asset_id: assetId,
						},
						session.query_scope,
						signal,
					),
				]);
				const project = readProject(rawProject),
					asset = readObject(rawAsset);
				let weatherSource: unknown = asset;
				if (!weather) {
					const weatherId = readObject(
						project.inputs.pv_preparation,
					).weather_asset_id;
					if (
						typeof weatherId !== "string" ||
						!/^[a-f0-9]{32}$/.test(weatherId)
					)
						throw new ApiError(502, "preparation_source_mismatch");
					weatherSource = await client.query(
						"assets/read",
						{
							schema_version: 1,
							project_id: run.project_id,
							asset_id: weatherId,
						},
						session.query_scope,
						signal,
					);
					if (readObject(weatherSource).id !== weatherId)
						throw new ApiError(502, "preparation_source_mismatch");
				}
				return {
					project,
					asset,
					weather: readPreparationWeather(weatherSource, run),
				};
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
	let selectionError: unknown = null;
	if (source.data) {
		try {
			selectPreparation(inputs, run, source.data.project, source.data.asset);
		} catch (cause) {
			selectionError = cause;
		}
	}
	const selected =
		asset !== null &&
		(weather
			? readObject(inputs.pv_preparation ?? {}).weather_asset_id === asset.id
			: readObject(readObject(inputs.profile_selections ?? {}).selected ?? {})[
					preparationPvRole(inputs)
				] === asset.id);
	const summary = run.result
		? readObject(
				weather ? run.result.weather_summary : run.result.profile_summary,
			)
		: null;
	const format = (value: unknown) =>
		typeof value === "number"
			? new Intl.NumberFormat(locale, { maximumFractionDigits: 3 }).format(
					value,
				)
			: "—";
	const date = (value: unknown) =>
		typeof value === "string" && Number.isFinite(Date.parse(value))
			? `${new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short", timeZone: "UTC", hourCycle: "h23" }).format(new Date(value))} UTC`
			: "—";
	return (
		<div className="lp-run-result">
			<div className="lp-run-heading">
				<h3 tabIndex={-1}>{taskLabel(kind)}</h3>
				<span role="status">{runStateLabel(run.state, kind)}</span>
			</div>
			<p>{sprintf(__("Revision %d", "linker-tools"), run.revision)}</p>
			{weather && (
				<WeatherProgress
					runId={run.id}
					session={session}
					client={client}
					recheck={recheck}
					active={active}
				/>
			)}
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
					{weather ? (
						<dl className="lp-run-facts">
							<dt>{__("Latitude", "linker-tools")}</dt>
							<dd>{format(summary.latitude_deg)} °</dd>
							<dt>{__("Longitude", "linker-tools")}</dt>
							<dd>{format(summary.longitude_deg)} °</dd>
							<dt>{__("Altitude", "linker-tools")}</dt>
							<dd>{format(summary.altitude_m)} m</dd>
							<dt>{__("Hourly weather records", "linker-tools")}</dt>
							<dd>{format(summary.interval_count)}</dd>
						</dl>
					) : (
						<>
							<dl className="lp-run-facts">
								<dt>{__("Modelled PV generation", "linker-tools")}</dt>
								<dd>{format(summary.energy_kwh)} kWh</dd>
								<dt>{__("Start", "linker-tools")}</dt>
								<dd>{date(summary.start_utc)}</dd>
								<dt>{__("End", "linker-tools")}</dt>
								<dd>{date(summary.end_utc)}</dd>
							</dl>
							<p>
								{__(
									"This is an unshaded reference profile. Site shading, equipment compatibility and country requirements remain unassessed.",
									"linker-tools",
								)}
							</p>
						</>
					)}
					<p>
						{__(
							"Preparation leaves your project inputs unchanged. Selecting a source updates the current open draft. Save project saves that selection on the server.",
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
					{Boolean(selectionError) && (
						<Notice
							error={
								!(
									selectionError instanceof ApiError &&
									selectionError.code === "preparation_source_changed"
								)
							}
						>
							{selectionError instanceof ApiError &&
							selectionError.code === "preparation_source_changed"
								? __(
										"The source request, roof or model has changed. A source matching the current inputs is required.",
										"linker-tools",
									)
								: __(
										"The saved source could not be checked. Existing project inputs remain unchanged.",
										"linker-tools",
									)}
						</Notice>
					)}
					{Boolean(error) && (
						<Notice error>
							{error instanceof ApiError &&
							error.code === "preparation_source_changed"
								? __(
										"The source request, roof or model has changed. A source matching the current inputs is required.",
										"linker-tools",
									)
								: __(
										"This project cannot be edited right now. The source has not been selected.",
										"linker-tools",
									)}
						</Notice>
					)}
					<button
						type="button"
						className="lp-button"
						disabled={
							blocked ||
							!active ||
							selected ||
							!source.data ||
							Boolean(selectionError) ||
							!client.isCurrentScope(session.query_scope)
						}
						onClick={() => {
							if (
								!source.data ||
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
											source.data!.project,
											source.data!.asset,
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
							: weather
								? __("Use this weather source", "linker-tools")
								: __("Use this PV profile", "linker-tools")}
					</button>
					{source.data && (
						<PreparationBasis
							weather={source.data.weather}
							project={source.data.project}
							pv={!weather}
						/>
					)}
					<details className="lp-comparison">
						<summary>{__("Source and task checksums", "linker-tools")}</summary>
						<dl className="lp-run-facts">
							<dt>{__("Input SHA-256", "linker-tools")}</dt>
							<dd>{String(run.manifest.input_sha256)}</dd>
							<dt>{__("Task manifest SHA-256", "linker-tools")}</dt>
							<dd>{run.manifest_sha256}</dd>
							<dt>{__("Result SHA-256", "linker-tools")}</dt>
							<dd>{run.result_sha256}</dd>
							<dt>{__("Execution environment SHA-256", "linker-tools")}</dt>
							<dd>{String(run.result!.runtime_sha256)}</dd>
							<dt>{__("Source content SHA-256", "linker-tools")}</dt>
							<dd>{String(asset!.content_sha256)}</dd>
						</dl>
					</details>
				</>
			)}
		</div>
	);
}
