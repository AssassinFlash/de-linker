import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ApiError, type Session } from "../../data/protocol.ts";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import type { ReportOptions } from "../../data/planningReport.ts";
import type { RunSummary } from "../../data/planningProtocol.ts";
import { isEnergyTask } from "../../data/readEnergyResult.ts";
import {
	comparisonPair,
	COMPARISON_MODEL,
	readEnergyComparison,
} from "../../data/energyComparison.ts";
import { replacePlannerLocation } from "../../data/plannerLocation.ts";
import { __, sprintf } from "../../i18n.ts";
import { comparisonLabel } from "./comparisonLabels.ts";
import {
	equipmentStatus,
	equipmentCheckLabel,
} from "../equipment/equipmentLabels.ts";
import { Notice } from "../Notice.tsx";

export function EnergyComparison({
	projectId,
	runs,
	client,
	session,
	active,
	locale,
	recheck,
	reportDisabled,
	generateReport,
	openRun,
}: {
	projectId: string;
	runs: readonly RunSummary[];
	client: PlannerClient;
	session: Session;
	active: boolean;
	locale: string;
	recheck: () => void;
	reportDisabled: boolean;
	generateReport: (options: ReportOptions) => Promise<void>;
	openRun: (id: string) => void;
}) {
	const [pair, setPair] = useState<readonly [string, string]>(
		() =>
			comparisonPair(new URL(location.href).searchParams.get("compare")) ?? [
				"",
				"",
			],
	);
	const [retained, setRetained] = useState<Record<string, RunSummary>>({});
	const admitted = client.isCurrentScope(session.query_scope);
	const ready =
		pair.every((id) => /^[a-f0-9]{32}$/.test(id)) && pair[0] !== pair[1];
	const supported = session.runtime.models.comparison === COMPARISON_MODEL;
	const query = useQuery({
		queryKey: [
			session.query_scope,
			session.runtime.runtime_sha256,
			"energy-comparison",
			projectId,
			...pair,
		],
		staleTime: Infinity,
		enabled: active && admitted && ready && supported,
		retry: false,
		queryFn: async ({ signal }) =>
			readEnergyComparison(
				await client.query(
					"runs/compare",
					{
						schema_version: 1,
						project_id: projectId,
						baseline_run_id: pair[0],
						candidate_run_id: pair[1],
					},
					session.query_scope,
					signal,
				),
				projectId,
				pair[0],
				pair[1],
			),
	});
	useEffect(() => {
		if (
			query.error instanceof ApiError &&
			([401, 403].includes(query.error.status) ||
				query.error.code === "session_changed")
		)
			recheck();
	}, [query.error, recheck]);
	useEffect(() => {
		if (!active || !client.isCurrentScope(session.query_scope)) return;
		const url = new URL(location.href);
		if (url.searchParams.get("project") !== projectId) return;
		const previous = url.href;
		url.searchParams.delete("run");
		if (ready) url.searchParams.set("compare", pair.join(","));
		else url.searchParams.delete("compare");
		if (previous !== url.href) replacePlannerLocation(url);
	}, [active, pair, ready, projectId, client, session.query_scope]);
	if (!admitted) return null;
	const data = query.data;
	const choices = [
		...new Map(
			[...runs, ...Object.values(retained)]
				.filter((r) => r.state === "succeeded" && isEnergyTask(r.task_kind))
				.map((r) => [r.id, r]),
		).values(),
	];
	const label = (revision: number) =>
		sprintf(__("Input revision %d", "linker-tools"), revision);
	function choose(index: 0 | 1, id: string) {
		if (!client.isCurrentScope(session.query_scope)) return;
		const next: readonly [string, string] =
			index === 0 ? [id, pair[1]] : [pair[0], id];
		setPair(next);
		setRetained(
			Object.fromEntries(
				choices
					.filter((row) => next.includes(row.id))
					.map((row) => [row.id, row]),
			),
		);
	}
	const format = (value: number | null, unit: string) =>
		value === null
			? __("Not defined", "linker-tools")
			: `${new Intl.NumberFormat(locale, { maximumFractionDigits: 3 }).format(value * (unit === "%" ? 100 : 1))} ${unit}`;
	return (
		<section className="lp-scenario-block lp-energy-comparison">
			<h3>{__("Saved calculation comparison", "linker-tools")}</h3>
			{!supported && (
				<Notice>
					{__(
						"Saved calculation comparison is not available on this service version.",
						"linker-tools",
					)}
				</Notice>
			)}
			<p>
				{__(
					"Compare two saved energy calculations from this project using their original inputs and results.",
					"linker-tools",
				)}
			</p>
			<div className="lp-comparison-variants">
				{([0, 1] as const).map((index) => (
					<label className="lp-field" key={index}>
						<span>
							{index === 0
								? __("Baseline calculation", "linker-tools")
								: __("Comparison calculation", "linker-tools")}
						</span>
						<select
							value={pair[index]}
							onChange={(e) => choose(index, e.currentTarget.value)}
						>
							<option value="">{__("Choose an option", "linker-tools")}</option>
							{pair[index] && !choices.some((r) => r.id === pair[index]) && (
								<option value={pair[index]}>
									{data
										? label(
												(index === 0 ? data.baseline : data.candidate).revision,
											)
										: __("Selected calculation", "linker-tools")}
								</option>
							)}
							{choices.map((row) => (
								<option key={row.id} value={row.id}>
									{label(row.revision)} ·{" "}
									{new Intl.DateTimeFormat(locale, {
										dateStyle: "short",
										timeStyle: "short",
									}).format(row.created_at * 1000)}
								</option>
							))}
						</select>
					</label>
				))}
			</div>
			{pair[0] && pair[0] === pair[1] && (
				<Notice>
					{__("Choose two different calculations.", "linker-tools")}
				</Notice>
			)}
			{ready && supported && query.isPending && (
				<p role="status">
					{__("Reading saved calculation results…", "linker-tools")}
				</p>
			)}
			{query.error && (
				<Notice error>
					<p>
						{__(
							"The selected results could not be compared. Check that both calculations are available in this project.",
							"linker-tools",
						)}
					</p>
					<button
						type="button"
						className="lp-text-button"
						onClick={() => void query.refetch()}
					>
						{__("Read comparison again", "linker-tools")}
					</button>
				</Notice>
			)}
			{data && !query.error && (
				<>
					<div className="lp-comparison-variants">
						{([data.baseline, data.candidate] as const).map((ref) => (
							<div key={ref.run_id}>
								<h4>{label(ref.revision)}</h4>
								{ref.equipment_models.map((name, i) => (
									<p key={i}>{name}</p>
								))}
								<dl className="lp-field-summary">
									<div>
										<dt>{equipmentCheckLabel("usable_energy")}</dt>
										<dd>{format(ref.usable_window_kwh, "kWh")}</dd>
									</div>
									{(["modules_per_stack", "parallel_stacks"] as const).map(
										(field) =>
											ref[field] !== null && (
												<div key={field}>
													<dt>{equipmentCheckLabel(field)}</dt>
													<dd>
														{new Intl.NumberFormat(locale).format(ref[field])}
													</dd>
												</div>
											),
									)}
								</dl>
								{ref.equipment_status !== null && (
									<p>{equipmentStatus(ref.equipment_status)}</p>
								)}
								{ref.source_note && (
									<details>
										<summary>
											{__(
												"Source or assumption for storage parameters",
												"linker-tools",
											)}
										</summary>
										<p>{ref.source_note}</p>
									</details>
								)}
								<p>
									{ref.coupling === "shared_dc"
										? __("PV and battery share an inverter", "linker-tools")
										: __("Separate AC connections", "linker-tools")}
								</p>
								<p>
									{ref.scenario_constraint_status === "satisfied"
										? __("Scenario requirements met", "linker-tools")
										: __("Scenario requirements not met", "linker-tools")}
								</p>
								<button
									type="button"
									className="lp-text-button"
									onClick={() => openRun(ref.run_id)}
								>
									{__("Open saved calculation", "linker-tools")}
								</button>
							</div>
						))}
					</div>
					{!data.conditions_aligned && (
						<Notice>
							{__(
								"No differences are shown because the comparison conditions differ or are incomplete.",
								"linker-tools",
							)}
						</Notice>
					)}
					<p>
						{__(
							"Difference = comparison minus baseline. Differences in ratios are shown in percentage points. PV differences also require the same AC/DC boundary.",
							"linker-tools",
						)}
					</p>
					<div className="lp-table-scroll">
						<table className="lp-data-table">
							<thead>
								<tr>
									<th>{__("Result", "linker-tools")}</th>
									<th>{__("Baseline calculation", "linker-tools")}</th>
									<th>{__("Comparison calculation", "linker-tools")}</th>
									<th>{__("Difference", "linker-tools")}</th>
								</tr>
							</thead>
							<tbody>
								{data.metrics.map((row) => (
									<tr key={row.id}>
										<th scope="row">{comparisonLabel(row.id)}</th>
										<td>
											{format(row.baseline, row.unit)}
											{row.id === "pv_generation" || row.id === "pv_use"
												? ` (${row.baseline_boundary.toUpperCase()})`
												: ""}
										</td>
										<td>
											{format(row.candidate, row.unit)}
											{row.id === "pv_generation" || row.id === "pv_use"
												? ` (${row.candidate_boundary.toUpperCase()})`
												: ""}
										</td>
										<td>
											{row.delta === null
												? "—"
												: format(row.delta, row.delta_unit)}
										</td>
									</tr>
								))}
							</tbody>
						</table>
					</div>
					<details>
						<summary>{__("Comparison basis", "linker-tools")}</summary>
						<dl className="lp-field-summary">
							{data.conditions.map((c) => (
								<div key={c.id}>
									<dt>{comparisonLabel(c.id)}</dt>
									<dd>{comparisonLabel(c.status)}</dd>
								</div>
							))}
						</dl>
					</details>
					<details>
						<summary>
							{__("Design and assumption changes", "linker-tools")}
						</summary>
						<dl className="lp-field-summary">
							{data.differences.map((d) => (
								<div key={d.id}>
									<dt>{comparisonLabel(d.id)}</dt>
									<dd>
										{d.changed
											? __("Changed", "linker-tools")
											: __("Unchanged", "linker-tools")}
									</dd>
								</div>
							))}
						</dl>
					</details>
					<p>
						{__(
							"Matching comparison conditions do not establish manufacturer performance or installation approval.",
							"linker-tools",
						)}
					</p>
					<button
						type="button"
						className="lp-button"
						disabled={reportDisabled || query.isFetching}
						onClick={() =>
							void generateReport({
								locale: locale.startsWith("de") ? "de" : "en",
								energy_run_id: null,
								pv_run_id: null,
								equipment_run_id: null,
								logo: null,
								comparison: {
									baseline_run_id: data.baseline.run_id,
									candidate_run_id: data.candidate.run_id,
								},
							})
						}
					>
						{__("Save comparison in planning report", "linker-tools")}
					</button>
				</>
			)}
		</section>
	);
}
