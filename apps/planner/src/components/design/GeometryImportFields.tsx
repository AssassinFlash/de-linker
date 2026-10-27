import type { GeoJsonChoice } from "../../domain/geoJsonChoices.ts";
import type { GeographicReference } from "../../domain/geographic.ts";
import type { GeometryImportOptions } from "../../domain/geometryImports.ts";
import { formatDecimal } from "../../domain/decimal.ts";
import { GeometryNumber, GeometryText } from "./GeometryForm.tsx";
import { __, sprintf } from "../../i18n.ts";

export const choiceKey = (choice: GeoJsonChoice) =>
	`${choice.featureIndex}:${choice.polygonIndex}`;
export function choiceLabel(choice: GeoJsonChoice): string {
	return sprintf(
		__("%1$s · face %2$d", "linker-tools"),
		choice.name ??
			sprintf(__("Feature %d", "linker-tools"), choice.featureIndex + 1),
		choice.polygonIndex + 1,
	);
}

/** Steps remain mounted: Back and validation never erase unfinished values. */
export function GeometryImportFields({
	step,
	choices,
	selected,
	select,
	roofName,
	setRoofName,
	reference,
	locale,
	zeroHeight,
	setZeroHeight,
	original,
}: {
	step: number;
	choices: readonly GeoJsonChoice[];
	selected: string;
	select: (key: string) => void;
	roofName: string;
	setRoofName: (value: string) => void;
	reference: GeographicReference | null;
	locale: string;
	zeroHeight: boolean;
	setZeroHeight: (value: boolean) => void;
	original?: GeometryImportOptions | undefined;
}) {
	const current = choices.find((choice) => choiceKey(choice) === selected);
	return (
		<>
			<section data-import-step="0" hidden={step !== 0}>
				<label className="lp-field">
					<span>{__("Roof in this file", "linker-tools")}</span>
					<select
						name="selection"
						value={selected}
						onChange={(event) => select(event.currentTarget.value)}
						required
					>
						<option value="">{__("Select a roof face", "linker-tools")}</option>
						{choices.map((choice) => (
							<option key={choiceKey(choice)} value={choiceKey(choice)}>
								{choiceLabel(choice)}
							</option>
						))}
					</select>
				</label>
				{current && (
					<p className="lp-profile-help">
						{sprintf(
							__("Openings in source: %d", "linker-tools"),
							current.openingCount,
						)}
					</p>
				)}
				<label className="lp-field">
					<span>{__("Roof face name", "linker-tools")}</span>
					<input
						name="roof"
						value={roofName}
						onChange={(event) => setRoofName(event.currentTarget.value)}
						maxLength={4096}
						required
					/>
				</label>
			</section>
			<section data-import-step="1" hidden={step !== 1}>
				<p>
					{__(
						"The file provides the horizontal outline. Add the roof pitch, downslope direction and relative height from a survey or drawing to reconstruct the roof surface.",
						"linker-tools",
					)}
				</p>
				<div className="lp-geometry-fields">
					<GeometryNumber
						locale={locale}
						name="pitch"
						unit="°"
						label={__("Roof pitch", "linker-tools")}
						help={__(
							"Enter 0° for a flat roof, or a value greater than 0° and below 90°.",
							"linker-tools",
						)}
					/>
					<GeometryNumber
						locale={locale}
						name="bearing"
						unit="°"
						label={__("Downslope direction from true north", "linker-tools")}
						help={__(
							"Measured clockwise from true north: 0° north, 90° east, 180° south, 270° west. For a flat roof this sets its local drawing axes.",
							"linker-tools",
						)}
					/>
				</div>
				<label className="lp-geometry-check">
					<input
						type="checkbox"
						checked={zeroHeight}
						onChange={(event) => setZeroHeight(event.currentTarget.checked)}
					/>
					<span>
						{__(
							"Set the first outline point's relative height to 0 m",
							"linker-tools",
						)}
					</span>
				</label>
				<p className="lp-profile-help">
					{__(
						"0 m uses the project's height reference. It does not establish ground level or height above sea level. Other roofs and obstacles must use the same height reference.",
						"linker-tools",
					)}
				</p>
				<div hidden={zeroHeight}>
					<GeometryNumber
						locale={locale}
						name="height"
						optional={zeroHeight}
						label={__(
							"Relative height at the first outline point",
							"linker-tools",
						)}
						help={__(
							"Metres relative to the project's height reference. Negative values are allowed.",
							"linker-tools",
						)}
					/>
				</div>
				<GeometryText
					name="basis"
					value={original?.plane.basis_note ?? ""}
					label={__("Measurement or drawing reference", "linker-tools")}
					help={__(
						"Identify the drawing or survey used for pitch, downslope direction and relative height. Include its date or identifier.",
						"linker-tools",
					)}
					multiline
				/>
				<details className="lp-comparison">
					<summary>
						{__("Position and coordinate reference", "linker-tools")}
					</summary>
					<p>
						{__(
							"An existing geographic project origin is kept. For an empty, unreferenced project, the first point of the selected outer outline becomes the geographic origin, with WGS 84 true north. This sets the coordinate reference; it does not verify the survey.",
							"linker-tools",
						)}
					</p>
					{reference && (
						<p>
							{formatDecimal(reference.latitude_deg, locale)}° ·{" "}
							{formatDecimal(reference.longitude_deg, locale)}° · WGS 84
						</p>
					)}
				</details>
			</section>
			<section data-import-step="2" hidden={step !== 2}>
				<GeometryText
					name="source"
					value={original?.source.label ?? ""}
					label={__("Source reference", "linker-tools")}
					help={__(
						"Name the drawing, survey or data export used for this roof.",
						"linker-tools",
					)}
				/>
				<GeometryNumber
					locale={locale}
					name="precision"
					value={original?.source.spatial_precision_m}
					optional
					label={__("Declared spatial precision", "linker-tools")}
					help={__(
						"Source-stated precision, in metres. Leave blank if unknown.",
						"linker-tools",
					)}
				/>
				<GeometryText
					name="rights"
					value={original?.source.rights_note ?? ""}
					label={__("Permission or licence basis", "linker-tools")}
					help={__(
						"Explain your permission to use and privately retain this original file and its derived geometry.",
						"linker-tools",
					)}
					multiline
				/>
				<label className="lp-field">
					<span>{__("Permission to export geometry", "linker-tools")}</span>
					<select
						name="export"
						defaultValue={original?.source.export_permission ?? "unknown"}
					>
						<option value="unknown">{__("Unknown", "linker-tools")}</option>
						<option value="permitted">{__("Permitted", "linker-tools")}</option>
						<option value="prohibited">
							{__("Prohibited", "linker-tools")}
						</option>
					</select>
				</label>
				<label className="lp-geometry-check">
					<input name="retention" type="checkbox" required />
					<span>
						{__(
							"I have permission to upload this original file, derive roof geometry from it and retain both privately with this project.",
							"linker-tools",
						)}
					</span>
				</label>
			</section>
		</>
	);
}
