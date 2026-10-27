import type { GeometryDocument } from "../../domain/geometry.ts";
import type { GeometryFormProps } from "./RoofForm.tsx";
import { GeometryForm, GeometryNumber } from "./GeometryForm.tsx";
import { __ } from "../../i18n.ts";

export function CoordinatesForm({
	document,
	locale,
	commit,
	cancel,
	onValidity,
}: GeometryFormProps) {
	const coordinate = document.coordinate_system;
	return (
		<GeometryForm
			title={__("Project coordinate references", "linker-tools")}
			locale={locale}
			cancel={cancel}
			onValidity={onValidity}
			submit={(values) => {
				const north = values.text(
					"north",
				) as GeometryDocument["coordinate_system"]["north_reference"];
				const latitude = values.number("latitude", {
						optional: true,
						min: -90,
						max: 90,
					}),
					longitude = values.number("longitude", {
						optional: true,
						min: -180,
						max: 180,
					});
				if ((latitude === null) !== (longitude === null))
					throw new Error("coordinate_pair_required");
				return commit({
					type: "set_coordinate_system",
					before: coordinate,
					value: {
						...coordinate,
						north_reference: north,
						north_source_id:
							north === "unreferenced" ? null : values.text("north_source"),
						anchor:
							latitude === null || longitude === null
								? null
								: {
										latitude_deg: latitude,
										longitude_deg: longitude,
										source_id: values.text("anchor_source"),
										datum: "EPSG:4326",
									},
					},
				});
			}}
		>
			<p className="lp-profile-help">
				{__(
					"The project uses metres in a local east/north/up frame. A north reference records the stated basis for that frame; it does not rotate existing objects or verify a survey.",
					"linker-tools",
				)}
			</p>
			<label className="lp-field">
				<span>{__("North reference", "linker-tools")}</span>
				<select name="north" defaultValue={coordinate.north_reference}>
					<option value="unreferenced">
						{__("Unreferenced", "linker-tools")}
					</option>
					<option value="user_declared">
						{__("User-declared north", "linker-tools")}
					</option>
					<option value="true_north">
						{__("True north with source reference", "linker-tools")}
					</option>
				</select>
			</label>
			<label className="lp-field">
				<span>{__("North reference source", "linker-tools")}</span>
				<select
					name="north_source"
					defaultValue={coordinate.north_source_id ?? ""}
				>
					<option value="">{__("Select a source", "linker-tools")}</option>
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
					name="latitude"
					label={__("Project origin latitude", "linker-tools")}
					value={coordinate.anchor?.latitude_deg}
					optional
					unit="°"
					help={__(
						"−90 to 90. Both coordinates are required for a geographic anchor; empty fields leave it unknown.",
						"linker-tools",
					)}
				/>
				<GeometryNumber
					locale={locale}
					name="longitude"
					label={__("Project origin longitude", "linker-tools")}
					value={coordinate.anchor?.longitude_deg}
					optional
					unit="°"
					help={__("−180 to 180, WGS 84 (EPSG:4326).", "linker-tools")}
				/>
			</div>
			<label className="lp-field">
				<span>{__("Geographic anchor source", "linker-tools")}</span>
				<select
					name="anchor_source"
					defaultValue={coordinate.anchor?.source_id ?? ""}
				>
					<option value="">{__("Select a source", "linker-tools")}</option>
					{document.sources.map((source) => (
						<option key={source.id} value={source.id}>
							{source.note}
						</option>
					))}
				</select>
			</label>
		</GeometryForm>
	);
}
