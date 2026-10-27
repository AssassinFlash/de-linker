import type { MapRoofDraft, MapRoofFields } from "../../domain/mapRoofDraft.ts";
import { useId } from "react";
import { useMapPropertyFeedback } from "./useMapPropertyFeedback.ts";
import { Notice } from "../Notice.tsx";
import { decimalSeparator, formatDecimal } from "../../domain/decimal.ts";
import { mapDrawingTextLimit } from "../../domain/mapDrawingBase.ts";
import { __, sprintf } from "../../i18n.ts";

export function MapRoofProperties({
	drawing,
	locale,
	busy,
	field,
	submit,
	continueDrawing,
	invalidField,
	error,
}: {
	drawing: MapRoofDraft;
	locale: string;
	busy: boolean;
	field: <K extends keyof MapRoofFields>(
		name: K,
		value: MapRoofFields[K],
	) => void;
	submit: () => void;
	continueDrawing: () => void;
	invalidField: string | null;
	error: string | null;
}) {
	const { form, result } = useMapPropertyFeedback(error, invalidField);
	const errorId = useId();
	const fieldInput = (
		name: keyof Omit<MapRoofFields, "permission" | "export">,
		label: string,
		help?: string,
		numeric = false,
		optional = false,
		multiline = false,
	) => (
		<label className="lp-field" key={name}>
			<span>{label}</span>
			{multiline ? (
				<textarea
					name={name}
					value={drawing!.fields[name]}
					onChange={(e) => field(name, e.target.value)}
					maxLength={mapDrawingTextLimit}
					required={!optional}
					rows={3}
					aria-invalid={invalidField === name || undefined}
					aria-describedby={invalidField === name ? errorId : undefined}
				/>
			) : (
				<input
					name={name}
					value={drawing!.fields[name]}
					onChange={(e) => field(name, e.target.value)}
					maxLength={mapDrawingTextLimit}
					required={!optional}
					inputMode={numeric ? "decimal" : "text"}
					aria-invalid={invalidField === name || undefined}
					aria-describedby={invalidField === name ? errorId : undefined}
				/>
			)}
			{help && <small>{help}</small>}
			{invalidField === name && error && (
				<small id={errorId} className="lp-field-error" role="alert">
					{error}
				</small>
			)}
		</label>
	);
	return (
		<form
			ref={form}
			className="lp-drawing-properties lp-focus-target"
			id="lp-map-roof-properties"
			onSubmit={(event) => {
				event.preventDefault();
				submit();
			}}
		>
			<h3>{__("Roof properties", "linker-tools")}</h3>
			<p>
				{__(
					"Drag a corner to move it, or use an edge midpoint to add a corner. The marked height reference stays fixed when the outline changes.",
					"linker-tools",
				)}
			</p>
			<fieldset disabled={busy}>
				<div className="lp-geometry-fields">
					{fieldInput("name", __("Roof face name", "linker-tools"))}
					{fieldInput(
						"pitch",
						__("Roof pitch (°)", "linker-tools"),
						__(
							"0 or greater and less than 90. A flat roof is 0.",
							"linker-tools",
						),
						true,
					)}
					{fieldInput(
						"bearing",
						__("Down-slope bearing (°)", "linker-tools"),
						__(
							"Clockwise from true north, 0 to less than 360. North is 0, east 90, south 180 and west 270.",
							"linker-tools",
						),
						true,
					)}
					{fieldInput(
						"height",
						__("Height at marked reference (m)", "linker-tools"),
						__(
							"Height relative to the project origin, not altitude above sea level. The reference is fixed at the first recorded map point.",
							"linker-tools",
						),
						true,
					)}
				</div>
				{drawing.height_reference_position && (
					<p className="lp-profile-help">
						{sprintf(
							__(
								"Height reference: longitude %1$s; latitude %2$s.",
								"linker-tools",
							),
							formatDecimal(drawing.height_reference_position[0], locale),
							formatDecimal(drawing.height_reference_position[1], locale),
						)}
					</p>
				)}
				<p className="lp-profile-help">
					{decimalSeparator(drawing.locale) === ","
						? __("Decimal comma; no thousands separators.", "linker-tools")
						: __("Decimal point; no thousands separators.", "linker-tools")}
				</p>
				{fieldInput(
					"source",
					__("Measurement or drawing reference", "linker-tools"),
					__(
						"The source reference identifies the measurements or drawing used for the outline, slope and height. The street map provides orientation.",
						"linker-tools",
					),
					false,
					false,
					true,
				)}
				<div className="lp-geometry-fields">
					{fieldInput(
						"precision",
						__("Declared spatial precision (m)", "linker-tools"),
						__(
							"0 or greater. An empty field means unknown. This is a source claim, separate from numerical calculation precision.",
							"linker-tools",
						),
						true,
						true,
					)}
					{fieldInput(
						"calibration",
						__("Calibration and measurement conditions", "linker-tools"),
						undefined,
						false,
						false,
						true,
					)}
				</div>
				{fieldInput(
					"rights",
					__("Basis for using these measurements", "linker-tools"),
					undefined,
					false,
					false,
					true,
				)}
				<label className="lp-field">
					<span>{__("Permission to export geometry", "linker-tools")}</span>
					<select
						value={drawing.fields.export}
						onChange={(e) =>
							field("export", e.target.value as MapRoofFields["export"])
						}
					>
						<option value="unknown">{__("Unknown", "linker-tools")}</option>
						<option value="permitted">{__("Permitted", "linker-tools")}</option>
						<option value="prohibited">
							{__("Prohibited", "linker-tools")}
						</option>
					</select>
				</label>
				<label className="lp-geometry-check">
					<input
						type="checkbox"
						checked={drawing.fields.permission}
						onChange={(e) => field("permission", e.target.checked)}
						required
					/>
					{__(
						"I have permission to retain these measurements and derive an editable design from them.",
						"linker-tools",
					)}
				</label>
				{error && !invalidField && (
					<div ref={result} tabIndex={-1} className="lp-focus-target">
						<Notice error>{error}</Notice>
					</div>
				)}
				<div className="lp-inline-actions">
					<button type="submit" className="lp-button">
						{__("Check and add roof face", "linker-tools")}
					</button>
					<button
						type="button"
						className="lp-button lp-button-secondary"
						onClick={continueDrawing}
					>
						{__("Continue adding corners", "linker-tools")}
					</button>
				</div>
			</fieldset>
			<p className="lp-profile-help">
				{__(
					"This check tests roof boundary geometry. It does not verify measurement accuracy, structural safety or engineering approval.",
					"linker-tools",
				)}
			</p>
		</form>
	);
}
