import { useEffect, useRef, useState } from "react";
import type { ComponentProps } from "react";
import type { GeometryDocument } from "../../domain/geometry.ts";
import type { MapRoofFields } from "../../domain/mapRoofDraft.ts";
import type { MapFeatureFields } from "../../domain/mapFeatureDraft.ts";
import type { MapDrawingDraft } from "../../domain/mapDrawingDraft.ts";
import {
	editMapDrawingVertex,
	mapDrawingDraftCommand,
	appendMapDrawingVertex,
	mapDrawingVertices,
	mapDrawingReviewTarget,
} from "../../domain/mapDrawingDraft.ts";
import {
	drawingBridge,
	mapPolygon,
	readMapPolygon,
} from "../../domain/mapDrawingGeometry.ts";
import { applyGeometryCommand } from "../../domain/geometryCommands.ts";
import type { GeometryCommand } from "../../domain/geometryCommands.ts";
import { sameJson } from "../../domain/draft.ts";
import { useMapDrawingDraft } from "../../data/useMapDrawingDraft.ts";
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
import { MapRingProperties } from "./MapRingProperties.tsx";
import { MapRingSelector } from "./MapRingSelector.tsx";
import { MapFeatureSelector } from "./MapFeatureSelector.tsx";
import { MapFeatureProperties } from "./MapFeatureProperties.tsx";
import { mapDrawingName, mapFeatureContext } from "./mapDrawingLabels.ts";

