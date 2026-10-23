import { useEffect, useRef, useState } from "react";
import type { GeometryDocument } from "../../domain/geometry.ts";
import { sameJson } from "../../domain/draft.ts";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import { ApiError } from "../../data/protocol.ts";
import type { Session } from "../../data/protocol.ts";
import { readObject } from "../../data/readProtocol.ts";
import { readLayoutReview } from "../../data/geometryReview.ts";
import type { LayoutReview } from "../../data/geometryReview.ts";
import { formatDecimal } from "../../domain/decimal.ts";
import { __, sprintf } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";

function issueLabel(kind: string): string {
	const labels: Record<string, string> = {
		north_reference_unspecified: __(
			"North reference is missing.",
			"linker-tools",
		),
		source_precision_unspecified: __(
			"Source measurement precision is unknown.",
			"linker-tools",
		),
		edge_clearance_unspecified: __(
			"Roof-edge clearance has not been specified.",
			"linker-tools",
		),
		obstacle_clearance_unspecified: __(
			"Obstacle clearance has not been specified.",
			"linker-tools",
		),
		invalid_roof_polygon: __(
			"The roof boundary or openings do not form a valid polygon.",
			"linker-tools",
		),
		invalid_obstacle_polygon: __(
			"The obstacle footprint is invalid.",
			"linker-tools",
		),
		obstacle_not_above_roof: __(
			"The obstacle does not extend above this roof face.",
			"linker-tools",
		),
		obstacle_outside_roof: __(
			"The obstacle projection extends outside this roof face.",
			"linker-tools",
		),
		invalid_keepout_polygon: __(
			"The keep-out footprint is invalid.",
			"linker-tools",
		),
		invalid_panel_projection: __(
			"A module projection cannot be resolved at the supported numerical precision.",
			"linker-tools",
		),
		numeric_resolution_unsupported: __(
			"Coordinate resolution exceeds this check's numerical support. The design remains available for correction.",
			"linker-tools",
		),
		panel_over_opening: __("A module overlaps a roof opening.", "linker-tools"),
		panel_outside_roof: __(
			"A module extends outside the roof boundary.",
			"linker-tools",
		),
		panel_edge_clearance: __(
			"A module is closer to the roof boundary than the declared clearance.",
			"linker-tools",
		),
		panel_projected_obstacle_overlap: __(
			"A module projection overlaps an obstacle projection.",
			"linker-tools",
		),
		panel_in_keepout: __("A module overlaps a keep-out area.", "linker-tools"),
		panel_obstacle_clearance: __(
			"A module is closer to an obstacle than the declared clearance.",
			"linker-tools",
		),
		panel_projected_overlap: __(
			"Two module projections overlap.",
			"linker-tools",
		),
	};
	return labels[kind] ?? __("Additional layout diagnostic.", "linker-tools");
}

