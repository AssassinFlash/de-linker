import { useState } from "react";
import type { GeometryDocument } from "../../domain/geometry.ts";
import type { MapRingTarget } from "../../domain/mapDrawingGeometry.ts";
import { mapRingMetadata } from "../../domain/mapDrawingGeometry.ts";
import { mapRingTargets } from "../../domain/mapRingDraft.ts";
import { mapRingLabel } from "./mapDrawingLabels.ts";
import { __ } from "../../i18n.ts";

export function MapRingSelector({
	geometry,
	selected,
	disabled,
	begin,
}: {
	geometry: GeometryDocument;
	selected: string | null;
	disabled: boolean;
	begin: (target: MapRingTarget) => void;
}) {
	const options = mapRingTargets(geometry, selected);
	const [selection, setSelection] = useState({ object: selected, index: 0 });
	const at = selection.object === selected ? selection.index : 0;
	const target = options[at] ?? options[0];
	if (!target)
		return (
			<p className="lp-profile-help">
				{__(
					"Select a roof face, obstacle or keep-out area on the map or in the object list. For a roof face, choose its outer boundary or an existing opening.",
					"linker-tools",
				)}
			</p>
		);
	return (
		<div className="lp-map-ring-selector">
			<p>{mapRingMetadata(geometry, target).name}</p>
			<div className="lp-inline-actions">
				<label className="lp-field">
					<span>{__("Boundary to edit", "linker-tools")}</span>
					<select
						value={String(options.indexOf(target))}
						disabled={disabled}
						onChange={(event) =>
							setSelection({
								object: selected,
								index: Number(event.currentTarget.value),
							})
						}
					>
						{options.map((value, index) => (
							<option key={index} value={String(index)}>
								{mapRingLabel(value)}
							</option>
						))}
					</select>
				</label>
				<button
					type="button"
					className="lp-button lp-button-secondary"
					disabled={disabled}
					onClick={() => begin(target)}
				>
					{__("Edit boundary on map", "linker-tools")}
				</button>
			</div>
		</div>
	);
}
