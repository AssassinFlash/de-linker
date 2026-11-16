import type { MapRoofDraft, MapRoofFields } from "../../domain/mapRoofDraft.ts";
import { useId } from "react";
import { useMapPropertyFeedback } from "./useMapPropertyFeedback.ts";
import { Notice } from "../Notice.tsx";
import { decimalSeparator } from "../../domain/decimal.ts";
import { mapDrawingTextLimit } from "../../domain/mapDrawingBase.ts";
import { __ } from "../../i18n.ts";

export function MapRoofProperties({
	drawing,
	sourceProvided = false,
	busy,
	field,
	submit,
	continueDrawing,
	invalidField,
	error,
}: {
	drawing: MapRoofDraft;
	locale: string;
	sourceProvided?: boolean;
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
			onInvalid={(event) => {
				const details = (event.target as HTMLElement).closest("details");
				if (details) details.open = true;
			}}
			onSubmit={(event) => {
				event.preventDefault();
				submit();
			}}
		>
			<h3>{__("Roof properties", "linker-tools")}</h3>
			<p>
				{__(
					"Check the outline, then enter the roof pitch and the direction it faces.",
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
						__("Roof direction (°)", "linker-tools"),
						__("North 0°, east 90°, south 180°, west 270°.", "linker-tools"),
						true,
					)}
				</div>
				<p className="lp-profile-help">
					{decimalSeparator(drawing.locale) === ","
						? __("Decimal comma; no thousands separators.", "linker-tools")
						: __("Decimal point; no thousands separators.", "linker-tools")}
				</p>
				<details
					open={
						!sourceProvided ||
						Boolean(
							invalidField &&
							!["name", "pitch", "bearing"].includes(invalidField),
						)
					}
				>
					<summary>{__("Height and drawing source", "linker-tools")}</summary>
					{fieldInput(
						"height",
						__("Height at marked reference (m)", "linker-tools"),
						__(
							"Height relative to the project origin, not altitude above sea level. The reference is fixed at the first recorded map point.",
							"linker-tools",
						),
						true,
					)}
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
							<option value="permitted">
								{__("Permitted", "linker-tools")}
							</option>
							<option value="prohibited">
								{__("Prohibited", "linker-tools")}
							</option>
						</select>
					</label>
				</details>
				{!(sourceProvided && drawing.fields.permission) && (
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
				)}
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
		</form>
	);
}
