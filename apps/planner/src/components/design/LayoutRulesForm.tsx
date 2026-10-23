import type { GeometryFormProps } from "./RoofForm.tsx";
import { GeometryForm, GeometryNumber, GeometryText } from "./GeometryForm.tsx";
import { __ } from "../../i18n.ts";

export function LayoutRulesForm({
	document,
	locale,
	commit,
	cancel,
	onValidity,
	roofId,
}: GeometryFormProps & { roofId: string }) {
	const roof = document.roofs.find((roof) => roof.id === roofId)!;
	const rules =
		document.layout_rules.find((rules) => rules.roof_id === roofId) ?? null;
	return (
		<GeometryForm
			title={__("Declared layout clearances", "linker-tools")}
			locale={locale}
			cancel={cancel}
			onValidity={onValidity}
			submit={(values) =>
				commit({
					type: "set_rules",
					before: rules,
					value: {
						roof_id: roofId,
						source_id: values.text("source"),
						edge_clearance_m: values.number("edge", { optional: true, min: 0 }),
						obstacle_clearance_m: values.number("obstacle", {
							optional: true,
							min: 0,
						}),
						source_note: values.text("note"),
					},
				})
			}
		>
			<p className="lp-profile-help">
				{__(
					"Clearances are project inputs with a stated basis. Empty fields remain unknown. A value of 0 explicitly allows contact in the plan check; it is not a country, fire-safety or mounting approval.",
					"linker-tools",
				)}
			</p>
			<GeometryNumber
				locale={locale}
				name="edge"
				label={__("Minimum roof-edge clearance", "linker-tools")}
				value={rules?.edge_clearance_m}
				optional
				help={__(
					"0 or greater; roof openings are included in the boundary distance.",
					"linker-tools",
				)}
			/>
			<GeometryNumber
				locale={locale}
				name="obstacle"
				label={__("Minimum obstacle clearance", "linker-tools")}
				value={rules?.obstacle_clearance_m}
				optional
				help={__(
					"0 or greater, measured between roof-plane projections.",
					"linker-tools",
				)}
			/>
			<label className="lp-field">
				<span>{__("Clearance source", "linker-tools")}</span>
				<select name="source" defaultValue={rules?.source_id ?? roof.source_id}>
					{document.sources.map((source) => (
						<option key={source.id} value={source.id}>
							{source.note}
						</option>
					))}
				</select>
			</label>
			<GeometryText
				name="note"
				label={__("Requirement, applicability and reference", "linker-tools")}
				value={rules?.source_note ?? ""}
				multiline
			/>
		</GeometryForm>
	);
}
