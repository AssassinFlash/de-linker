import { Component, lazy, Suspense, useMemo, useState } from "react";
import type { ReactNode } from "react";
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

const EnergyFlowChart = lazy(() => import("./EnergyFlowChart.tsx"));

class ChartBoundary extends Component<
	{ children: ReactNode },
	{ failed: boolean }
> {
	state = { failed: false };
	static getDerivedStateFromError() {
		return { failed: true };
	}
	render() {
		return this.state.failed ? (
			<Notice>
				{__(
					"The chart could not be displayed. The interval table and CSV remain available.",
					"linker-tools",
				)}
			</Notice>
		) : (
			this.props.children
		);
	}
}

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
	const pageSize = session.runtime.limits.max_page_size;
	const labels = useMemo(
		() => [
			__("Load", "linker-tools"),
			__("Available PV power", "linker-tools"),
			__("Charging power", "linker-tools"),
			__("Discharging power", "linker-tools"),
			__("Grid import", "linker-tools"),
			__("Grid export", "linker-tools"),
			__("Stored energy", "linker-tools"),
		],
		[locale],
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
					{ schema_version: 1, run_id: run.id, offset, page_size: pageSize },
					session.query_scope,
					signal,
				),
				run,
				offset,
				pageSize,
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
				traceCsv(page, [
					"start_utc",
					"end_utc",
					...labels.map(
						(label, index) => `${label} (${index === 6 ? "kWh" : "kW"})`,
					),
				]),
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
