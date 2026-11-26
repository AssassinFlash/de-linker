import { panelLabel } from "../../domain/panelParameters.ts";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type {
	GeometryDocument,
	PanelArray,
	Vec2,
} from "../../domain/geometry.ts";
import type {
	PreparedGeometryImport,
	GeometryImportSelections,
} from "../../domain/geometryImports.ts";
import type { PlaceImagery } from "../../domain/place.ts";
import type { GeometryCommand } from "../../domain/geometryCommands.ts";
import {
	applyGeometryCommand,
	roofDependents,
} from "../../domain/geometryCommands.ts";
import type { ArrayPlacement } from "../../data/mapInteraction.ts";
import { revealActionResult } from "../revealActionResult.ts";
import { moduleSummary, panelPoses } from "../../domain/panelPoses.ts";
import { selectedRoofId } from "../../domain/geometrySelection.ts";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import type { Session } from "../../data/protocol.ts";
import { __, sprintf } from "../../i18n.ts";
import { formatDecimal } from "../../domain/decimal.ts";
import { Icon } from "../Icon.tsx";
import { Notice } from "../Notice.tsx";
import { RoofForm } from "./RoofForm.tsx";
import { ArrayForm } from "./ArrayForm.tsx";
import { ModuleForm } from "./ModuleForm.tsx";
import { ShapeForm } from "./ShapeForm.tsx";
import { SourceForm } from "./SourceForm.tsx";
import { LayoutRulesForm } from "./LayoutRulesForm.tsx";
import { LayoutReviewPanel } from "./LayoutReviewPanel.tsx";
import { PlanViewport } from "./PlanViewport.tsx";
import { GeometryIntake } from "./GeometryIntake.tsx";
import { ImageCalibrationWorkspace } from "./ImageCalibrationWorkspace.tsx";
import { CoordinatesForm } from "./CoordinatesForm.tsx";
import { LazySceneViewport } from "./LazySceneViewport.tsx";
import { MapDrawingWorkspace } from "./MapDrawingWorkspace.tsx";
import type { MapCamera } from "./MapViewport.tsx";
import type { SceneViewState } from "../../domain/sceneCamera.ts";

type FormKind =
	| "roof"
	| "array"
	| "module"
	| "obstacle"
	| "keepout"
	| "source"
	| "rules"
	| "coordinates"
	| "delete_roof";
interface FormState {
	kind: FormKind;
	id: string | null;
	roofId: string | null;
	snapshot: GeometryDocument;
}

