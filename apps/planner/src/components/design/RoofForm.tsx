import type { GeometryDocument, RoofFace } from "../../domain/geometry.ts";
import type { GeometryCommand } from "../../domain/geometryCommands.ts";
import {
	formatRing,
	manualSource,
	parseHoles,
	parseRing,
	rectangularRoof,
} from "../../domain/geometryEditing.ts";
import { GeometryForm, GeometryNumber, GeometryText } from "./GeometryForm.tsx";
import { __ } from "../../i18n.ts";

export interface GeometryFormProps {
	document: GeometryDocument;
	locale: string;
	commit: (command: GeometryCommand) => boolean;
	cancel: () => void;
	onValidity: (valid: boolean) => void;
}

export function RoofForm({
	document,
	locale,
	commit,
	cancel,
	onValidity,
	roof,
}: GeometryFormProps & { roof: RoofFace | null }) {
	const numberProps = { locale };
	return (
		<GeometryForm
			title={
				roof
					? __("Roof properties", "linker-tools")
					: __("Add a measured roof face", "linker-tools")
			}
			locale={locale}
			cancel={cancel}
			onValidity={onValidity}
			submit={(values) => {
				if (roof)
					return commit({
						type: "put_roof",
						before: roof,
						value: {
							...roof,
							name: values.text("name"),
							origin_enu: [
								values.metric("east"),
								values.metric("north"),
								values.metric("up"),
							],
							boundary_uv: parseRing(values.text("boundary"), locale),
							holes_uv: parseHoles(values.text("holes"), locale),
						},
					});
				if (!values.checked("rights")) return false;
				const id = "roof_" + crypto.randomUUID().replaceAll("-", ""),
					sourceId = "source_" + crypto.randomUUID().replaceAll("-", "");
				const source = {
					...manualSource(
						sourceId,
						values.text("source"),
						values.text("rights_note"),
					),
					calibration_note: __("Not recorded.", "linker-tools"),
				};
				const next = rectangularRoof(
					{ id, name: values.text("name"), source_id: sourceId },
					{
						width: values.metric("width", { positive: true }),
						slopeLength: values.metric("length", { positive: true }),
						pitch: values.metric("pitch", { min: 0, maxExclusive: 90 }),
						bearing: values.metric("bearing"),
						origin: [
							values.metric("east"),
							values.metric("north"),
							values.metric("up"),
						],
					},
				);
				return commit({
					type: "group",
					edits: [
						{ type: "put_source", before: null, value: source },
						{ type: "put_roof", before: null, value: next },
					],
				});
			}}
		>
			<GeometryText
				name="name"
				label={__("Roof face name", "linker-tools")}
				value={roof?.name ?? ""}
			/>
			{!roof && (
				<>
					<div className="lp-geometry-fields">
						<GeometryNumber
							{...numberProps}
							name="width"
							label={__("Width along U", "linker-tools")}
							help={__("Greater than 0.", "linker-tools")}
						/>
						<GeometryNumber
							{...numberProps}
							name="length"
							label={__("Length down the slope", "linker-tools")}
							help={__(
								"Surface length, greater than 0; this is not its horizontal projection.",
								"linker-tools",
							)}
						/>
						<GeometryNumber
							{...numberProps}
							name="pitch"
							label={__("Roof pitch", "linker-tools")}
							unit="°"
							help={__(
								"0 or greater and less than 90. A flat roof is 0.",
								"linker-tools",
							)}
						/>
						<GeometryNumber
							{...numberProps}
							name="bearing"
							label={__("Down-slope bearing", "linker-tools")}
							unit="°"
							help={__(
								"Clockwise from project north: 0 north, 90 east, 180 south, 270 west. Bearings use the project's stated north reference; recording a reference does not verify it.",
								"linker-tools",
							)}
						/>
					</div>
				</>
			)}
			<p className="lp-profile-help">
				{__(
					"The origin is the high corner of the roof face. East, north and height are relative to the project origin; height is not altitude above sea level.",
					"linker-tools",
				)}
			</p>
			<div className="lp-geometry-fields">
				<GeometryNumber
					{...numberProps}
					name="east"
					label={__("Origin east", "linker-tools")}
					value={roof?.origin_enu[0] ?? (document.roofs.length ? null : 0)}
				/>
				<GeometryNumber
					{...numberProps}
					name="north"
					label={__("Origin north", "linker-tools")}
					value={roof?.origin_enu[1] ?? (document.roofs.length ? null : 0)}
				/>
				<GeometryNumber
					{...numberProps}
					name="up"
					label={__("Origin height", "linker-tools")}
					value={roof?.origin_enu[2] ?? (document.roofs.length ? null : 0)}
				/>
			</div>
			{roof ? (
				<>
					<GeometryText
						name="boundary"
						label={__("Roof boundary in U/V metres", "linker-tools")}
						value={formatRing(roof.boundary_uv, locale)}
						multiline
						help={__(
							"One U ; V pair per line, at least three vertices. The final vertex connects to the first. The existing roof plane is preserved.",
							"linker-tools",
						)}
					/>
					<GeometryText
						name="holes"
						label={__("Roof openings in U/V metres", "linker-tools")}
						value={roof.holes_uv
							.map((ring) => formatRing(ring, locale))
							.join("\n\n")}
						optional
						multiline
						help={__(
							"One U ; V pair per line. A blank line separates openings; an empty field means no openings.",
							"linker-tools",
						)}
					/>
				</>
			) : (
				<>
					<GeometryText
						name="source"
						label={__("Measurement or drawing reference", "linker-tools")}
						multiline
						help={__(
							"The reference stays with this roof face in the project draft and is stored with Save project. Measurement precision starts as unknown and can be recorded in Source properties.",
							"linker-tools",
						)}
					/>
					<GeometryText
						name="rights_note"
						label={__("Basis for using these measurements", "linker-tools")}
						multiline
					/>
					<label className="lp-geometry-check">
						<input name="rights" type="checkbox" required />
						{__(
							"I have permission to retain these measurements and derive an editable design from them.",
							"linker-tools",
						)}
					</label>
				</>
			)}
		</GeometryForm>
	);
}
