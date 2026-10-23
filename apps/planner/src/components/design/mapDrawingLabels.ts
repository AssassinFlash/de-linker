import type { MapDrawingDraft } from "../../domain/mapDrawingDraft.ts";
import type { MapRingTarget } from "../../domain/mapDrawingGeometry.ts";
import { mapRingMetadata } from "../../domain/mapDrawingGeometry.ts";
import { __, sprintf } from "../../i18n.ts";

export function mapRingLabel(target: MapRingTarget): string {
	switch (target.kind) {
		case "roof_boundary":
			return __("Roof boundary", "linker-tools");
		case "roof_hole":
			return sprintf(__("Opening %d", "linker-tools"), target.index + 1);
		case "obstacle":
			return __("Obstacle footprint", "linker-tools");
		case "keepout":
			return __("Keep-out boundary", "linker-tools");
	}
}
export function mapDrawingName(drawing: MapDrawingDraft): string {
	if (drawing.schema_version === 1)
		return drawing.fields.name || __("Unfinished roof drawing", "linker-tools");
	return (
		mapRingMetadata(drawing.before, drawing.target).name +
		" · " +
		mapRingLabel(drawing.target)
	);
}
