import type { GeometryDocument, PanelPose } from "./geometry.ts";
import { panelPoses } from "./panelPoses.ts";

/** Resolve the actual selected object; panel identities are opaque, never parsed.
 * A caller that already renders poses may reuse that same current snapshot. */
export function selectedRoofId(
	document: GeometryDocument,
	selected: string | null,
	poses: readonly PanelPose[] = panelPoses(document),
): string | null {
	if (selected === null) return null;
	const panel = poses.find((pose) => pose.id === selected);
	if (panel) return panel.roof_id;
	const object = [
		...document.roofs,
		...document.arrays,
		...document.obstacles,
		...document.keepouts,
	].find((item) => item.id === selected);
	return object ? ("roof_id" in object ? object.roof_id : object.id) : null;
}
