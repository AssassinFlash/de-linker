import { panelLabel } from "../../domain/panelParameters.ts";
import { useCallback, useState } from "react";
import type { PanelArray, Vec2 } from "../../domain/geometry.ts";
import { applyGeometryCommand } from "../../domain/geometryCommands.ts";
import type { GeometryFormProps } from "./RoofForm.tsx";
import { GeometryForm, GeometryNumber, GeometryText } from "./GeometryForm.tsx";
import type { GeometryValues } from "./GeometryForm.tsx";
import { __, sprintf } from "../../i18n.ts";

export function ArrayForm({
	document,
	locale,
	commit,
	cancel,
	onValidity,
	array,
	roofId,
	position,
	preview,
	choosePosition,
}: GeometryFormProps & {
	array: PanelArray | null;
	roofId: string;
	position: Vec2 | null;
	preview: (array: PanelArray | null) => void;
	choosePosition: () => void;
}) {
	const roof = document.roofs.find((roof) => roof.id === roofId)!;
	const [id] = useState(
		() => array?.id ?? "array_" + crypto.randomUUID().replaceAll("-", ""),
	);
	const readArray = useCallback(
		(values: GeometryValues): PanelArray => {
			if (!position) throw new Error("array_position_required");
			const rows = values.metric("rows", { integer: true, positive: true });
			const columns = values.metric("columns", {
				integer: true,
				positive: true,
			});
			return {
				id,
				name: values.text("name"),
				roof_id: roofId,
				source_id: array?.source_id ?? roof.source_id,
				module_spec_id: values.text("module"),
				origin_uv: position,
				rotation_deg: values.metric("rotation"),
				mount_tilt_deg: values.metric("tilt", { min: 0, max: 90 }),
				lower_edge_clearance_m: values.metric("height", { min: 0 }),
				rows,
				columns,
				column_gap_m: values.metric("column_gap", { min: 0 }),
				row_gap_m: values.metric("row_gap", { min: 0 }),
				excluded_slots: (array?.excluded_slots ?? []).filter((slot) => {
					const [row, column] = slot.split(":").map(Number);
					return row! < rows && column! < columns;
				}),
				mounting_note: values.text("mounting"),
			};
		},
		[array, id, position, roof.source_id, roofId],
	);
	const showPreview = useCallback(
		(values: GeometryValues) => {
			try {
				const next = readArray(values);
				// Use the same schema and resource limits before rendering and applying.
				applyGeometryCommand(document, {
					type: "put_array",
					before: array,
					value: next,
				});
				preview(next);
			} catch {
				// Incomplete input remains in the form; no stale preview is shown as current.
				preview(null);
			}
		},
		[array, document, preview, readArray],
	);
	// A new layout starts with one panel on the roof surface. These editable
	// zero offsets describe the preview, not a specified mounting system.
	return (
		<GeometryForm
			id="sc-array-properties"
			title={
				array
					? __("Array properties", "linker-tools")
					: __("Add a module array", "linker-tools")
			}
			locale={locale}
			cancel={cancel}
			onValidity={onValidity}
			onValuesChange={showPreview}
			measurementHelp={false}
			submitDisabled={!position}
			submit={(values) =>
				commit({ type: "put_array", before: array, value: readArray(values) })
			}
		>
			<p className="sc-field-help">{roof.name}</p>
			<label className="sc-field">
				<span>{__("Module specification", "linker-tools")}</span>
				<select
					name="module"
					required
					defaultValue={
						array?.module_spec_id ?? document.module_specs[0]?.id ?? ""
					}
				>
					{document.module_specs.map((module) => (
						<option key={module.id} value={module.id}>
							{panelLabel(module, locale)}
						</option>
					))}
				</select>
			</label>
			<div className="sc-geometry-fields">
				<GeometryNumber
					locale={locale}
					name="rows"
					label={__("Rows", "linker-tools")}
					value={array?.rows ?? 1}
					unit=""
				/>
				<GeometryNumber
					locale={locale}
					name="columns"
					label={__("Columns", "linker-tools")}
					value={array?.columns ?? 1}
					unit=""
				/>
			</div>
			<p className="sc-field-help" role="status">
				{position
					? __(
							"Preview the panels on your roof. Click another position to move them before applying.",
							"linker-tools",
						)
					: __(
							"Choose where the first panel starts on your roof.",
							"linker-tools",
						)}
			</p>
			<button
				type="button"
				className="sc-button"
				onClick={choosePosition}
			>
				{position
					? __("Change position on roof", "linker-tools")
					: __("Choose position on roof", "linker-tools")}
			</button>
			<details className="sc-array-settings">
				<summary>{__("Layout and mounting settings", "linker-tools")}</summary>
				<p className="sc-field-help">
					{__(
						"The initial layout follows the roof with no extra spacing or mounting height. Adjust these values for your layout.",
						"linker-tools",
					)}
				</p>
				<GeometryText
					name="name"
					label={__("Array name", "linker-tools")}
					value={
						array?.name ??
						sprintf(
							__("Panel array %d", "linker-tools"),
							document.arrays.length + 1,
						)
					}
				/>
				<div className="sc-geometry-fields">
					<GeometryNumber
						locale={locale}
						name="rotation"
						label={__("Panel rotation", "linker-tools")}
						value={array?.rotation_deg ?? 0}
						unit="°"
					/>
					<GeometryNumber
						locale={locale}
						name="tilt"
						label={__("Tilt above the roof", "linker-tools")}
						value={array?.mount_tilt_deg ?? 0}
						unit="°"
					/>
					<GeometryNumber
						locale={locale}
						name="column_gap"
						label={__("Gap between columns", "linker-tools")}
						value={array?.column_gap_m ?? 0}
					/>
					<GeometryNumber
						locale={locale}
						name="row_gap"
						label={__("Gap between rows", "linker-tools")}
						value={array?.row_gap_m ?? 0}
					/>
					<GeometryNumber
						locale={locale}
						name="height"
						label={__("Height above the roof", "linker-tools")}
						value={array?.lower_edge_clearance_m ?? 0}
					/>
				</div>
				<GeometryText
					name="mounting"
					label={__("Mounting notes", "linker-tools")}
					value={
						array?.mounting_note ??
						__("Mounting not specified.", "linker-tools")
					}
					multiline
				/>
			</details>
		</GeometryForm>
	);
}
