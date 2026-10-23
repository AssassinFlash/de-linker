import { useId } from "react";
import type { MapRingDraft } from "../../domain/mapRingDraft.ts";
import { mapRingMetadata } from "../../domain/mapDrawingGeometry.ts";
import { formatDecimal } from "../../domain/decimal.ts";
import { mapRingLabel } from "./mapDrawingLabels.ts";
import { useMapPropertyFeedback } from "./useMapPropertyFeedback.ts";
import { Notice } from "../Notice.tsx";
import { __ } from "../../i18n.ts";

export function MapRingProperties({
	drawing,
	locale,
	busy,
	invalidField,
	error,
	confirm,
	submit,
}: {
	drawing: MapRingDraft;
	locale: string;
	busy: boolean;
	invalidField: string | null;
	error: string | null;
	confirm: (confirmed: boolean) => void;
	submit: () => void;
}) {
	const { form, result } = useMapPropertyFeedback(error, invalidField),
		errorId = useId();
	const { name, source } = mapRingMetadata(drawing.before, drawing.target);
	return (
		<form
			ref={form}
			className="lp-drawing-properties lp-focus-target"
			id="lp-map-ring-properties"
			onSubmit={(event) => {
				event.preventDefault();
				submit();
			}}
		>
			<h3>{__("Boundary properties", "linker-tools")}</h3>
			<p>
				{name} · {mapRingLabel(drawing.target)}
			</p>
			<p>
				{__(
					"Drag a corner to move it, or use an edge midpoint to add a corner. The roof plane, other boundaries and recorded source details stay unchanged.",
					"linker-tools",
				)}
			</p>
			<dl className="lp-drawing-source">
				<dt>{__("Measurement or drawing reference", "linker-tools")}</dt>
				<dd>{source.note}</dd>
				<dt>{__("Declared spatial precision (m)", "linker-tools")}</dt>
				<dd>
					{source.spatial_precision_m === null
						? __("Unknown", "linker-tools")
						: formatDecimal(source.spatial_precision_m, locale)}
				</dd>
				<dt>{__("Calibration and measurement conditions", "linker-tools")}</dt>
				<dd>{source.calibration_note}</dd>
				<dt>{__("Basis for using these measurements", "linker-tools")}</dt>
				<dd>{source.rights_note}</dd>
				<dt>{__("Permission to export geometry", "linker-tools")}</dt>
				<dd>
					{source.permissions.export === "permitted"
						? __("Permitted", "linker-tools")
						: source.permissions.export === "prohibited"
							? __("Prohibited", "linker-tools")
							: __("Unknown", "linker-tools")}
				</dd>
			</dl>
			<fieldset disabled={busy}>
				<label className="lp-geometry-check">
					<input
						name="source_confirmed"
						type="checkbox"
						checked={drawing.source_confirmed}
						onChange={(event) => confirm(event.currentTarget.checked)}
						required
						aria-invalid={invalidField === "source_confirmed" || undefined}
						aria-describedby={
							invalidField === "source_confirmed" ? errorId : undefined
						}
					/>
					{__(
						"I have checked that the recorded source and permissions cover these boundary edits.",
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
						{__("Check and apply changes", "linker-tools")}
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
