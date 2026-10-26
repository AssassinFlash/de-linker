import {
	isPlantEnergyTask,
	DC_PLANT_ENERGY_TASK,
} from "../../domain/plantEnergy.ts";
import { readObject } from "../../data/readProtocol.ts";
import type { JsonObject } from "../../data/protocol.ts";
import { runTask } from "../../data/planningProtocol.ts";
import { DC_ENERGY_TASK } from "../../domain/dcEnergy.ts";
import { lazy, Suspense, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import type { Session } from "../../data/protocol.ts";
import type { PlanningRun } from "../../data/planningProtocol.ts";
import {
	readTraceWindow,
	TRACE_FIELDS,
	traceCsv,
} from "../../data/traceWindow.ts";
import { __, sprintf } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";
import { ChartBoundary } from "./ChartBoundary.tsx";

const EnergyFlowChart = lazy(() => import("./EnergyFlowChart.tsx"));

export function TraceExplorer({
	run,
	client,
	session,
	locale,
	active,
}: {
	run: PlanningRun;
	client: PlannerClient;
	session: Session;
	locale: string;
	active: boolean;
}) {
	const [open, setOpen] = useState(false),
		[offset, setOffset] = useState(0),
		[first, setFirst] = useState("1");
	const [unitId, selectUnit] = useState<string | null>(null);
	const joint = isPlantEnergyTask(runTask(run));
	const plantDc = runTask(run) === DC_PLANT_ENERGY_TASK;
	const units = joint
		? (readObject(readObject(run.result?.equipment_binding).plant)
				.units as readonly JsonObject[])
		: [];
	const unitLabels = unitId
		? [
				__("Storage unit", "linker-tools"),
				plantDc
					? __(
							"DC charging power per storage unit (interval average, kW)",
							"linker-tools",
						)
					: __("Unit AC charging power (interval mean, kW)", "linker-tools"),
				plantDc
					? __(
							"DC discharging power per storage unit (interval average, kW)",
							"linker-tools",
						)
					: __("Unit AC discharging power (interval mean, kW)", "linker-tools"),
				__("Stored from PV (kWh)", "linker-tools"),
				__("Stored from grid (kWh)", "linker-tools"),
				__("Stored with unknown origin (kWh)", "linker-tools"),
			]
		: [];
	const pageSize = session.runtime.limits.max_page_size;
	const dc = runTask(run) === DC_ENERGY_TASK;
	const labels = useMemo(
		() => [
			__("Load", "linker-tools"),
			plantDc
				? __("PV at the common AC bus", "linker-tools")
				: dc
					? __("Available PV power (DC)", "linker-tools")
					: __("Available PV power", "linker-tools"),
			dc || plantDc
				? __("Charging power at the battery terminals (DC)", "linker-tools")
				: __("Charging power", "linker-tools"),
			dc || plantDc
				? __("Discharging power at the battery terminals (DC)", "linker-tools")
				: __("Discharging power", "linker-tools"),
			dc
				? __("Grid import (AC)", "linker-tools")
				: __("Grid import", "linker-tools"),
			dc
				? __("Grid export (AC)", "linker-tools")
				: __("Grid export", "linker-tools"),
			__("Stored energy", "linker-tools"),
		],
		[locale, dc, plantDc],
	);
	const query = useQuery({
		queryKey: [
			"planner",
			session.query_scope,
			"trace-window",
			run.id,
			run.result?.trace_sha256,
			offset,
			pageSize,
			unitId,
		],
		enabled:
			active &&
			open &&
			run.state === "succeeded" &&
			client.isCurrentScope(session.query_scope),
		staleTime: Infinity,
		retry: false,
		queryFn: async ({ signal }) =>
			readTraceWindow(
				await client.query(
					"runs/trace",
					{
						schema_version: 1,
						run_id: run.id,
						offset,
						page_size: pageSize,
						...(unitId ? { unit_id: unitId } : {}),
					},
					session.query_scope,
					signal,
				),
				run,
				offset,
				pageSize,
				unitId,
			),
	});
	const page =
		active && client.isCurrentScope(session.query_scope)
			? query.data
			: undefined;
	function move(next: number) {
		setOffset(next);
		setFirst(String(next + 1));
	}
	function download() {
		if (!page || !client.isCurrentScope(session.query_scope)) return;
		const blob = new Blob(
			[
				traceCsv(
					page,
					[
						"start_utc",
						"end_utc",
						...labels.map(
							(label, index) => `${label} (${index === 6 ? "kWh" : "kW"})`,
						),
					],
					unitLabels,
				),
			],
			{ type: "text/csv;charset=utf-8" },
		);
		const url = URL.createObjectURL(blob),
			link = document.createElement("a");
		link.href = url;
		link.download = `${run.id}-intervals-${page.offset + 1}-${page.offset + page.rows.length}.csv`;
		link.click();
		URL.revokeObjectURL(url);
	}
	return (
		<details
			className="lp-trace-explorer"
			onToggle={(event) => setOpen(event.currentTarget.open)}
		>
			<summary>{__("Energy flows", "linker-tools")}</summary>
			{open && (
				<>
					<p className="lp-profile-help">
						{__(
							"These saved values show mean power for each interval and stored energy at its end.",
							"linker-tools",
						)}
					</p>
					{joint && (
						<label className="lp-field">
							<span>{__("Storage unit", "linker-tools")}</span>
							<select
								value={unitId ?? ""}
								onChange={(e) => selectUnit(e.currentTarget.value || null)}
							>
								<option value="">
									{__("Shared AC metering point", "linker-tools")}
								</option>
								{units.map((u) => (
									<option key={String(u.id)} value={String(u.id)}>
										{String(u.name)}
									</option>
								))}
							</select>
						</label>
					)}
					{joint && (
						<p className="lp-profile-help">
							{plantDc
								? __(
										"Load, PV generation and grid import/export are shown at the common AC bus. The charging and discharging curves show the sum of the power at each battery’s DC terminals. Total stored energy is shown for reference. Select a storage unit to show its DC power and stored energy in the table.",
										"linker-tools",
									)
								: __(
										"The chart shows the shared AC metering point. Select a storage unit to add its AC power and stored-energy data to the table.",
										"linker-tools",
									)}
						</p>
					)}
					{query.isFetching && (
						<p role="status">
							{__("Loading interval values…", "linker-tools")}
						</p>
					)}
					{query.error && (
						<Notice error>
							{__("Interval values could not be loaded.", "linker-tools")}{" "}
							<button
								type="button"
								className="lp-text-button"
								onClick={() => void query.refetch()}
							>
								{__("Try again", "linker-tools")}
							</button>
						</Notice>
					)}
					{page && (
						<>
							<p>
								{sprintf(
									__("Intervals %1$d to %2$d of %3$d · UTC", "linker-tools"),
									page.offset + 1,
									page.offset + page.rows.length,
									page.interval_count,
								)}
							</p>
							<ChartBoundary>
								<Suspense
									fallback={
										<p role="status">
											{__("Loading interval values…", "linker-tools")}
										</p>
									}
								>
									<EnergyFlowChart
										page={page}
										labels={labels}
										locale={locale}
									/>
								</Suspense>
							</ChartBoundary>
							{unitId && (
								<div className="lp-table-scroll" tabIndex={0}>
									<table>
										<caption>
											{String(units.find((u) => u.id === unitId)?.name)}
										</caption>
										<thead>
											<tr>
												<th>{__("Start", "linker-tools")}</th>
												{unitLabels.slice(1).map((label) => (
													<th key={label}>{label}</th>
												))}
											</tr>
										</thead>
										<tbody>
											{page.rows.map((row) => {
												const u = row.unit!;
												return (
													<tr key={row.interval_index}>
														<th scope="row">{row.start_utc}</th>
														{[
															u.charge_kw,
															u.discharge_kw,
															u.after.pv_kwh,
															u.after.grid_kwh,
															u.after.initial_unknown_kwh,
														].map((n, index) => (
															<td key={index}>
																{new Intl.NumberFormat(locale, {
																	maximumFractionDigits: 5,
																}).format(n)}
															</td>
														))}
													</tr>
												);
											})}
										</tbody>
									</table>
								</div>
							)}
							<div className="lp-trace-controls">
								<button
									type="button"
									className="lp-button lp-button-secondary"
									disabled={!page.offset || query.isFetching}
									onClick={() => move(Math.max(0, page.offset - pageSize))}
								>
									{__("Previous intervals", "linker-tools")}
								</button>
								<button
									type="button"
									className="lp-button lp-button-secondary"
									disabled={page.next_offset === null || query.isFetching}
									onClick={() => {
										if (page.next_offset !== null) move(page.next_offset);
									}}
								>
									{__("Next intervals", "linker-tools")}
								</button>
								<button
									type="button"
									className="lp-text-button"
									onClick={download}
								>
									{__("Download displayed intervals (CSV)", "linker-tools")}
								</button>
							</div>
							<form
								className="lp-trace-controls"
								onSubmit={(event) => {
									event.preventDefault();
									const number = Number(first);
									if (
										Number.isSafeInteger(number) &&
										number >= 1 &&
										number <= page.interval_count
									)
										move(number - 1);
								}}
							>
								<label className="lp-field">
									<span>{__("First interval", "linker-tools")}</span>
									<input
										type="number"
										min={1}
										max={page.interval_count}
										step={1}
										required
										value={first}
										onChange={(event) => setFirst(event.currentTarget.value)}
									/>
								</label>
								<button
									type="submit"
									className="lp-button lp-button-secondary"
									disabled={query.isFetching}
								>
									{__("Show intervals", "linker-tools")}
								</button>
							</form>
							<details className="lp-comparison">
								<summary>{__("Interval values", "linker-tools")}</summary>
								<div className="lp-table-scroll lp-trace-table" tabIndex={0}>
									<table>
										<caption>
											{__("Interval values", "linker-tools")} · UTC
										</caption>
										<thead>
											<tr>
												<th>UTC</th>
												{labels.map((label, index) => (
													<th key={label}>
														{label} ({index === 6 ? "kWh" : "kW"})
													</th>
												))}
											</tr>
										</thead>
										<tbody>
											{page.rows.map((row) => (
												<tr key={row.interval_index}>
													<th scope="row">
														{row.start_utc}
														<br />
														{row.end_utc}
													</th>
													{TRACE_FIELDS.map((field) => (
														<td key={field}>
															{new Intl.NumberFormat(locale, {
																maximumFractionDigits: 6,
															}).format(row[field])}
														</td>
													))}
												</tr>
											))}
										</tbody>
									</table>
								</div>
							</details>
						</>
					)}
				</>
			)}
		</details>
	);
}