export function MapDrawingWorkspace({
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
	const journal = useMapDrawingDraft({
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
		[unchanged, setUnchanged] = useState(false),
		[completedApplications, setCompletedApplications] = useState(0);
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
	const canStartDrawing =
		!mapProps.disabled &&
		!journal.checking &&
		!journal.storageFailed &&
		geographicReady;
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
		if (completedApplications > 0) revealActionResult(result.current);
	}, [completedApplications]);
	useEffect(
		() => setUnchanged(false),
		[geometry, projectId, session.query_scope, mapProps.selected],
	);
	function begin(input: Parameters<typeof journal.begin>[0]) {
		setError(null);
		setInvalidField(null);
		setUnchanged(false);
		try {
			journal.begin(input);
		} catch {
			setError(
				__(
					"This boundary cannot be edited on the map. Numeric properties remain available.",
					"linker-tools",
				),
			);
		}
	}
	function change(next: MapDrawingDraft) {
		if (busy || !client.isCurrentScope(session.query_scope)) return;
		setError(null);
		setInvalidField(null);
		setUnchanged(false);
		void journal.update(next).catch(() => undefined);
	}
	function field<K extends keyof MapRoofFields>(
		name: K,
		value: MapRoofFields[K],
	) {
		if (drawing?.schema_version === 1)
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
	function featureField<K extends keyof MapFeatureFields>(
		name: K,
		value: MapFeatureFields[K],
	) {
		if (drawing?.schema_version === 3)
			change({
				...drawing,
				prepared_geometry: null,
				fields: {
					...drawing.fields,
					[name]: value,
					source_confirmed: name === "source_confirmed" && value === true,
				},
			});
	}
	const interaction: MapInteraction | null =
		active && drawing && !stale && !busy
			? {
					key: drawing.key,
					phase: drawing.phase,
					vertices: drawing.vertices,
					referencePosition:
						drawing.schema_version === 1
							? drawing.height_reference_position
							: null,
					append(point) {
						try {
							const value = journal.latest.current;
							if (!value) throw new Error("unexpected_append");
							change(appendMapDrawingVertex(value, point));
						} catch {
							inputFailure();
						}
					},
					transaction(transaction) {
						try {
							let value = journal.latest.current!;
							for (const step of transaction.steps) {
								if (step.action === "draw")
									throw new Error("unexpected_draw_transaction");
								value = editMapDrawingVertex(value, step.geometry, step.action);
							}
							change(value);
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
			command = mapDrawingDraftCommand(value);
			result = applyGeometryCommand(value.before, command);
		} catch (cause) {
			const field = (cause as { field?: unknown } | null)?.field;
			setInvalidField(typeof field === "string" ? field : null);
			setError(
				value.schema_version === 3
					? __(
							"Some feature or source details are missing or invalid. Your entries have been kept.",
							"linker-tools",
						)
					: value.schema_version === 2
						? __(
								"Review the boundary and its recorded source details. Your edits have been kept.",
								"linker-tools",
							)
						: __(
								"Some roof or source details are missing or invalid. Review the roof properties and source permissions. Your entries have been kept.",
								"linker-tools",
							),
			);
			flight.current = null;
			setBusy(false);
			return;
		}
		const admitted = (expected: MapDrawingDraft = value) =>
			mounted.current &&
			flight.current === controller &&
			!controller.signal.aborted &&
			client.isCurrentScope(session.query_scope) &&
			current.current.active &&
			current.current.drawing?.key === value.key &&
			sameJson(current.current.geometry, value.before) &&
			sameJson(journal.latest.current, expected);
		try {
			if (!admitted()) return;
			const changed = !sameJson(result, value.before);
			if (changed) {
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
				const target = mapDrawingReviewTarget(value);
				if (
					!report.review_complete ||
					report.diagnostics_truncated ||
					report.issues.some(
						(issue) =>
							(issue.object_id === target.id &&
								issue.kind === target.invalid) ||
							// An invalid parent roof makes the service skip its shapes.
							// Absence of a target diagnostic cannot validate that shape.
							(issue.object_id === target.roof &&
								issue.kind === "invalid_roof_polygon") ||
							((issue.object_id === target.id ||
								issue.roof_id === target.roof) &&
								issue.category === "numerical_limit"),
					)
				) {
					setError(
						value.schema_version !== 1
							? __(
									"The geometry check could not validate this boundary. Your edits remain available for correction.",
									"linker-tools",
								)
							: __(
									"This roof boundary could not pass the geometry check. Its points remain available for correction.",
									"linker-tools",
								),
					);
					return;
				}
			}
			// Protect both sides of the commit/persist boundary before exposing a
			// project change. Unknown storage outcomes never discard raw vertices.
			const prepared = { ...value, prepared_geometry: result };
			await journal.update(prepared);
			if (!admitted(prepared)) return;
			if (changed && !commit(command)) {
				setError(
					value.schema_version !== 1
						? __(
								"The project changed before this boundary edit could be applied. Your edit has been kept.",
								"linker-tools",
							)
						: __(
								"The project changed before this roof could be added. The drawing has been kept.",
								"linker-tools",
							),
				);
				return;
			}
			setUnchanged(!changed);
			journal.deactivate();
			setCompletedApplications((count) => count + 1);
		} catch (cause) {
			if (!mounted.current || controller.signal.aborted) return;
			setError(
				value.schema_version !== 1
					? __(
							"The boundary check or browser save could not be completed. Your edits remain available.",
							"linker-tools",
						)
					: __(
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
	function drawingStatus(): string {
		if (!drawing) return "";
		if (busy)
			return drawing.schema_version === 1
				? __("Checking roof geometry…", "linker-tools")
				: __("Checking boundary geometry…", "linker-tools");
		if (journal.writing)
			return __("Saving drawing in this browser…", "linker-tools");
		if (active)
			return sprintf(
				__("Recorded corners: %d", "linker-tools"),
				drawing.vertices.length,
			);
		if (!protectedResult)
			return __("Drawing paused and retained in this browser.", "linker-tools");
		if (drawing.schema_version === 1)
			return __(
				"Roof added to the project draft. Save project stores it with the project.",
				"linker-tools",
			);
		if (drawing.schema_version === 3)
			return __(
				"Feature added to the project draft. Choose Save project to save it.",
				"linker-tools",
			);
		return sameJson(drawing.prepared_geometry, drawing.before)
			? __(
					"The boundary is unchanged. No project change was made.",
					"linker-tools",
				)
			: __(
					"Boundary changes applied to the project draft. Choose Save project to save them.",
					"linker-tools",
				);
	}
	return (
		<div className="lp-map-workspace">
			<section
				ref={result}
				tabIndex={-1}
				className="lp-map-drawing lp-focus-target"
				aria-label={__("Map drawing", "linker-tools")}
			>
				<div className="lp-inline-actions">
					<h3>
						{drawing?.schema_version === 2
							? __("Edit an existing boundary", "linker-tools")
							: drawing?.schema_version === 3
								? __("Draw a roof feature", "linker-tools")
								: drawing
									? __("Draw a roof face", "linker-tools")
									: __("Map drawing", "linker-tools")}
					</h3>
					{!active && !drawing && (
						<button
							className="lp-button"
							type="button"
							disabled={!canStartDrawing}
							onClick={() => begin({ kind: "new_roof" })}
						>
							{__("Start roof drawing", "linker-tools")}
						</button>
					)}
				</div>
				{drawing?.schema_version === 3 && (
					<p className="lp-profile-help">{mapFeatureContext(drawing)}</p>
				)}
				<p className="lp-profile-help">
					{drawing?.schema_version === 3
						? __(
								"The outline lies in the selected roof plane. Check the source details and feature properties before adding it to the project draft.",
								"linker-tools",
							)
						: drawing?.schema_version === 2
							? __(
									"The roof plane stays fixed while you edit this boundary. Applied changes appear in this project's map, plan and 3D views.",
									"linker-tools",
								)
							: __(
									"The outline and roof properties form an editable roof face. The source and permissions stay with it in the project, alongside the plan and 3D views.",
									"linker-tools",
								)}
				</p>
				{!drawing && (
					<>
						<MapRingSelector
							geometry={geometry}
							selected={mapProps.selected}
							disabled={!canStartDrawing}
							begin={(target) => begin({ kind: "edit_ring", target })}
						/>
						<MapFeatureSelector
							geometry={geometry}
							selected={mapProps.selected}
							disabled={!canStartDrawing}
							begin={(target) => begin({ kind: "new_feature", target })}
						/>
					</>
				)}
				{!drawing && unchanged && (
					<p className="lp-drawing-status" role="status">
						{__(
							"The boundary is unchanged. No project change was made.",
							"linker-tools",
						)}
					</p>
				)}
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
									{mapDrawingName(record.drawing)}
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
									onClick={() => begin({ kind: "restore", record })}
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
							{drawingStatus()}
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
											change(
												mapDrawingVertices(
													drawing,
													drawing.vertices.slice(0, -1),
												),
											)
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
									href={
										drawing.schema_version === 1
											? "#lp-map-roof-properties"
											: drawing.schema_version === 3
												? "#lp-map-feature-properties"
												: "#lp-map-ring-properties"
									}
								>
									{drawing.schema_version === 1
										? __("Roof properties", "linker-tools")
										: drawing.schema_version === 3
											? __("Feature properties", "linker-tools")
											: __("Boundary properties", "linker-tools")}
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
			{active &&
				drawing &&
				drawing.phase === "staged" &&
				!stale &&
				(drawing.schema_version === 1 ? (
					<MapRoofProperties
						drawing={drawing}
						locale={locale}
						busy={busy}
						invalidField={invalidField}
						error={error}
						field={field}
						submit={() => void apply()}
						continueDrawing={() =>
							change({
								...drawing,
								phase: "collecting",
								prepared_geometry: null,
							})
						}
					/>
				) : drawing.schema_version === 3 ? (
					<MapFeatureProperties
						drawing={drawing}
						locale={locale}
						busy={busy}
						invalidField={invalidField}
						error={error}
						field={featureField}
						submit={() => void apply()}
						continueDrawing={() =>
							change({
								...drawing,
								phase: "collecting",
								fields: { ...drawing.fields, source_confirmed: false },
								prepared_geometry: null,
							})
						}
					/>
				) : (
					<MapRingProperties
						drawing={drawing}
						locale={locale}
						busy={busy}
						invalidField={invalidField}
						error={error}
						confirm={(confirmed) =>
							change({
								...drawing,
								source_confirmed: confirmed,
								prepared_geometry: null,
							})
						}
						submit={() => void apply()}
					/>
				))}
		</div>
	);
}
