import type {
	GeometryDocument,
	RoofFace,
	Vec3,
} from "../../domain/geometry.ts";
import type { GeometryCommand } from "../../domain/geometryCommands.ts";
import {
	formatRing,
	manualSource,
	parseHoles,
	parseRing,
	rectangularRoof,
	roofPlane,
} from "../../domain/geometryEditing.ts";
import {
	GeometryExportPermission,
	GeometryForm,
	GeometryNumber,
	GeometryText,
} from "./GeometryForm.tsx";
import { __ } from "../../i18n.ts";

export interface GeometryFormProps {
	document: GeometryDocument;
	locale: string;
	commit: (command: GeometryCommand) => boolean;
	cancel: () => void;
	onValidity: (valid: boolean) => void;
}

/** Recover the two angles only for a frame this form's own constructor makes:
 * a measured rectangle, or a two-point calibrated drawing. */
function measuredAngles(
	document: GeometryDocument,
	roof: RoofFace | null,
	imported: boolean,
) {
	// V extends down-slope, so a face this constructor makes never points up;
	// a flat roof's V is exactly horizontal.
	if (!roof || imported || roof.u_axis_enu[2] !== 0 || roof.v_axis_enu[2] > 0)
		return null;
	const source = document.sources.find((item) => item.id === roof.source_id);
	const measured =
		source?.kind === "user_measurement" && source.reference_sha256 === null;
	const calibrated =
		source?.kind === "user_drawing" && source.calibration != null;
	if (!measured && !calibrated) return null;
	const [ux, uy] = roof.u_axis_enu;
	const [vx, vy, vz] = roof.v_axis_enu;
	const pitch = (Math.atan2(Math.abs(vz), Math.hypot(vx, vy)) * 180) / Math.PI;
	const azimuth = (Math.atan2(-uy, ux) * 180) / Math.PI;
	const bearing = azimuth < 0 ? (azimuth + 360) % 360 : azimuth;
	// Binary64 has 15 reliable decimal digits. Prefer the short angles only
	// when they recreate both saved axes exactly, including near-vertical roofs.
	const short = {
		pitch: Number(pitch.toPrecision(15)),
		bearing: Number(bearing.toPrecision(15)) % 360,
	};
	const plane = roofPlane(short.pitch, short.bearing, roof.origin_enu);
	if (
		short.pitch < 90 &&
		plane.u_axis_enu.every((n, i) => n === roof.u_axis_enu[i]) &&
		plane.v_axis_enu.every((n, i) => n === roof.v_axis_enu[i])
	)
		return short;
	return { pitch, bearing };
}

export function RoofForm({
	document,
	locale,
	commit,
	cancel,
	onValidity,
	roof,
	imported,
}: GeometryFormProps & { roof: RoofFace | null; imported: boolean }) {
	const orientation = measuredAngles(document, roof, imported);
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
				const origin: Vec3 = [
					values.metric("east"),
					values.metric("north"),
					values.metric("up"),
				];
				if (roof) {
					let plane = {
						origin_enu: origin,
						u_axis_enu: roof.u_axis_enu,
						v_axis_enu: roof.v_axis_enu,
					};
					if (orientation) {
						const pitch = values.metric("pitch", { min: 0, maxExclusive: 90 });
						const bearing = values.metric("bearing");
						// Keep the saved basis byte-for-byte for unrelated edits.
						if (pitch !== orientation.pitch || bearing !== orientation.bearing)
							plane = roofPlane(pitch, bearing, origin);
					}
					return commit({
						type: "put_roof",
						before: roof,
						value: {
							...roof,
							name: values.text("name"),
							...plane,
							boundary_uv: parseRing(values.text("boundary"), locale),
							holes_uv: parseHoles(values.text("holes"), locale),
						},
					});
				}
				if (!values.checked("rights")) return false;
				const id = "roof_" + crypto.randomUUID().replaceAll("-", ""),
					sourceId = "source_" + crypto.randomUUID().replaceAll("-", "");
				const source = manualSource(
					sourceId,
					values.text("source"),
					values.text("rights_note"),
				);
				source.permissions.export = values.text(
					"export",
				) as typeof source.permissions.export;
				source.calibration_note = __("Not recorded.", "linker-tools");
				const next = rectangularRoof(
					{ id, name: values.text("name"), source_id: sourceId },
					{
						width: values.metric("width", { positive: true }),
						slopeLength: values.metric("length", { positive: true }),
						pitch: values.metric("pitch", { min: 0, maxExclusive: 90 }),
						bearing: values.metric("bearing"),
						origin,
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
			{(!roof || orientation) && (
				<div className="lp-geometry-fields">
					{!roof && (
						<>
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
						</>
					)}
					<GeometryNumber
						{...numberProps}
						name="pitch"
						value={orientation?.pitch}
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
						value={orientation?.bearing}
						label={__("Down-slope bearing", "linker-tools")}
						unit="°"
						help={__(
							"Clockwise from project north: 0 north, 90 east, 180 south, 270 west. Bearings use the project's stated north reference; recording a reference does not verify it.",
							"linker-tools",
						)}
					/>
				</div>
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
					<GeometryExportPermission />
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
