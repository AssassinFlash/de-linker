import { useId } from "react";
import type {
	MapFeatureDraft,
	MapFeatureFields,
} from "../../domain/mapFeatureDraft.ts";
import { mapFeatureSource } from "../../domain/mapFeatureDraft.ts";
import { decimalSeparator } from "../../domain/decimal.ts";
import { useMapPropertyFeedback } from "./useMapPropertyFeedback.ts";
import { MapSourceDetails } from "./MapSourceDetails.tsx";
import { mapFeatureContext } from "./mapDrawingLabels.ts";
import { Notice } from "../Notice.tsx";
import { __ } from "../../i18n.ts";

export function MapFeatureProperties({
	drawing,
	locale,
	busy,
	invalidField,
	error,
	field,
	submit,
	continueDrawing,
}: {
	drawing: MapFeatureDraft;
	locale: string;
	busy: boolean;
	invalidField: string | null;
	error: string | null;
	field: <K extends keyof MapFeatureFields>(
		name: K,
		value: MapFeatureFields[K],
	) => void;
	submit: () => void;
	continueDrawing: () => void;
}) {
	const { form, result } = useMapPropertyFeedback(error, invalidField),
		errorId = useId();
	const invalid = (name: string) => ({
		"aria-invalid": invalidField === name || undefined,
		"aria-describedby": invalidField === name ? errorId : undefined,
	});
	return (
		<form
			ref={form}
			id="lp-map-feature-properties"
			className="lp-drawing-properties lp-focus-target"
			onSubmit={(event) => {
				event.preventDefault();
				submit();
			}}
		>
			<h3>{__("Feature properties", "linker-tools")}</h3>
			<p>{mapFeatureContext(drawing)}</p>
			<p>
				{__(
					"The outline lies in the selected roof plane. Check the source details and feature properties before adding it to the project draft.",
					"linker-tools",
				)}
			</p>
			<fieldset disabled={busy}>
				{drawing.target.kind !== "hole" && (
					<>
						<label className="lp-field">
							<span>{__("Object name", "linker-tools")}</span>
							<input
								name="name"
								value={drawing.fields.name}
								onChange={(event) => field("name", event.currentTarget.value)}
								required
								maxLength={4096}
								{...invalid("name")}
							/>
						</label>
						<label className="lp-field">
							<span>{__("Source reference", "linker-tools")}</span>
							<select
								name="source_id"
								value={drawing.fields.source_id}
								onChange={(event) =>
									field("source_id", event.currentTarget.value)
								}
								required
								{...invalid("source_id")}
							>
								{drawing.before.sources.map((source) => (
									<option key={source.id} value={source.id}>
										{source.note}
									</option>
								))}
							</select>
						</label>
					</>
				)}
				{drawing.target.kind === "obstacle" && (
					<div className="lp-geometry-fields">
						<label className="lp-field">
							<span>{__("Obstacle height", "linker-tools")} (m)</span>
							<input
								name="height"
								inputMode="decimal"
								value={drawing.fields.height}
								onChange={(event) => field("height", event.currentTarget.value)}
								required
								maxLength={4096}
								{...invalid("height")}
							/>
							<small>
								{__(
									"Greater than 0, measured along the selected extrusion direction.",
									"linker-tools",
								)}
							</small>
						</label>
						<label className="lp-field">
							<span>{__("Extrusion direction", "linker-tools")}</span>
							<select
								name="axis"
								value={drawing.fields.axis}
								onChange={(event) =>
									field(
										"axis",
										event.currentTarget.value as MapFeatureFields["axis"],
									)
								}
								required
								{...invalid("axis")}
							>
								<option value="">
									{__("Select a direction", "linker-tools")}
								</option>
								<option value="normal">
									{__("Perpendicular to this roof face", "linker-tools")}
								</option>
								<option value="vertical">
									{__("Vertically upward", "linker-tools")}
								</option>
							</select>
						</label>
						<p className="lp-profile-help">
							{decimalSeparator(drawing.locale) === ","
								? __("Decimal comma; no thousands separators.", "linker-tools")
								: __("Decimal point; no thousands separators.", "linker-tools")}
						</p>
					</div>
				)}
				{drawing.target.kind === "keepout" && (
					<label className="lp-field">
						<span>{__("Reason or requirement", "linker-tools")}</span>
						<textarea
							name="reason"
							value={drawing.fields.reason}
							onChange={(event) => field("reason", event.currentTarget.value)}
							rows={3}
							required
							maxLength={4096}
							{...invalid("reason")}
						/>
					</label>
				)}
				<MapSourceDetails source={mapFeatureSource(drawing)} locale={locale} />
				<label className="lp-geometry-check">
					<input
						name="source_confirmed"
						type="checkbox"
						checked={drawing.fields.source_confirmed}
						onChange={(event) =>
							field("source_confirmed", event.currentTarget.checked)
						}
						required
						{...invalid("source_confirmed")}
					/>
					{__(
						"I have checked that the recorded source and permissions cover this new roof feature.",
						"linker-tools",
					)}
				</label>
				{invalidField && error && (
					<small id={errorId} className="lp-field-error" role="alert">
						{error}
					</small>
				)}
				{!invalidField && error && (
					<div ref={result} tabIndex={-1} className="lp-focus-target">
						<Notice error>{error}</Notice>
					</div>
				)}
				<div className="lp-inline-actions">
					<button type="submit" className="lp-button">
						{__("Check and add feature", "linker-tools")}
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
					"The geometry check does not verify measurements or source permissions. Your confirmation does not change the recorded export permission. If the source or permissions do not cover your changes, pause the drawing and review the project's source details.",
					"linker-tools",
				)}
			</p>
		</form>
	);
}
