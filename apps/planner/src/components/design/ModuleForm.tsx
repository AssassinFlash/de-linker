import type { ModuleSpec } from "../../domain/geometry.ts";
import type { GeometryFormProps } from "./RoofForm.tsx";
import { GeometryForm, GeometryNumber, GeometryText } from "./GeometryForm.tsx";
import { __ } from "../../i18n.ts";

export function ModuleForm({
	locale,
	commit,
	cancel,
	onValidity,
	module,
}: GeometryFormProps & { module: ModuleSpec | null }) {
	return (
		<GeometryForm
			title={__("Module specification", "linker-tools")}
			locale={locale}
			cancel={cancel}
			onValidity={onValidity}
			submit={(values) =>
				commit({
					type: "put_module",
					before: module,
					value: {
						id:
							module?.id ?? "module_" + crypto.randomUUID().replaceAll("-", ""),
						model: values.text("model"),
						width_m: values.metric("width", { positive: true }),
						length_m: values.metric("length", { positive: true }),
						thickness_m: values.metric("thickness", { positive: true }),
						stc_power_w: values.metric("power", { positive: true }),
						source: {
							kind: values.text("kind") as ModuleSpec["source"]["kind"],
							note: values.text("note"),
							url: values.text("url") || null,
							document_sha256: values.text("hash") || null,
							page: values.number("page", {
								optional: true,
								integer: true,
								positive: true,
							}),
						},
					},
				})
			}
		>
			<GeometryText
				name="model"
				label={__("Model or reference name", "linker-tools")}
				value={module?.model ?? ""}
			/>
			<div className="lp-geometry-fields">
				<GeometryNumber
					locale={locale}
					name="width"
					label={__("Module width", "linker-tools")}
					value={module?.width_m}
					help={__("Greater than 0.", "linker-tools")}
				/>
				<GeometryNumber
					locale={locale}
					name="length"
					label={__("Module length", "linker-tools")}
					value={module?.length_m}
					help={__("Greater than 0.", "linker-tools")}
				/>
				<GeometryNumber
					locale={locale}
					name="thickness"
					label={__("Module thickness", "linker-tools")}
					value={module?.thickness_m}
					help={__("Greater than 0.", "linker-tools")}
				/>
				<GeometryNumber
					locale={locale}
					name="power"
					label={__("Rated power at STC", "linker-tools")}
					value={module?.stc_power_w}
					unit="W"
					help={__(
						"Declared nameplate power, greater than 0. This is not generated energy.",
						"linker-tools",
					)}
				/>
			</div>
			<label className="lp-field">
				<span>{__("Specification evidence", "linker-tools")}</span>
				<select
					name="kind"
					defaultValue={module?.source.kind ?? "user_declared"}
				>
					<option value="user_declared">
						{__("User-declared values", "linker-tools")}
					</option>
					<option value="datasheet">
						{__("Referenced datasheet", "linker-tools")}
					</option>
				</select>
			</label>
			<GeometryText
				name="note"
				label={__("Specification source and conditions", "linker-tools")}
				value={module?.source.note ?? ""}
				multiline
			/>
			<GeometryText
				name="url"
				label={__("Source document URL", "linker-tools")}
				value={module?.source.url ?? ""}
				optional
			/>
			<GeometryText
				name="hash"
				label={__("Source document SHA-256", "linker-tools")}
				value={module?.source.document_sha256 ?? ""}
				optional
			/>
			<GeometryNumber
				locale={locale}
				name="page"
				label={__("Source page", "linker-tools")}
				value={module?.source.page}
				optional
				unit=""
				help={__(
					"A datasheet reference requires its URL, 64-character SHA-256 and a positive whole page number. The reference is recorded; this form does not fetch or verify the document.",
					"linker-tools",
				)}
			/>
		</GeometryForm>
	);
}
