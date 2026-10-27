import type { PanelArray } from "../../domain/geometry.ts";
import type { GeometryFormProps } from "./RoofForm.tsx";
import { GeometryForm, GeometryNumber, GeometryText } from "./GeometryForm.tsx";
import { __ } from "../../i18n.ts";

export function ArrayForm({
	document,
	locale,
	commit,
	cancel,
	onValidity,
	array,
	roofId,
}: GeometryFormProps & { array: PanelArray | null; roofId: string }) {
	const roof = document.roofs.find((roof) => roof.id === roofId)!;
	return (
		<GeometryForm
			title={
				array
					? __("Array properties", "linker-tools")
					: __("Add a module array", "linker-tools")
			}
			locale={locale}
			cancel={cancel}
			onValidity={onValidity}
			submit={(values) => {
				const rows = values.metric("rows", { integer: true, positive: true }),
					columns = values.metric("columns", { integer: true, positive: true });
				const next: PanelArray = {
					id: array?.id ?? "array_" + crypto.randomUUID().replaceAll("-", ""),
					name: values.text("name"),
					roof_id: roofId,
					source_id: values.text("source"),
					module_spec_id: values.text("module"),
					origin_uv: [values.metric("u"), values.metric("v")],
					rotation_deg: values.metric("rotation"),
					mount_tilt_deg: values.metric("tilt", { min: 0, max: 90 }),
					lower_edge_clearance_m: values.metric("height", { min: 0 }),
					rows,
					columns,
					column_gap_m: values.metric("column_gap", { min: 0 }),
					row_gap_m: values.metric("row_gap", { min: 0 }),
					excluded_slots: array?.excluded_slots ?? [],
					mounting_note: values.text("mounting"),
				};
				// Removing rows/columns with excluded slots needs an explicit slot restore first.
				// The shared validator refuses an out-of-bounds slot instead of silently deleting it.
				return commit({ type: "put_array", before: array, value: next });
			}}
		>
			<p className="lp-profile-help">{roof.name}</p>
			<GeometryText
				name="name"
				label={__("Array name", "linker-tools")}
				value={array?.name ?? ""}
			/>
			<label className="lp-field">
				<span>{__("Module specification", "linker-tools")}</span>
				<select
					name="module"
					required
					defaultValue={array?.module_spec_id ?? ""}
				>
					<option value="">
						{__("Select a module specification", "linker-tools")}
					</option>
					{document.module_specs.map((module) => (
						<option key={module.id} value={module.id}>
							{module.model}
						</option>
					))}
				</select>
			</label>
			<label className="lp-field">
				<span>{__("Layout source", "linker-tools")}</span>
				<select
					name="source"
					required
					defaultValue={array?.source_id ?? roof.source_id}
				>
					{document.sources.map((source) => (
						<option key={source.id} value={source.id}>
							{source.note}
						</option>
					))}
				</select>
			</label>
			<div className="lp-geometry-fields">
				<GeometryNumber
					locale={locale}
					name="u"
					label={__("Anchor U", "linker-tools")}
					value={array?.origin_uv[0]}
				/>
				<GeometryNumber
					locale={locale}
					name="v"
					label={__("Anchor V", "linker-tools")}
					value={array?.origin_uv[1]}
				/>
				<GeometryNumber
					locale={locale}
					name="rows"
					label={__("Rows", "linker-tools")}
					value={array?.rows}
					unit=""
					help={__("Positive whole number.", "linker-tools")}
				/>
				<GeometryNumber
					locale={locale}
					name="columns"
					label={__("Columns", "linker-tools")}
					value={array?.columns}
					unit=""
					help={__("Positive whole number.", "linker-tools")}
				/>
				<GeometryNumber
					locale={locale}
					name="rotation"
					label={__("Rotation within roof plane", "linker-tools")}
					value={array?.rotation_deg}
					unit="°"
					help={__(
						"Counter-clockwise from the roof U axis toward V.",
						"linker-tools",
					)}
				/>
				<GeometryNumber
					locale={locale}
					name="tilt"
					label={__("Additional module tilt", "linker-tools")}
					value={array?.mount_tilt_deg}
					unit="°"
					help={__(
						"0 to 90, relative to this roof face. Each row starts at its own lower edge.",
						"linker-tools",
					)}
				/>
				<GeometryNumber
					locale={locale}
					name="column_gap"
					label={__("Gap between columns", "linker-tools")}
					value={array?.column_gap_m}
					help={__("0 or greater.", "linker-tools")}
				/>
				<GeometryNumber
					locale={locale}
					name="row_gap"
					label={__("Projected gap between rows", "linker-tools")}
					value={array?.row_gap_m}
					help={__(
						"Gap on the roof plane, 0 or greater. Shading and maintenance requirements are assessed separately.",
						"linker-tools",
					)}
				/>
				<GeometryNumber
					locale={locale}
					name="height"
					label={__("Lower-edge height above roof", "linker-tools")}
					value={array?.lower_edge_clearance_m}
					help={__(
						"0 or greater, measured along the roof normal.",
						"linker-tools",
					)}
				/>
			</div>
			<GeometryText
				name="mounting"
				label={__("Mounting assumptions and reference", "linker-tools")}
				value={array?.mounting_note ?? ""}
				multiline
			/>
			<p className="lp-profile-help">
				{__(
					"The anchor is the lower-left corner of the first row before tilt and thickness are projected. Resizing preserves excluded module slots; slots outside the new size must be restored first.",
					"linker-tools",
				)}
			</p>
		</GeometryForm>
	);
}
