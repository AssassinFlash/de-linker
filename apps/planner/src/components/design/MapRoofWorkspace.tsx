import { useEffect, useRef, useState } from "react";
import type { ComponentProps } from "react";
import type { GeometryDocument } from "../../domain/geometry.ts";
import {
	appendMapRoofVertex,
	mapRoofDraftCommand,
} from "../../domain/mapRoofDraft.ts";
import type { MapRoofDraft, MapRoofFields } from "../../domain/mapRoofDraft.ts";
import {
	drawingBridge,
	mapPolygon,
	readMapPolygon,
} from "../../domain/mapDrawingGeometry.ts";
import { reconcileMapVertex } from "../../domain/mapRingEdit.ts";
import { applyGeometryCommand } from "../../domain/geometryCommands.ts";
import type { GeometryCommand } from "../../domain/geometryCommands.ts";
import { sameJson } from "../../domain/draft.ts";
import { useMapRoofDraft } from "../../data/useMapRoofDraft.ts";
import type { MapInteraction } from "../../data/mapInteraction.ts";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import { ApiError } from "../../data/protocol.ts";
import type { Session } from "../../data/protocol.ts";
import { readObject } from "../../data/readProtocol.ts";
import { readLayoutReview } from "../../data/geometryReview.ts";
import { __, sprintf } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";
import { revealActionResult } from "../revealActionResult.ts";
import { LazyMapViewport } from "./LazyMapViewport.tsx";
import { MapRoofProperties } from "./MapRoofProperties.tsx";