export function LayoutReviewPanel({
	geometry,
	projectId,
	client,
	session,
	locale,
	recheck,
	select,
	disabled,
}: {
	geometry: GeometryDocument;
	projectId: string;
	client: PlannerClient;
	session: Session;
	locale: string;
	recheck: () => void;
	select: (id: string) => void;
	disabled: boolean;
}) {
	const [result, setResult] = useState<{
		input: GeometryDocument;
		report: LayoutReview;
	} | null>(null);
	const [busy, setBusy] = useState(false),
		[failed, setFailed] = useState(false);
	const mounted = useRef(true),
		abort = useRef<AbortController | null>(null);
	useEffect(() => {
		mounted.current = true;
		return () => {
			mounted.current = false;
			abort.current?.abort();
		};
	}, []);
	const current = result && sameJson(result.input, geometry);
	async function review() {
		if (busy || disabled) return;
		const input = geometry,
			controller = new AbortController();
		abort.current = controller;
		setBusy(true);
		setFailed(false);
		try {
			const report = readLayoutReview(
				await client.query(
					"geometry/review",
					{
						schema_version: 1,
						project_id: projectId,
						geometry: readObject(input),
					},
					session.query_scope,
					controller.signal,
				),
			);
			if (mounted.current && client.isCurrentScope(session.query_scope))
				setResult({ input, report });
		} catch (error) {
			if (!mounted.current || controller.signal.aborted) return;
			setFailed(true);
			if (error instanceof ApiError && [401, 403].includes(error.status))
				recheck();
		} finally {
			if (mounted.current) setBusy(false);
		}
	}
	return (
		<section
			className="lp-layout-review"
			aria-labelledby="lp-layout-review-heading"
		>
			<div className="lp-inline-actions">
				<h3 id="lp-layout-review-heading">
					{__("Layout check", "linker-tools")}
				</h3>
				<button
					type="button"
					className="lp-button lp-button-secondary"
					onClick={() => void review()}
					disabled={busy || disabled || !geometry.roofs.length}
				>
					{busy
						? __("Checking layout…", "linker-tools")
						: __("Check layout", "linker-tools")}
				</button>
			</div>
			<p className="lp-profile-help">
				{__(
					"The check compares full module projections, roof boundaries and openings, obstacles, keep-out areas and declared clearances in each roof plane. Structural, fire-safety, electrical and shading assessments are separate.",
					"linker-tools",
				)}
			</p>
			{failed && (
				<Notice error>
					{__(
						"The layout check could not be completed. The design and any previous check remain available.",
						"linker-tools",
					)}
				</Notice>
			)}
			{result && (
				<>
					<p
						role="status"
						className="lp-review-status"
						data-stale={!current || undefined}
					>
						{!current
							? __(
									"Previous check: the design has changed. A new check is required.",
									"linker-tools",
								)
							: result.report.geometry_status === "incomplete"
								? __(
										"Check incomplete. Some checks could not be performed.",
										"linker-tools",
									)
								: result.report.conflict_count
									? __("Layout conflicts detected.", "linker-tools")
									: __(
											"No conflicts detected in the completed plan checks.",
											"linker-tools",
										)}
					</p>
					{result.report.issues.length > 0 && (
						<ul className="lp-diagnostics">
							{result.report.issues.map((issue, index) => (
								<li key={index} data-category={issue.category}>
									<button
										type="button"
										className="lp-text-button"
										disabled={disabled || !current}
										onClick={() => select(issue.object_id)}
									>
										{issueLabel(issue.kind)}
									</button>
									<small>
										{issue.object_id}
										{issue.related_id ? ` · ${issue.related_id}` : ""}
									</small>
									{issue.actual_m !== null && (
										<span>
											{sprintf(
												__("Actual: %1$s m; required: %2$s m.", "linker-tools"),
												formatDecimal(issue.actual_m, locale),
												formatDecimal(issue.required_m, locale),
											)}
										</span>
									)}
								</li>
							))}
						</ul>
					)}
					{result.report.diagnostics_truncated && (
						<Notice>
							{sprintf(
								__(
									"%1$d diagnostics are shown out of %2$d. Further conflicts may remain.",
									"linker-tools",
								),
								result.report.issues.length,
								result.report.issue_count,
							)}
						</Notice>
					)}
					<details className="lp-comparison">
						<summary>
							{__("Method, inputs and numerical limits", "linker-tools")}
						</summary>
						<p>
							{__(
								"Missing source precision, north references and clearance values remain listed even when a plan check finds no geometric conflicts. Geometry checks do not provide engineering approval.",
								"linker-tools",
							)}
						</p>
						<dl className="lp-source-hashes">
							<dt>{__("Checker and geometry library", "linker-tools")}</dt>
							<dd>
								{result.report.checker} · Shapely{" "}
								{result.report.libraries.shapely} · GEOS{" "}
								{result.report.libraries.geos}
							</dd>
							<dt>{__("Geometry SHA-256", "linker-tools")}</dt>
							<dd>{result.report.geometry_sha256}</dd>
							<dt>{__("Calculation runtime SHA-256", "linker-tools")}</dt>
							<dd>{result.report.runtime_sha256}</dd>
							<dt>
								{__(
									"Observed coordinate granularity / supported maximum",
									"linker-tools",
								)}
							</dt>
							<dd>
								{result.report.uv_resolution_m} m /{" "}
								{result.report.limits.max_uv_resolution_m} m
							</dd>
							<dt>{__("Candidate checks / limit", "linker-tools")}</dt>
							<dd>
								{result.report.candidate_checks} /{" "}
								{result.report.limits.max_candidate_checks}
							</dd>
						</dl>
						<p>
							{__(
								"The numerical limit describes internal arithmetic support. It is not a surveying tolerance or an installation requirement.",
								"linker-tools",
							)}
						</p>
					</details>
				</>
			)}
		</section>
	);
}
