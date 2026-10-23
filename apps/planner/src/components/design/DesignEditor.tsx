import {
	lazy,
	Suspense,
	useCallback,
	useEffect,
	useMemo,
	useState,
} from "react";
import type { GeometryDocument } from "../../domain/geometry.ts";
import type { GeometryCommand } from "../../domain/geometryCommands.ts";
import { roofDependents } from "../../domain/geometryCommands.ts";
import { moduleSummary, panelPoses } from "../../domain/panelPoses.ts";
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
import { CoordinatesForm } from "./CoordinatesForm.tsx";

const SceneViewport = lazy(() => import("./SceneViewport.tsx"));
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
	commit,
	locale,
	projectId,
	session,
	client,
	recheck,
	onValidity,
}: {
	geometry: GeometryDocument;
	commit: (command: GeometryCommand) => boolean;
	locale: string;
	projectId: string;
	session: Session;
	client: PlannerClient;
	recheck: () => void;
	onValidity: (valid: boolean) => void;
}) {
	const [selected, setSelected] = useState<string | null>(null),
		[roofId, setRoofId] = useState<string | null>(
			geometry.roofs[0]?.id ?? null,
		),
		[view, setView] = useState<"plan" | "3d">("plan");
	const [form, setForm] = useState<FormState | null>(null),
		[error, setError] = useState(false),
		[page, setPage] = useState(0);
	const poses = useMemo(() => panelPoses(geometry), [geometry]),
		summary = useMemo(() => moduleSummary(geometry), [geometry]);
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
		setError(false);
	}, []);
	useEffect(() => {
		onValidity(form === null);
		return () => onValidity(true);
	}, [form, onValidity]);
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
		if (form) return;
		if (id === "coordinate_system") {
			open("coordinates");
			return;
		}
		setSelected(id);
		const pose = poses.find((pose) => pose.id === id),
			object = [
				...geometry.roofs,
				...geometry.arrays,
				...geometry.obstacles,
				...geometry.keepouts,
			].find((object) => object.id === id);
		if (pose) setRoofId(pose.roof_id);
		else if (object)
			setRoofId("roof_id" in object ? object.roof_id : object.id);
	}
	function open(
		kind: FormKind,
		id: string | null = null,
		forRoof: string | null = roof?.id ?? null,
	) {
		if (form) return;
		setError(false);
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
			className="lp-section lp-design-section"
			id="lp-design"
			tabIndex={-1}
			aria-labelledby="lp-design-heading"
		>
			<div className="lp-section-heading">
				<span className="lp-index">06</span>
				<div>
					<h2 id="lp-design-heading">{__("Roof design", "linker-tools")}</h2>
					<p>
						{__(
							"Measured roof faces and module specifications produce an editable layout and a traceable plan check. The roof step is optional for every project type.",
							"linker-tools",
						)}
					</p>
				</div>
			</div>
			<div className="lp-design-toolbar">
				<div className="lp-inline-actions">
					<button
						type="button"
						className="lp-button"
						disabled={!!form}
						onClick={() => open("roof")}
					>
						<Icon name="plus" />
						{__("Add roof face", "linker-tools")}
					</button>
					<button
						type="button"
						className="lp-button lp-button-secondary"
						disabled={!!form}
						onClick={() => open("module")}
					>
						{__("Add module specification", "linker-tools")}
					</button>
				</div>
				<div
					className="lp-view-switch"
					role="group"
					aria-label={__("Design view", "linker-tools")}
				>
					<button
						type="button"
						aria-pressed={view === "plan"}
						onClick={() => setView("plan")}
					>
						{__("Plan", "linker-tools")}
					</button>
					<button
						type="button"
						aria-pressed={view === "3d"}
						onClick={() => setView("3d")}
					>
						3D
					</button>
				</div>
			</div>
			{error && (
				<Notice error>
					{__(
						"The edit could not be applied. An object may have changed, a reference may still be in use, or the values may exceed the design contract. The current design has been preserved.",
						"linker-tools",
					)}
				</Notice>
			)}
			<div className="lp-design-workspace">
				<div className="lp-design-canvas">
					{roof ? (
						<>
							<div className="lp-roof-picker">
								<label>
									{__("Active roof face", "linker-tools")}
									<select
										value={roof.id}
										disabled={!!form}
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
								<span className="lp-eyebrow">
									{geometry.coordinate_system.north_reference === "unreferenced"
										? __("North unreferenced", "linker-tools")
										: __("North reference recorded", "linker-tools")}
								</span>
							</div>
							{view === "plan" ? (
								<PlanViewport
									key={roof.id}
									document={geometry}
									roof={roof}
									poses={poses}
									selected={selected}
									select={choose}
									commit={edit}
									disabled={!!form}
								/>
							) : (
								<Suspense
									fallback={
										<p role="status">
											{__("Loading 3D workspace…", "linker-tools")}
										</p>
									}
								>
									<SceneViewport
										document={geometry}
										poses={poses}
										selected={selected}
										select={choose}
										commit={edit}
										disabled={!!form}
									/>
								</Suspense>
							)}
						</>
					) : (
						<div className="lp-design-empty">
							<Icon name="layers" width={42} height={42} />
							<h3>
								{__(
									"The roof layout starts with measured geometry",
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
								className="lp-text-button"
								disabled={!!form}
								onClick={() => open("roof")}
							>
								{__("Add the first roof face", "linker-tools")}
								<Icon name="arrow" />
							</button>
						</div>
					)}
					<dl className="lp-design-quantities">
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
					className="lp-design-properties"
					aria-label={__("Design objects and properties", "linker-tools")}
				>
					{form ? (
						<>
							{form.kind === "roof" && (
								<RoofForm {...formProps} roof={formRoof} />
							)}
							{form.kind === "coordinates" && (
								<CoordinatesForm {...formProps} />
							)}
							{form.kind === "array" && form.roofId && (
								<ArrayForm
									{...formProps}
									array={formArray}
									roofId={form.roofId}
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
												"Removing %1$s also removes %2$d dependent arrays, obstacles and keep-out areas from this draft. Undo restores this edit.",
												"linker-tools",
											),
											formRoof.name,
											roofDependents(model!, formRoof.id).length,
										)}
									</p>
									<div className="lp-inline-actions">
										<button
											type="button"
											className="lp-button"
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
											className="lp-text-button"
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
								className="lp-object-tree"
								role="group"
								aria-label={__("Select a design object", "linker-tools")}
							>
								{geometry.roofs.map((face) => (
									<div key={face.id} className="lp-object-branch">
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
													className="lp-object-child"
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
										{module.model}
									</button>
								))}
							</div>
							{roof && (
								<div className="lp-object-actions">
									<button
										type="button"
										className="lp-text-button"
										disabled={!geometry.module_specs.length}
										onClick={() => open("array")}
									>
										{__("Add module array", "linker-tools")}
										<Icon name="plus" />
									</button>
									<button
										type="button"
										className="lp-text-button"
										onClick={() => open("obstacle")}
									>
										{__("Add obstacle", "linker-tools")}
										<Icon name="plus" />
									</button>
									<button
										type="button"
										className="lp-text-button"
										onClick={() => open("keepout")}
									>
										{__("Add keep-out area", "linker-tools")}
										<Icon name="plus" />
									</button>
									<button
										type="button"
										className="lp-text-button"
										onClick={() => open("rules")}
									>
										{__("Layout clearances", "linker-tools")}
									</button>
									{!geometry.module_specs.length && (
										<p className="lp-profile-help">
											{__(
												"A module specification is needed before an array can be placed.",
												"linker-tools",
											)}
										</p>
									)}
								</div>
							)}
							{(object || module || source || array) && (
								<div className="lp-object-inspector">
									<h3>
										{object?.name ??
											module?.model ??
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
											className="lp-button lp-button-secondary"
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
									<div className="lp-inline-actions">
										<button
											type="button"
											className="lp-text-button"
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
												className="lp-text-button"
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
											className="lp-text-button"
											onClick={() => open("source", object.source_id)}
										>
											{__("Source properties", "linker-tools")}
										</button>
									)}
								</div>
							)}
							<button
								type="button"
								className="lp-text-button"
								disabled={!geometry.sources.length}
								onClick={() => open("coordinates")}
							>
								{__("Coordinate references", "linker-tools")}
							</button>
							<details className="lp-comparison">
								<summary>{__("Sources", "linker-tools")}</summary>
								{geometry.sources.map((source) => (
									<button
										type="button"
										className="lp-text-button"
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
				<details className="lp-comparison lp-module-table">
					<summary>
						{sprintf(__("Module slots in %s", "linker-tools"), array.name)}
					</summary>
					<div className="lp-table-scroll">
						<table className="lp-data-table">
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
													className="lp-text-button"
													onClick={() => choose(pose.id)}
												>
													{__("Select module", "linker-tools")}
												</button>
												<button
													type="button"
													className="lp-text-button"
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
					<div className="lp-inline-actions">
						<button
							type="button"
							className="lp-text-button"
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
							className="lp-text-button"
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
				disabled={!!form}
			/>
		</section>
	);
}