export function MapRoofWorkspace({
	geometry,
	confirmedGeometry,
	projectId,
	locale,
	session,
	client,
	recheck,
	recoveryScopes,
	recoveryChecking,
	commit,
	onActivity,
	...mapProps
}: Omit<ComponentProps<typeof LazyMapViewport>, "document" | "interaction"> & {
	geometry: GeometryDocument;
	confirmedGeometry: GeometryDocument | null;
	projectId: string;
	locale: string;
	session: Session;
	client: PlannerClient;
	recheck: () => void;
	recoveryScopes?: readonly string[] | undefined;
	recoveryChecking?: boolean | undefined;
	commit: (command: GeometryCommand) => boolean;
	onActivity: (active: boolean) => void;
}) {
	const journal = useMapRoofDraft({
		projectId,
		geometry,
		confirmedGeometry,
		locale,
		session,
		client,
		recoveryScopes,
		recoveryChecking,
	});
	const { drawing, active } = journal;
	const [error, setError] = useState<string | null>(null),
		[invalidField, setInvalidField] = useState<string | null>(null),
		[busy, setBusy] = useState(false),
		[applied, setApplied] = useState(false);
	const flight = useRef<AbortController | null>(null),
		mounted = useRef(true),
		result = useRef<HTMLElement>(null);
	const current = useRef({ geometry, active, drawing });
	current.current = { geometry, active, drawing };
	const stale = drawing !== null && !sameJson(drawing.before, geometry);
	const protectedResult =
		drawing?.prepared_geometry && sameJson(drawing.prepared_geometry, geometry);
	let geographicReady = true;
	try {
		drawingBridge(geometry);
	} catch {
		geographicReady = false;
	}
	useEffect(() => {
		onActivity(active || busy || (journal.writing && drawing !== null));
		return () => onActivity(false);
	}, [active, busy, journal.writing, drawing !== null, onActivity]);
	useEffect(() => {
		mounted.current = true;
		return () => {
			mounted.current = false;
			flight.current?.abort();
		};
	}, []);
	useEffect(() => {
		if (applied) revealActionResult(result.current);
	}, [applied]);
	function change(next: MapRoofDraft) {
		if (busy || !client.isCurrentScope(session.query_scope)) return;
		setError(null);
		setInvalidField(null);
		setApplied(false);
		void journal.update(next).catch(() => undefined);
	}
	function field<K extends keyof MapRoofFields>(
		name: K,
		value: MapRoofFields[K],
	) {
		if (drawing)
			change({
				...drawing,
				prepared_geometry: null,
				fields: { ...drawing.fields, [name]: value },
			});
	}
	function inputFailure() {
		setError(
			__(
				"The point or edit could not be accepted. Your previous drawing is still available.",
				"linker-tools",
			),
		);
	}
	const interaction: MapInteraction | null =
		active && drawing && !stale && !busy
			? {
					key: drawing.key,
					phase: drawing.phase,
					vertices: drawing.vertices,
					referencePosition: drawing.height_reference_position,
					append(point) {
						try {
							change(appendMapRoofVertex(journal.latest.current!, point));
						} catch {
							inputFailure();
						}
					},
					transaction(transaction) {
						try {
							const value = journal.latest.current!;
							let ring = { geographic: value.vertices, metric: value.vertices };
							for (const step of transaction.steps) {
								if (step.action === "draw")
									throw new Error("unexpected_draw_transaction");
								ring = reconcileMapVertex(
									ring,
									readMapPolygon(step.geometry),
									step.action,
									(point) => point,
								);
							}
							change({
								...value,
								vertices: ring.geographic,
								prepared_geometry: null,
							});
						} catch {
							inputFailure();
							void journal.pause();
						}
					},
					failed() {
						inputFailure();
						void journal.pause();
					},
					interrupted() {
						void journal.pause();
					},
				}
			: null;
	async function apply() {
		const value = journal.latest.current;
		if (
			!value ||
			flight.current ||
			stale ||
			!client.isCurrentScope(session.query_scope)
		)
			return;
		const controller = new AbortController();
		flight.current = controller;
		setBusy(true);
		setError(null);
		setInvalidField(null);
		if (!(await journal.flush())) {
			flight.current = null;
			setBusy(false);
			return;
		}
		let command: GeometryCommand, result: GeometryDocument;
		try {
			command = mapRoofDraftCommand(value);
			result = applyGeometryCommand(value.before, command);
		} catch (cause) {
			const field = (cause as { field?: unknown } | null)?.field;
			setInvalidField(typeof field === "string" ? field : null);
			setError(
				__(
					"Some roof or source details are missing or invalid. Review the roof properties and source permissions. Your entries have been kept.",
					"linker-tools",
				),
			);
			flight.current = null;
			setBusy(false);
			return;
		}
		const admitted = () =>
			mounted.current &&
			flight.current === controller &&
			!controller.signal.aborted &&
			client.isCurrentScope(session.query_scope) &&
			current.current.active &&
			current.current.drawing?.key === value.key &&
			sameJson(current.current.geometry, value.before) &&
			sameJson(journal.latest.current, value);
		try {
			const report = readLayoutReview(
				await client.query(
					"geometry/review",
					{
						schema_version: 1,
						project_id: projectId,
						geometry: readObject(result),
					},
					session.query_scope,
					controller.signal,
				),
			);
			if (!admitted()) return;
			const roofId = "roof_" + value.key.replaceAll("-", "");
			if (
				!report.review_complete ||
				report.diagnostics_truncated ||
				report.issues.some(
					(issue) =>
						(issue.object_id === roofId || issue.roof_id === roofId) &&
						(issue.category === "numerical_limit" ||
							issue.kind === "invalid_roof_polygon"),
				)
			) {
				setError(
					__(
						"This roof boundary could not pass the geometry check. Its points remain available for correction.",
						"linker-tools",
					),
				);
				return;
			}
			// Protect both sides of the commit/persist boundary before exposing a
			// project change. Unknown storage outcomes never discard raw vertices.
			await journal.update({ ...value, prepared_geometry: result });
			if (
				!mounted.current ||
				flight.current !== controller ||
				!client.isCurrentScope(session.query_scope) ||
				!sameJson(current.current.geometry, value.before)
			)
				return;
			if (!commit(command)) {
				setError(
					__(
						"The project changed before this roof could be added. The drawing has been kept.",
						"linker-tools",
					),
				);
				return;
			}
			journal.deactivate();
			setApplied(true);
		} catch (cause) {
			if (!mounted.current || controller.signal.aborted) return;
			setError(
				__(
					"The roof check or local save could not be completed. The drawing and its entered values remain available.",
					"linker-tools",
				),
			);
			if (
				cause instanceof ApiError &&
				([401, 403].includes(cause.status) || cause.code === "session_changed")
			)
				recheck();
		} finally {
			if (mounted.current && flight.current === controller) {
				flight.current = null;
				setBusy(false);
			}
		}
	}
	return (
		<div className="lp-map-workspace">
			<section
				ref={result}
				tabIndex={-1}
				className="lp-map-drawing lp-focus-target"
				aria-label={__("Map roof drawing", "linker-tools")}
			>
				<div className="lp-inline-actions">
					<h3>{__("Draw a roof face", "linker-tools")}</h3>
					{!active && !drawing && (
						<button
							className="lp-button"
							type="button"
							disabled={
								mapProps.disabled ||
								journal.checking ||
								journal.storageFailed ||
								!geographicReady
							}
							onClick={() => {
								setApplied(false);
								setError(null);
								journal.begin(null);
							}}
						>
							{__("Start roof drawing", "linker-tools")}
						</button>
					)}
				</div>
				<p className="lp-profile-help">
					{__(
						"The outline and roof properties form an editable roof face. The source and permissions stay with it in the project, alongside the plan and 3D views.",
						"linker-tools",
					)}
				</p>
				{journal.checking && (
					<p role="status">{__("Checking saved drawings…", "linker-tools")}</p>
				)}
				{journal.storageFailed && (
					<Notice error>
						<p>
							{drawing
								? __(
										"The browser recovery copy could not be updated. The drawing remains open in this tab. Retrying keeps a different version saved by another tab.",
										"linker-tools",
									)
								: __(
										"Saved drawings could not be read from this browser. Retry to check for an unfinished drawing.",
										"linker-tools",
									)}
						</p>
						{drawing && (
							<div className="lp-inline-actions">
								<button
									className="lp-button lp-button-secondary"
									type="button"
									disabled={journal.writing || busy}
									onClick={() => void journal.retry()}
								>
									{__("Retry local save", "linker-tools")}
								</button>
								<button
									className="lp-button lp-button-secondary"
									type="button"
									disabled={journal.writing || busy}
									onClick={journal.fork}
								>
									{__("Save as separate drawing", "linker-tools")}
								</button>
							</div>
						)}
						{!drawing && (
							<button
								type="button"
								className="lp-button lp-button-secondary"
								disabled={journal.checking}
								onClick={journal.reload}
							>
								{__("Retry reading saved drawings", "linker-tools")}
							</button>
						)}
					</Notice>
				)}
				{!active && !drawing && journal.records.length > 0 && (
					<ul className="lp-drawing-recoveries">
						{journal.records.map((record) => (
							<li key={record.scope + record.drawing.key}>
								<span>
									{record.drawing.fields.name ||
										__("Unfinished roof drawing", "linker-tools")}
									<small>
										{sprintf(
											__("Recorded corners: %d", "linker-tools"),
											record.drawing.vertices.length,
										)}
									</small>
								</span>
								<button
									type="button"
									className="lp-button lp-button-secondary"
									disabled={mapProps.disabled || journal.checking}
									onClick={() => journal.begin(record)}
								>
									{__("Open saved drawing", "linker-tools")}
								</button>
							</li>
						))}
					</ul>
				)}
				{drawing && (
					<>
						<p className="lp-drawing-status" role="status">
							{busy
								? __("Checking roof geometry…", "linker-tools")
								: journal.writing
									? __("Saving drawing in this browser…", "linker-tools")
									: active
										? sprintf(
												__("Recorded corners: %d", "linker-tools"),
												drawing.vertices.length,
											)
										: protectedResult
											? __(
													"Roof added to the project draft. Save project stores it with the project.",
													"linker-tools",
												)
											: __(
													"Drawing paused and retained in this browser.",
													"linker-tools",
												)}
						</p>
						{stale && !protectedResult && (
							<Notice error>
								{__(
									"The project geometry has changed since this drawing began. The original drawing is retained; it cannot be applied to this changed geometry.",
									"linker-tools",
								)}
							</Notice>
						)}
						{active && !stale && drawing.phase === "collecting" && (
							<>
								<p>
									{__(
										"Each map click records one corner. Panning and zooming keep the recorded points. At least three corners are needed before closing the outline.",
										"linker-tools",
									)}
								</p>
								<div className="lp-inline-actions">
									<button
										type="button"
										className="lp-button"
										disabled={drawing.vertices.length < 3 || busy}
										onClick={() => {
											try {
												readMapPolygon(mapPolygon(drawing.vertices));
												change({ ...drawing, phase: "staged" });
											} catch {
												inputFailure();
											}
										}}
									>
										{__("Close outline and review", "linker-tools")}
									</button>
									<button
										type="button"
										className="lp-button lp-button-secondary"
										disabled={!drawing.vertices.length || busy}
										onClick={() =>
											change({
												...drawing,
												vertices: drawing.vertices.slice(0, -1),
											})
										}
									>
										{__("Remove last corner", "linker-tools")}
									</button>
								</div>
							</>
						)}

						<div className="lp-inline-actions">
							{active && drawing.phase === "staged" && !stale && (
								<a
									className="lp-button lp-button-secondary"
									href="#lp-map-roof-properties"
								>
									{__("Roof properties", "linker-tools")}
								</a>
							)}
							{active ? (
								<button
									type="button"
									className="lp-button lp-button-secondary"
									disabled={busy || journal.writing}
									onClick={() => void journal.pause()}
								>
									{__("Pause drawing", "linker-tools")}
								</button>
							) : (
								!protectedResult && (
									<button
										type="button"
										className="lp-button lp-button-secondary"
										disabled={busy || stale || mapProps.disabled}
										onClick={journal.resume}
									>
										{__("Resume drawing", "linker-tools")}
									</button>
								)
							)}
							<button
								type="button"
								className="lp-text-button"
								disabled={busy || journal.writing}
								onClick={() =>
									protectedResult ? journal.hide() : void journal.discard()
								}
							>
								{protectedResult
									? __("Close drawing preview", "linker-tools")
									: __("Discard drawing", "linker-tools")}
							</button>
						</div>
					</>
				)}
				{error &&
					!(active && drawing && drawing.phase === "staged" && !stale) && (
						<Notice error>{error}</Notice>
					)}
			</section>
			<LazyMapViewport
				{...mapProps}
				document={geometry}
				interaction={interaction}
			/>
			{active && drawing && drawing.phase === "staged" && !stale && (
				<MapRoofProperties
					drawing={drawing}
					locale={locale}
					busy={busy}
					invalidField={invalidField}
					error={error}
					field={field}
					submit={() => void apply()}
					continueDrawing={() =>
						change({ ...drawing, phase: "collecting", prepared_geometry: null })
					}
				/>
			)}
		</div>
	);
}