export function DesignEditor({
	geometry,
	confirmedGeometry = null,
	geometryImports = { schema_version: 1, selected: {} },
	sceneModuleUrl = null,
	mapModuleUrl = null,
	mapStyleUrl = null,
	googleMapsApiKey = null,
	initialMapView = false,
	commit,
	locale,
	projectId,
	session,
	client,
	recheck,
	imagery = null,
	siteCentre = null,
	siteOutline = null,
	onValidity,
	attachImport,
	confirmedAssetIds = [],
	recoveryScopes,
	recoveryChecking,
}: {
	geometry: GeometryDocument;
	confirmedGeometry?: GeometryDocument | null;
	geometryImports?: GeometryImportSelections;
	imagery?: PlaceImagery | null;
	siteCentre?: readonly [number, number] | null;
	siteOutline?: {
		ring: [number, number][];
		source: string;
		licence: string;
		planes?: readonly {
			id: number;
			polygon: readonly [number, number][];
			tilt_deg: number;
			azimuth_deg: number;
			area_m2: number;
		}[];
	} | null;
	sceneModuleUrl?: string | null;
	mapModuleUrl?: string | null;
	mapStyleUrl?: string | null;
	googleMapsApiKey?: string | null;
	initialMapView?: boolean;
	commit: (command: GeometryCommand) => boolean;
	locale: string;
	projectId: string;
	session: Session;
	client: PlannerClient;
	recheck: () => void;
	onValidity: (valid: boolean) => void;
	attachImport: (
		before: GeometryDocument,
		asset: PreparedGeometryImport,
	) => boolean;
	confirmedAssetIds?: readonly string[];
	recoveryScopes?: readonly string[] | undefined;
	recoveryChecking?: boolean | undefined;
}) {
	const canShowGoogle3D = Boolean(
		googleMapsApiKey &&
		(siteCentre !== null ||
			(geometry.coordinate_system.anchor !== null &&
				geometry.coordinate_system.north_reference === "true_north")),
	);
	const canShowMap = Boolean(
		siteCentre !== null ||
		imagery !== null ||
		siteOutline !== null ||
		(geometry.coordinate_system.anchor !== null &&
			geometry.coordinate_system.north_reference === "true_north"),
	);
	const userPickedView = useRef(initialMapView);
	const [selected, setSelected] = useState<string | null>(null),
		[roofId, setRoofId] = useState<string | null>(
			geometry.roofs[0]?.id ?? null,
		),
		[view, setView] = useState<"plan" | "map" | "3d">(() =>
			initialMapView || canShowMap ? "map" : "plan",
		);
	useEffect(() => {
		if (userPickedView.current || view !== "plan") return;
		if (canShowMap) setView("map");
	}, [canShowMap, view]);
	const mapCamera = useRef<MapCamera | null>(null);
	const sceneCamera = useRef<SceneViewState | null>(null);
	const [importOpen, setImportOpen] = useState(false);
	const [drawingOpen, setDrawingOpen] = useState(false);
	const [calibrationOpen, setCalibrationOpen] = useState(false);
	const [form, setForm] = useState<FormState | null>(null),
		[error, setError] = useState(false),
		[page, setPage] = useState(0);
	const [arrayPosition, setArrayPosition] = useState<Vec2 | null>(null);
	const [arrayPreview, setArrayPreview] = useState<PanelArray | null>(null);
	const displayGeometry = useMemo(() => {
		if (form?.kind !== "array" || !arrayPreview) return geometry;
		return applyGeometryCommand(form.snapshot, {
			type: "put_array",
			before:
				form.snapshot.arrays.find((array) => array.id === form.id) ?? null,
			value: arrayPreview,
		});
	}, [arrayPreview, form, geometry]);
	const displayPoses = useMemo(
		() => panelPoses(displayGeometry),
		[displayGeometry],
	);
	const placement = useMemo<ArrayPlacement | null>(
		() =>
			form?.kind === "array" && form.roofId
				? {
						roofId: form.roofId,
						place: setArrayPosition,
						review: () =>
							revealActionResult(
								document.querySelector<HTMLElement>(
									"#sc-array-properties input, #sc-array-properties select",
								),
							),
					}
				: null,
		[form],
	);
	const poses = useMemo(() => panelPoses(geometry), [geometry]),
		summary = useMemo(() => moduleSummary(displayGeometry), [displayGeometry]);
	const roof =
		geometry.roofs.find((roof) => roof.id === roofId) ??
		geometry.roofs[0] ??
		null;
	const panel = poses.find((pose) => pose.id === selected);
	const array = geometry.arrays.find(
		(array) => array.id === (panel?.array_id ?? selected),
	);
	const object = [
		...geometry.roofs,
		...geometry.arrays,
		...geometry.obstacles,
		...geometry.keepouts,
	].find((item) => item.id === selected);
	const source = geometry.sources.find((source) => source.id === selected);
	const module = geometry.module_specs.find((module) => module.id === selected);
	const closeForm = useCallback(() => {
		setForm(null);
		setArrayPreview(null);
		setArrayPosition(null);
		setError(false);
	}, []);
	useEffect(() => {
		onValidity(
			form === null && !importOpen && !drawingOpen && !calibrationOpen,
		);
		return () => onValidity(true);
	}, [form, importOpen, drawingOpen, calibrationOpen, onValidity]);
	const edit = useCallback(
		(command: GeometryCommand) => {
			const accepted = commit(command);
			setError(!accepted);
			if (accepted) {
				const edits = command.type === "group" ? command.edits : [command];
				for (const edit of edits) {
					if (edit.type === "put_roof") {
						setRoofId(edit.value.id);
						setSelected(edit.value.id);
					} else if (edit.type === "put_array") {
						setRoofId(edit.value.roof_id);
						setSelected(edit.value.id);
					} else if (
						edit.type === "put_module" ||
						edit.type === "put_obstacle" ||
						edit.type === "put_keepout"
					)
						setSelected(edit.value.id);
				}
			}
			return accepted;
		},
		[commit],
	);
	useEffect(() => {
		setPage(0);
	}, [array?.id]);
	function choose(id: string) {
		if (form || importOpen || drawingOpen) return;
		if (id === "coordinate_system") {
			open("coordinates");
			return;
		}
		setSelected(id);
		const selectedRoof = selectedRoofId(geometry, id, poses);
		if (selectedRoof !== null) setRoofId(selectedRoof);
	}
	function open(
		kind: FormKind,
		id: string | null = null,
		forRoof: string | null = roof?.id ?? null,
	) {
		if (form || importOpen || drawingOpen) return;
		setError(false);
		if (kind === "array") {
			setArrayPreview(null);
			setArrayPosition(
				geometry.arrays.find((array) => array.id === id)?.origin_uv ?? null,
			);
			if (
				!geometry.coordinate_system.anchor ||
				geometry.coordinate_system.north_reference !== "true_north"
			) {
				userPickedView.current = true;
				setView("plan");
			} else if (view === "3d") setView("map");
		}
		setForm({ kind, id, roofId: forRoof, snapshot: geometry });
	}
	const formProps = {
		document: form?.snapshot ?? geometry,
		locale,
		commit: edit,
		cancel: closeForm,
		onValidity,
	};
	const model = form?.snapshot;
	const formRoof = model?.roofs.find((roof) => roof.id === form?.id) ?? null;
	const formArray =
		model?.arrays.find((array) => array.id === form?.id) ?? null;
	const slotPoses = array
		? poses.filter((pose) => pose.array_id === array.id)
		: [];
	// Table pagination is an interface resource policy, not a calculation limit.
	const pageSize = 40,
		totalPages = Math.max(1, Math.ceil(slotPoses.length / pageSize)),
		currentPage = Math.min(page, totalPages - 1);
	return (
		<section
			className="sc-section sc-design-section"
			id="sc-solar"
			tabIndex={-1}
			aria-labelledby="sc-design-heading"
		>
			<div className="sc-section-heading">
				<span className="sc-index">06</span>
				<div>
					<h2 id="sc-design-heading">{__("Roof design", "linker-tools")}</h2>
					<p>
						{__(
							"Draw your roof on the aerial map, then place your panels.",
							"linker-tools",
						)}
					</p>
				</div>
			</div>
			<div className="sc-design-toolbar">
				<div className="sc-actions">
					{roof && (
						<button
							type="button"
							className="sc-button"
							disabled={!!form || importOpen || drawingOpen}
							onClick={() => open("module")}
						>
							{__("Add module specification", "linker-tools")}
						</button>
					)}
				</div>
				<div
					className="sc-view-switch"
					role="group"
					aria-label={__("Design view", "linker-tools")}
				>
					<button
						type="button"
						aria-pressed={view === "3d"}
						disabled={drawingOpen || form?.kind === "array"}
						onClick={() => {
							userPickedView.current = true;
							setView("3d");
						}}
					>
						3D
					</button>
					<button
						type="button"
						aria-pressed={view === "map"}
						disabled={
							drawingOpen ||
							(form?.kind === "array" &&
								(!geometry.coordinate_system.anchor ||
									geometry.coordinate_system.north_reference !== "true_north"))
						}
						onClick={() => {
							userPickedView.current = true;
							setView("map");
						}}
					>
						{__("Map", "linker-tools")}
					</button>
					<button
						type="button"
						aria-pressed={view === "plan"}
						disabled={drawingOpen}
						onClick={() => {
							userPickedView.current = true;
							setView("plan");
						}}
					>
						{__("Plan", "linker-tools")}
					</button>
				</div>
			</div>
			{error && (
				<Notice error>
					{__(
						"This edit could not be applied. Some values or references may be invalid or may have changed. The current design is unchanged.",
						"linker-tools",
					)}
				</Notice>
			)}
			<details className="sc-design-imports">
				<summary>
					{__("Use measurements or import a roof plan", "linker-tools")}
				</summary>
				<button
					type="button"
					className="sc-button"
					disabled={!!form || importOpen || drawingOpen}
					onClick={() => open("roof")}
				>
					<Icon name="plus" />
					{__("Add roof face", "linker-tools")}
				</button>
				<GeometryIntake
					geometry={geometry}
					projectId={projectId}
					session={session}
					client={client}
					locale={locale}
					recheck={recheck}
					disabled={!!form || drawingOpen}
					onActivity={setImportOpen}
					attach={(before, asset) => {
						if (!attachImport(before, asset)) return false;
						const added = asset.geometry.roofs[0]!;
						setRoofId(added.id);
						setSelected(added.id);
						return true;
					}}
					currentAssetIds={Object.values(geometryImports.selected)}
					confirmedAssetIds={confirmedAssetIds}
					recoveryScopes={recoveryScopes}
					recoveryChecking={recoveryChecking}
				/>
				<ImageCalibrationWorkspace
					geometry={geometry}
					roofId={roof?.id ?? null}
					locale={locale}
					disabled={!!form || drawingOpen || importOpen}
					onActivity={setCalibrationOpen}
					commit={edit}
				/>
			</details>
			<div className="sc-design-workspace">
				<div className="sc-design-canvas" id="sc-array-canvas" tabIndex={-1}>
					{view === "map" ? (
						<MapDrawingWorkspace
							imagery={imagery}
							siteCentre={siteCentre}
							siteOutline={siteOutline}
							mapModuleUrl={mapModuleUrl}
							mapStyleUrl={mapStyleUrl}
							geometry={geometry}
							previewGeometry={displayGeometry}
							placement={placement}
							confirmedGeometry={confirmedGeometry}
							projectId={projectId}
							locale={locale}
							session={session}
							client={client}
							recheck={recheck}
							recoveryScopes={recoveryScopes}
							recoveryChecking={recoveryChecking}
							commit={edit}
							onActivity={setDrawingOpen}
							poses={displayPoses}
							selected={arrayPreview?.id ?? selected}
							select={choose}
							disabled={!!form || importOpen}
							openReferences={() => open("coordinates")}
							camera={mapCamera}
						/>
					) : view === "3d" && (roof || canShowGoogle3D) ? (
						<>
							{roof && (
								<div className="sc-roof-picker">
									<label>
										{__("Active roof face", "linker-tools")}
										<select
											value={roof.id}
											disabled={!!form || importOpen || drawingOpen}
											onChange={(event) => {
												setRoofId(event.currentTarget.value);
												setSelected(event.currentTarget.value);
											}}
										>
											{geometry.roofs.map((roof) => (
												<option key={roof.id} value={roof.id}>
													{roof.name}
												</option>
											))}
										</select>
									</label>
									<span className="sc-eyebrow">
										{geometry.coordinate_system.north_reference ===
										"unreferenced"
											? __("North unreferenced", "linker-tools")
											: __("North reference recorded", "linker-tools")}
									</span>
								</div>
							)}
							<LazySceneViewport
								sceneModuleUrl={sceneModuleUrl}
								document={geometry}
								poses={poses}
								selected={selected}
								select={choose}
								commit={edit}
								disabled={!!form || importOpen || drawingOpen}
								camera={sceneCamera}
								googleMapsApiKey={googleMapsApiKey}
								siteCentre={siteCentre}
								siteOutline={siteOutline}
								onSwitchToMap={() => {
									userPickedView.current = true;
									setView("map");
								}}
							/>
						</>
					) : roof ? (
						<>
							<div className="sc-roof-picker">
								<label>
									{__("Active roof face", "linker-tools")}
									<select
										value={roof.id}
										disabled={!!form || importOpen || drawingOpen}
										onChange={(event) => {
											setRoofId(event.currentTarget.value);
											setSelected(event.currentTarget.value);
										}}
									>
										{geometry.roofs.map((roof) => (
											<option key={roof.id} value={roof.id}>
												{roof.name}
											</option>
										))}
									</select>
								</label>
								<span className="sc-eyebrow">
									{geometry.coordinate_system.north_reference === "unreferenced"
										? __("North unreferenced", "linker-tools")
										: __("North reference recorded", "linker-tools")}
								</span>
							</div>
							<PlanViewport
								key={roof.id}
								document={displayGeometry}
								roof={roof}
								poses={displayPoses}
								selected={arrayPreview?.id ?? selected}
								placement={placement}
								locale={locale}
								select={choose}
								commit={edit}
								disabled={
									(!!form && form.kind !== "array") || importOpen || drawingOpen
								}
							/>
						</>
					) : (
						<div className="sc-design-empty">
							<Icon name="layers" width={42} height={42} />
							<h3>
								{__(
									"The roof layout starts with roof geometry",
									"linker-tools",
								)}
							</h3>
							<p>
								{__(
									"A roof face needs surface dimensions, pitch, orientation and a measurement reference. Module dimensions and mounting parameters then determine the layout. Missing dimensions are left empty.",
									"linker-tools",
								)}
							</p>
							<button
								type="button"
								className="sc-text-button"
								disabled={!!form || importOpen || drawingOpen}
								onClick={() => open("roof")}
							>
								{__("Add the first roof face", "linker-tools")}
								<Icon name="arrow" />
							</button>
						</div>
					)}
					<dl className="sc-design-quantities">
						<div>
							<dt>{__("Included modules", "linker-tools")}</dt>
							<dd>{summary.count}</dd>
						</div>
						<div>
							<dt>{__("Declared DC nameplate power", "linker-tools")}</dt>
							<dd>
								{formatDecimal(summary.stc_kwp, locale)} <small>kWp</small>
							</dd>
						</div>
						<div>
							<dt>{__("Roof faces", "linker-tools")}</dt>
							<dd>{geometry.roofs.length}</dd>
						</div>
					</dl>
				</div>
				<aside
					className="sc-design-properties"
					inert={drawingOpen}
					aria-label={__("Design objects and properties", "linker-tools")}
				>
					{form ? (
						<>
							{form.kind === "roof" && (
								<RoofForm
									{...formProps}
									roof={formRoof}
									imported={
										formRoof !== null &&
										Object.hasOwn(geometryImports.selected, formRoof.source_id)
									}
								/>
							)}
							{form.kind === "coordinates" && (
								<CoordinatesForm {...formProps} />
							)}
							{form.kind === "array" && form.roofId && (
								<ArrayForm
									{...formProps}
									array={formArray}
									roofId={form.roofId}
									position={arrayPosition}
									preview={setArrayPreview}
									choosePosition={() =>
										revealActionResult(
											globalThis.document.getElementById("sc-array-canvas"),
										)
									}
								/>
							)}
							{form.kind === "module" && (
								<ModuleForm
									{...formProps}
									module={
										model?.module_specs.find(
											(module) => module.id === form.id,
										) ?? null
									}
								/>
							)}
							{(form.kind === "obstacle" || form.kind === "keepout") &&
								form.roofId && (
									<ShapeForm
										{...formProps}
										kind={form.kind}
										roofId={form.roofId}
										object={
											[...model!.obstacles, ...model!.keepouts].find(
												(object) => object.id === form.id,
											) ?? null
										}
									/>
								)}
							{form.kind === "source" && (
								<SourceForm
									{...formProps}
									referenceLocked={
										form.id !== null &&
										Object.hasOwn(geometryImports.selected, form.id)
									}
									source={model!.sources.find(
										(source) => source.id === form.id,
									)!}
								/>
							)}
							{form.kind === "rules" && form.roofId && (
								<LayoutRulesForm {...formProps} roofId={form.roofId} />
							)}
							{form.kind === "delete_roof" && formRoof && (
								<div>
									<h3>{__("Remove this roof face?", "linker-tools")}</h3>
									<p>
										{sprintf(
											__(
												"Removing %1$s also removes %2$d dependent arrays, obstacles and keep-out areas, together with this roof face's clearance settings. Undo restores this edit.",
												"linker-tools",
											),
											formRoof.name,
											roofDependents(model!, formRoof.id).length,
										)}
									</p>
									<div className="sc-actions">
										<button
											type="button"
											className="sc-button sc-primary"
											onClick={() => {
												if (
													edit({
														type: "delete_roof",
														id: formRoof.id,
														expected_dependents: roofDependents(
															model!,
															formRoof.id,
														),
													})
												)
													closeForm();
											}}
										>
											{__("Remove roof and dependent objects", "linker-tools")}
										</button>
										<button
											type="button"
											className="sc-text-button"
											onClick={closeForm}
										>
											{__("Cancel", "linker-tools")}
										</button>
									</div>
								</div>
							)}
						</>
					) : (
						<>
							<h3>{__("Design objects", "linker-tools")}</h3>
							<div
								className="sc-object-tree"
								role="group"
								aria-label={__("Select a design object", "linker-tools")}
							>
								{geometry.roofs.map((face) => (
									<div key={face.id} className="sc-object-branch">
										<button
											type="button"
											aria-pressed={selected === face.id}
											onClick={() => choose(face.id)}
										>
											<Icon name="layers" />
											{face.name}
										</button>
										{[
											...geometry.arrays,
											...geometry.obstacles,
											...geometry.keepouts,
										]
											.filter((object) => object.roof_id === face.id)
											.map((object) => (
												<button
													type="button"
													className="sc-object-child"
													key={object.id}
													aria-pressed={
														selected === object.id ||
														panel?.array_id === object.id
													}
													onClick={() => choose(object.id)}
												>
													{object.name}
												</button>
											))}
									</div>
								))}
								{geometry.module_specs.map((module) => (
									<button
										type="button"
										key={module.id}
										aria-pressed={selected === module.id}
										onClick={() => choose(module.id)}
									>
										{panelLabel(module, locale)}
									</button>
								))}
							</div>
							{roof && (
								<div className="sc-object-actions">
									<button
										type="button"
										className="sc-text-button"
										disabled={!geometry.module_specs.length}
										onClick={() => open("array")}
									>
										{__("Add module array", "linker-tools")}
										<Icon name="plus" />
									</button>
									<button
										type="button"
										className="sc-text-button"
										onClick={() => open("obstacle")}
									>
										{__("Add obstacle", "linker-tools")}
										<Icon name="plus" />
									</button>
									<button
										type="button"
										className="sc-text-button"
										onClick={() => open("keepout")}
									>
										{__("Add keep-out area", "linker-tools")}
										<Icon name="plus" />
									</button>
									<button
										type="button"
										className="sc-text-button"
										onClick={() => open("rules")}
									>
										{__("Layout clearances", "linker-tools")}
									</button>
									{!geometry.module_specs.length && (
										<p className="sc-field-help">
											{__(
												"A module specification is needed before an array can be placed.",
												"linker-tools",
											)}
										</p>
									)}
								</div>
							)}
							{(object || module || source || array) && (
								<div className="sc-object-inspector">
									<h3>
										{object?.name ??
											(module ? panelLabel(module, locale) : null) ??
											source?.note ??
											array?.name}
									</h3>
									{panel && (
										<p>
											{sprintf(
												__("Module row %1$d, column %2$d", "linker-tools"),
												panel.row + 1,
												panel.column + 1,
											)}{" "}
											·{" "}
											{panel.included
												? __("Included", "linker-tools")
												: __("Excluded", "linker-tools")}
										</p>
									)}
									{panel && (
										<button
											type="button"
											className="sc-button"
											onClick={() =>
												edit({
													type: "toggle_panel",
													array_id: panel.array_id,
													row: panel.row,
													column: panel.column,
												})
											}
										>
											{panel.included
												? __("Exclude module", "linker-tools")
												: __("Restore module", "linker-tools")}
										</button>
									)}
									<div className="sc-actions">
										<button
											type="button"
											className="sc-text-button"
											onClick={() => {
												if (array) open("array", array.id, array.roof_id);
												else if (module) open("module", module.id);
												else if (source) open("source", source.id);
												else if (object)
													open(
														"boundary_uv" in object
															? "roof"
															: "reason" in object
																? "keepout"
																: "obstacle",
														object.id,
														"roof_id" in object ? object.roof_id : object.id,
													);
											}}
										>
											{__("Edit numeric properties", "linker-tools")}
										</button>
										{object && (
											<button
												type="button"
												className="sc-text-button"
												onClick={() =>
													"boundary_uv" in object
														? open("delete_roof", object.id, object.id)
														: edit({ type: "delete_object", id: object.id })
												}
											>
												{__("Remove object", "linker-tools")}
											</button>
										)}
									</div>
									{object && (
										<button
											type="button"
											className="sc-text-button"
											onClick={() => open("source", object.source_id)}
										>
											{__("Source properties", "linker-tools")}
										</button>
									)}
								</div>
							)}
							<button
								type="button"
								className="sc-text-button"
								disabled={!geometry.sources.length}
								onClick={() => open("coordinates")}
							>
								{__("Coordinate references", "linker-tools")}
							</button>
							<details className="sc-disclosure">
								<summary>{__("Sources", "linker-tools")}</summary>
								{geometry.sources.map((source) => (
									<button
										type="button"
										className="sc-text-button"
										key={source.id}
										onClick={() => open("source", source.id)}
									>
										{source.note}
									</button>
								))}
							</details>
						</>
					)}
				</aside>
			</div>
			{array && !form && (
				<details className="sc-disclosure sc-module-table">
					<summary>
						{sprintf(__("Module slots in %s", "linker-tools"), array.name)}
					</summary>
					<div className="sc-table-scroll">
						<table className="sc-data-table">
							<thead>
								<tr>
									<th>{__("Row / column", "linker-tools")}</th>
									<th>{__("Status", "linker-tools")}</th>
									<th>{__("Actions", "linker-tools")}</th>
								</tr>
							</thead>
							<tbody>
								{slotPoses
									.slice(currentPage * pageSize, (currentPage + 1) * pageSize)
									.map((pose) => (
										<tr key={pose.id}>
											<td>
												{pose.row + 1} / {pose.column + 1}
											</td>
											<td>
												{pose.included
													? __("Included", "linker-tools")
													: __("Excluded", "linker-tools")}
											</td>
											<td>
												<button
													type="button"
													className="sc-text-button"
													onClick={() => choose(pose.id)}
												>
													{__("Select module", "linker-tools")}
												</button>
												<button
													type="button"
													className="sc-text-button"
													onClick={() =>
														edit({
															type: "toggle_panel",
															array_id: pose.array_id,
															row: pose.row,
															column: pose.column,
														})
													}
												>
													{pose.included
														? __("Exclude module", "linker-tools")
														: __("Restore module", "linker-tools")}
												</button>
											</td>
										</tr>
									))}
							</tbody>
						</table>
					</div>
					<div className="sc-actions">
						<button
							type="button"
							className="sc-text-button"
							disabled={currentPage === 0}
							onClick={() => setPage(currentPage - 1)}
						>
							{__("Previous", "linker-tools")}
						</button>
						<span>
							{sprintf(
								__("Page %1$d of %2$d", "linker-tools"),
								currentPage + 1,
								totalPages,
							)}
						</span>
						<button
							type="button"
							className="sc-text-button"
							disabled={currentPage + 1 >= totalPages}
							onClick={() => setPage(currentPage + 1)}
						>
							{__("Next", "linker-tools")}
						</button>
					</div>
				</details>
			)}
			<LayoutReviewPanel
				geometry={geometry}
				projectId={projectId}
				client={client}
				session={session}
				locale={locale}
				recheck={recheck}
				select={choose}
				disabled={!!form || importOpen || drawingOpen}
			/>
		</section>
	);
}
