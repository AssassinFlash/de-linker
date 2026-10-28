import { useMemo, useState } from "react";
import type { PlanningRun } from "../../data/planningProtocol.ts";
import type { JsonObject, Session } from "../../data/protocol.ts";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import { readDirectBeamResult } from "../../data/directBeamResult.ts";
import { panelPoses } from "../../domain/panelPoses.ts";
import { LazySceneViewport } from "../design/LazySceneViewport.tsx";
import { __, sprintf } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";
import { runStateLabel, taskLabel } from "./planningLabels.ts";
import { DIRECT_BEAM_TASK } from "../../domain/directBeam.ts";

export function DirectBeamResult({
	run,
	session,
	client,
	locale,
	sceneModuleUrl,
}: {
	run: PlanningRun;
	session: Session;
	client: PlannerClient;
	locale: string;
	sceneModuleUrl: string | null;
}) {
	const [time, setTime] = useState(0),
		[scene, setScene] = useState(false),
		[selected, select] = useState<string | null>(null);
	const parsed = useMemo(() => {
		if (!run.result) return null;
		try {
			return readDirectBeamResult(
				run.result,
				run as unknown as JsonObject,
				run.manifest,
			);
		} catch {
			return null;
		}
	}, [run]);
	const row = parsed?.rows[time],
		fractions = useMemo(
			() =>
				new Map(
					row?.modules.map((m) => [
						m.module_id,
						m.fine?.visible_fraction ?? null,
					]),
				),
			[row],
		);
	const poses = useMemo(
		() => (parsed ? panelPoses(parsed.geometry) : []),
		[parsed],
	);
	const n = (v: number) =>
		new Intl.NumberFormat(locale, { maximumFractionDigits: 3 }).format(v);
	const percent = (v: number | null | undefined) =>
		v === null || v === undefined
			? "—"
			: new Intl.NumberFormat(locale, {
					style: "percent",
					maximumFractionDigits: 3,
				}).format(v);
	const moduleName = (id: string) => {
		const pose = poses.find((p) => p.id === id),
			array = parsed?.geometry.arrays.find((a) => a.id === pose?.array_id);
		return pose
			? sprintf(
					__("%s · row %d, column %d", "linker-tools"),
					array?.name ?? "",
					pose.row + 1,
					pose.column + 1,
				)
			: (parsed?.geometry.obstacles.find((p) => p.id === id)?.name ??
					parsed?.geometry.roofs.find((p) => p.id === id)?.name ??
					__("Unidentified blocker", "linker-tools"));
	};
	if (!client.isCurrentScope(session.query_scope))
		return (
			<Notice>
				{__(
					"The saved result is hidden until this session is verified.",
					"linker-tools",
				)}
			</Notice>
		);
	return (
		<section className="lp-run-result">
			<div className="lp-run-heading">
				<h3 tabIndex={-1}>{taskLabel(DIRECT_BEAM_TASK)}</h3>
				<span role="status">{runStateLabel(run.state, DIRECT_BEAM_TASK)}</span>
			</div>
			<p>{sprintf(__("Revision %d", "linker-tools"), run.revision)}</p>
			<p>
				{__(
					"These fractions describe the sampled geometric path to direct sunlight. They are not electrical losses, annual yield or equipment and grid approval.",
					"linker-tools",
				)}
			</p>
			{!run.is_current && (
				<Notice>
					{__(
						"This result uses an earlier saved roof and source selection. The 3D view below shows that frozen geometry, not the current draft.",
						"linker-tools",
					)}
				</Notice>
			)}
			{run.state === "failed" && (
				<Notice error>
					<p>
						{__(
							"The visibility calculation ended without a usable result. No PV profile or loss result was created.",
							"linker-tools",
						)}
					</p>
					<p>
						{run.error?.code === "product_evidence_changed"
							? __(
									"The module source information has changed or is no longer available. Review the roof module selection before making a new request.",
									"linker-tools",
								)
							: run.error?.code === "version_unavailable"
								? __(
										"A saved source or calculation version could not be verified. The original request and saved project remain available.",
										"linker-tools",
									)
								: __(
										"Review the selected source rows, roof geometry and sampling budget. Numerical ambiguity or an exhausted budget stops calculation; it does not imply full geometric visibility.",
										"linker-tools",
									)}
					</p>
				</Notice>
			)}
			{run.state === "cancelled" && (
				<Notice>
					{__(
						"This geometric task was cancelled. No visibility fraction is available from it.",
						"linker-tools",
					)}
				</Notice>
			)}
			{run.state === "succeeded" && !parsed && (
				<Notice error>
					{__(
						"The geometric result could not be verified against its saved run and geometry. No overlay is shown.",
						"linker-tools",
					)}
				</Notice>
			)}
			{parsed && row && (
				<>
					<label className="lp-field">
						<span>
							{__("Selected source irradiance timestamp (UTC)", "linker-tools")}
						</span>
						<select
							value={time}
							onChange={(e) => {
								setTime(Number(e.currentTarget.value));
								select(null);
							}}
						>
							{parsed.rows.map((r, i) => (
								<option key={r.source_row_index} value={i}>
									{r.irradiance_at_utc}
								</option>
							))}
						</select>
					</label>
					<dl className="lp-run-facts">
						<dt>{__("Synthetic interval (UTC)", "linker-tools")}</dt>
						<dd>
							<time>{row.interval_start_utc}</time> →{" "}
							<time>{row.interval_end_utc}</time>
						</dd>
						<dt>{__("Original source label (UTC)", "linker-tools")}</dt>
						<dd>
							<time>{row.source_label_utc}</time>
						</dd>
						<dt>{__("Source irradiance timestamp (UTC)", "linker-tools")}</dt>
						<dd>
							<time>{row.irradiance_at_utc}</time>
						</dd>
						<dt>{__("Midpoint samples evaluated", "linker-tools")}</dt>
						<dd>{n(parsed.sampling.sample_count)}</dd>
					</dl>
					<button
						type="button"
						className="lp-button lp-button-secondary"
						aria-expanded={scene}
						onClick={() => setScene(!scene)}
					>
						{scene
							? __("Hide geometric 3D overlay", "linker-tools")
							: __("Show geometric 3D overlay", "linker-tools")}
					</button>
					{scene && (
						<>
							<p>
								{__(
									"Lighter teal means greater sampled direct-beam visibility; darker teal means less. Grey modules have no defined fraction at this timestamp. Colours do not represent power or energy.",
									"linker-tools",
								)}
							</p>
							<LazySceneViewport
								sceneModuleUrl={sceneModuleUrl}
								document={parsed.geometry}
								poses={poses}
								directBeam={fractions}
								selected={selected}
								select={select}
								commit={() => false}
								disabled
							/>
						</>
					)}
					<p>
						{__(
							"The coarse and fine grids are equal-area midpoint samples. Their absolute difference describes the observed change between these resolutions; it is not an error bound. Night and back-facing or tangent modules have no fraction.",
							"linker-tools",
						)}
					</p>
					<div className="lp-table-scroll">
						<table className="lp-data-table">
							<thead>
								<tr>
									<th>{__("Module", "linker-tools")}</th>
									<th>{__("Geometric status", "linker-tools")}</th>
									<th>{__("Coarse visibility", "linker-tools")}</th>
									<th>{__("Fine visibility", "linker-tools")}</th>
									<th>
										{__(
											"Observed difference (percentage points)",
											"linker-tools",
										)}
									</th>
								</tr>
							</thead>
							<tbody>
								{row.modules.map((m) => (
									<tr
										key={m.module_id}
										aria-selected={selected === m.module_id}
									>
										<td>
											<button
												type="button"
												className="lp-text-button"
												onClick={() => select(m.module_id)}
											>
												{moduleName(m.module_id)}
											</button>
										</td>
										<td>
											{m.status === "sampled"
												? __("Sampled", "linker-tools")
												: m.status === "night"
													? __("Sun at or below horizon", "linker-tools")
													: __("Back-facing or tangent", "linker-tools")}
										</td>
										<td>{percent(m.coarse?.visible_fraction)}</td>
										<td>{percent(m.fine?.visible_fraction)}</td>
										<td>
											{m.observed_absolute_delta === null
												? "—"
												: n(m.observed_absolute_delta * 100)}
										</td>
									</tr>
								))}
							</tbody>
						</table>
					</div>
					<details>
						<summary>
							{__("Sampling cost and blockers", "linker-tools")}
						</summary>
						<dl className="lp-run-facts">
							<dt>{__("Coarse grid cells per module edge", "linker-tools")}</dt>
							<dd>{parsed.sampling.coarse_cells_per_edge}</dd>
							<dt>{__("Fine grid cells per module edge", "linker-tools")}</dt>
							<dd>{parsed.sampling.fine_cells_per_edge}</dd>
							<dt>{__("Face intersection checks", "linker-tools")}</dt>
							<dd>
								{n(parsed.sampling.ray_face_checks)} /{" "}
								{n(parsed.limits.max_ray_face_checks)}
							</dd>
							<dt>{__("Bounding-box checks", "linker-tools")}</dt>
							<dd>
								{n(parsed.sampling.bounds_checks)} /{" "}
								{n(parsed.limits.max_bounds_checks)}
							</dd>
						</dl>
						<p>
							{__(
								"Blocker sample counts can overlap and must not be added into a loss fraction.",
								"linker-tools",
							)}
						</p>
						{row.modules
							.filter(
								(m) =>
									m.fine && Object.keys(m.fine.blocker_sample_counts).length,
							)
							.map((m) => (
								<div key={m.module_id}>
									<strong>{moduleName(m.module_id)}</strong>
									<ul>
										{Object.entries(m.fine!.blocker_sample_counts).map(
											([id, count]) => (
												<li key={id}>
													{moduleName(id)}: {count} / {m.fine!.sample_count}
												</li>
											),
										)}
									</ul>
								</div>
							))}
					</details>
				</>
			)}
		</section>
	);
}
