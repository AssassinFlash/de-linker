import { useState } from "react";
import type { GeometryDocument } from "../../domain/geometry.ts";
import type { MapFeatureTarget } from "../../domain/mapFeatureDraft.ts";
import { mapFeatureLabel } from "./mapDrawingLabels.ts";
import { __ } from "../../i18n.ts";

export function MapFeatureSelector({
	geometry,
	selected,
	disabled,
	begin,
}: {
	geometry: GeometryDocument;
	selected: string | null;
	disabled: boolean;
	begin: (target: MapFeatureTarget) => void;
}) {
	const selectedRoof =
		geometry.roofs.find((roof) => roof.id === selected)?.id ??
		[...geometry.obstacles, ...geometry.keepouts, ...geometry.arrays].find(
			(object) => object.id === selected,
		)?.roof_id ??
		"";
	const [choice, setChoice] = useState({
		object: selected,
		roof: selectedRoof,
	});
	const [kind, setKind] = useState<MapFeatureTarget["kind"] | "">("");
	const roofId = choice.object === selected ? choice.roof : selectedRoof;
	if (!geometry.roofs.length) return null;
	return (
		<section
			className="lp-map-ring-selector"
			aria-label={__("Add a roof feature", "linker-tools")}
		>
			<h4>{__("Add a roof feature", "linker-tools")}</h4>
			<div className="lp-inline-actions">
				<label className="lp-field">
					<span>{__("Roof face", "linker-tools")}</span>
					<select
						value={roofId}
						disabled={disabled}
						onChange={(event) =>
							setChoice({ object: selected, roof: event.currentTarget.value })
						}
					>
						<option value="">{__("Select a roof face", "linker-tools")}</option>
						{geometry.roofs.map((roof) => (
							<option key={roof.id} value={roof.id}>
								{roof.name}
							</option>
						))}
					</select>
				</label>
				<label className="lp-field">
					<span>{__("Feature type", "linker-tools")}</span>
					<select
						value={kind}
						disabled={disabled}
						onChange={(event) =>
							setKind(event.currentTarget.value as typeof kind)
						}
					>
						<option value="">
							{__("Select a feature type", "linker-tools")}
						</option>
						{(["hole", "obstacle", "keepout"] as const).map((value) => (
							<option key={value} value={value}>
								{mapFeatureLabel(value)}
							</option>
						))}
					</select>
				</label>
				<button
					type="button"
					className="lp-button lp-button-secondary"
					disabled={
						disabled ||
						!kind ||
						!geometry.roofs.some((roof) => roof.id === roofId)
					}
					onClick={() => {
						if (kind) begin({ kind, roof_id: roofId });
					}}
				>
					{__("Draw a roof feature", "linker-tools")}
				</button>
			</div>
		</section>
	);
}
