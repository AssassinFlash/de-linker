import type { Keepout, Obstacle, Vec2 } from "../../domain/geometry.ts";
import { cross } from "../../domain/coordinates.ts";
import { formatRing, parseRing } from "../../domain/geometryEditing.ts";
import type { GeometryFormProps } from "./RoofForm.tsx";
import { GeometryForm, GeometryNumber, GeometryText } from "./GeometryForm.tsx";
import { __ } from "../../i18n.ts";

export function ShapeForm({
	document,
	locale,
	commit,
	cancel,
	onValidity,
	object,
	kind,
	roofId,
}: GeometryFormProps & {
	object: Obstacle | Keepout | null;
	kind: "obstacle" | "keepout";
	roofId: string;
}) {
	const roof = document.roofs.find((roof) => roof.id === roofId)!;
	return (
		<GeometryForm
			title={
				kind === "obstacle"
					? __("Obstacle properties", "linker-tools")
					: __("Keep-out area properties", "linker-tools")
			}
			locale={locale}
			cancel={cancel}
			onValidity={onValidity}
			submit={(values) => {
				let footprint: readonly Vec2[];
				if (object) footprint = parseRing(values.text("footprint"), locale);
				else {
					const u = values.metric("u"),
						v = values.metric("v"),
						width = values.metric("width", { positive: true }),
						length = values.metric("length", { positive: true });
					footprint = [
						[u, v],
						[u + width, v],
						[u + width, v + length],
						[u, v + length],
					];
				}
				const base = {
					id:
						object?.id ?? kind + "_" + crypto.randomUUID().replaceAll("-", ""),
					name: values.text("name"),
					roof_id: roofId,
					source_id: values.text("source"),
					footprint_uv: footprint,
				};
				if (kind === "keepout")
					return commit({
						type: "put_keepout",
						before: object as Keepout | null,
						value: { ...base, reason: values.text("reason") },
					});
				const axis = values.text("axis");
				return commit({
					type: "put_obstacle",
					before: object as Obstacle | null,
					value: {
						...base,
						height_m: values.metric("height", { positive: true }),
						extrusion_axis_enu:
							axis === "existing"
								? (object as Obstacle).extrusion_axis_enu
								: axis === "normal"
									? cross(roof.u_axis_enu, roof.v_axis_enu)
									: [0, 0, 1],
					},
				});
			}}
		>
			<GeometryText
				name="name"
				label={__("Object name", "linker-tools")}
				value={object?.name ?? ""}
			/>
			<label className="lp-field">
				<span>{__("Source reference", "linker-tools")}</span>
				<select
					name="source"
					defaultValue={object?.source_id ?? roof.source_id}
				>
					{document.sources.map((source) => (
						<option key={source.id} value={source.id}>
							{source.note}
						</option>
					))}
				</select>
			</label>
			{object ? (
				<GeometryText
					name="footprint"
					label={__("Footprint in U/V metres", "linker-tools")}
					value={formatRing(object.footprint_uv, locale)}
					multiline
					help={__(
						"One U ; V pair per line, at least three vertices. The final vertex connects to the first.",
						"linker-tools",
					)}
				/>
			) : (
				<div className="lp-geometry-fields">
					<GeometryNumber
						locale={locale}
						name="u"
						label={__("Lower corner U", "linker-tools")}
					/>
					<GeometryNumber
						locale={locale}
						name="v"
						label={__("Lower corner V", "linker-tools")}
					/>
					<GeometryNumber
						locale={locale}
						name="width"
						label={__("Width along U", "linker-tools")}
						help={__("Greater than 0.", "linker-tools")}
					/>
					<GeometryNumber
						locale={locale}
						name="length"
						label={__("Length along V", "linker-tools")}
						help={__("Greater than 0.", "linker-tools")}
					/>
				</div>
			)}
			{kind === "obstacle" ? (
				<>
					<GeometryNumber
						locale={locale}
						name="height"
						label={__("Obstacle height", "linker-tools")}
						value={object ? (object as Obstacle).height_m : null}
						help={__(
							"Greater than 0, measured along the selected extrusion direction.",
							"linker-tools",
						)}
					/>
					<label className="lp-field">
						<span>{__("Extrusion direction", "linker-tools")}</span>
						<select
							name="axis"
							required
							defaultValue={object ? "existing" : ""}
						>
							<option value="">
								{__("Select a direction", "linker-tools")}
							</option>
							{object && (
								<option value="existing">
									{__("Keep the recorded direction", "linker-tools")}
								</option>
							)}
							<option value="normal">
								{__("Perpendicular to this roof face", "linker-tools")}
							</option>
							<option value="vertical">
								{__("Vertically upward", "linker-tools")}
							</option>
						</select>
					</label>
				</>
			) : (
				<GeometryText
					name="reason"
					label={__("Reason or requirement", "linker-tools")}
					value={object ? (object as Keepout).reason : ""}
					multiline
				/>
			)}
		</GeometryForm>
	);
}
