import { add, cross, pointOnRoof, scale } from "./coordinates.ts";
import type { GeometryDocument, PanelPose } from "./geometry.ts";

/** Stable array/row/column identities; excluded slots remain editable objects. */
export const slotKey = (row: number, column: number): string =>
	`${row}:${column}`;
export const panelId = (arrayId: string, row: number, column: number): string =>
	`${arrayId}:${slotKey(row, column)}`;

/** Euclidean placement only. Fit, structural and electrical release are separate. */
export function panelPoses(document: GeometryDocument): readonly PanelPose[] {
	const roofs = new Map(document.roofs.map((roof) => [roof.id, roof]));
	const specs = new Map(document.module_specs.map((spec) => [spec.id, spec]));
	return document.arrays.flatMap((array) => {
		const roof = roofs.get(array.roof_id);
		const spec = specs.get(array.module_spec_id);
		if (!roof || !spec) throw new Error("geometry_reference_missing");
		const angle = (array.rotation_deg * Math.PI) / 180;
		const tilt = (array.mount_tilt_deg * Math.PI) / 180;
		const roofNormal = cross(roof.u_axis_enu, roof.v_axis_enu);
		const u = add(
			scale(roof.u_axis_enu, Math.cos(angle)),
			scale(roof.v_axis_enu, Math.sin(angle)),
		);
		const rowAxis = add(
			scale(roof.u_axis_enu, -Math.sin(angle)),
			scale(roof.v_axis_enu, Math.cos(angle)),
		);
		const v = add(
			scale(rowAxis, Math.cos(tilt)),
			scale(roofNormal, Math.sin(tilt)),
		);
		const normal = cross(u, v);
		const origin = pointOnRoof(roof, array.origin_uv);
		const excluded = new Set(array.excluded_slots);
		const poses: PanelPose[] = [];
		for (let row = 0; row < array.rows; row++) {
			for (let column = 0; column < array.columns; column++) {
				// Each row resets at its own lower edge. A whole sloped grid would
				// incorrectly raise every successive row on a flat mounting surface.
				const x =
					column * (spec.width_m + array.column_gap_m) + spec.width_m / 2;
				const y =
					row * (spec.length_m * Math.cos(tilt) + array.row_gap_m) +
					(spec.length_m * Math.cos(tilt)) / 2;
				const z =
					array.lower_edge_clearance_m + (spec.length_m * Math.sin(tilt)) / 2;
				const centre = add(
					origin,
					add(scale(u, x), add(scale(rowAxis, y), scale(roofNormal, z))),
				);
				poses.push({
					id: panelId(array.id, row, column),
					array_id: array.id,
					row,
					column,
					included: !excluded.has(slotKey(row, column)),
					centre_enu: add(centre, scale(normal, spec.thickness_m / 2)),
					u_axis_enu: u,
					v_axis_enu: v,
					normal_enu: normal,
					width_m: spec.width_m,
					length_m: spec.length_m,
					thickness_m: spec.thickness_m,
					stc_power_w: spec.stc_power_w,
				});
			}
		}
		return poses;
	});
}

export function moduleSummary(document: GeometryDocument): {
	count: number;
	stc_kwp: number;
} {
	const active = panelPoses(document).filter((pose) => pose.included);
	return {
		count: active.length,
		stc_kwp: active.reduce((sum, pose) => sum + pose.stc_power_w, 0) / 1000,
	};
}
