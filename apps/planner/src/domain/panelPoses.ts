import { requireUvResolution } from "./geometryNumerics.ts";
import {
	add,
	cross,
	scale,
	sinCosDegrees,
	vectorFromRoof,
} from "./coordinates.ts";
import type {
	GeometryDocument,
	PanelPose,
	RoofFace,
	Vec3,
} from "./geometry.ts";

/** Stable array/row/column identities; excluded slots remain editable objects. */
export const slotKey = (row: number, column: number): string =>
	`${row}:${column}`;
export const panelId = (arrayId: string, row: number, column: number): string =>
	`${arrayId}:${slotKey(row, column)}`;

/** The same full cuboid used by server plan-fit review, including thickness. */
export function panelCorners(pose: PanelPose): readonly Vec3[] {
	return [-1, 1].flatMap((u) =>
		[-1, 1].flatMap((v) =>
			[-1, 1].map((n) =>
				add(
					pose.centre_enu,
					add(
						scale(pose.u_axis_enu, (u * pose.width_m) / 2),
						add(
							scale(pose.v_axis_enu, (v * pose.length_m) / 2),
							scale(pose.normal_enu, (n * pose.thickness_m) / 2),
						),
					),
				),
			),
		),
	);
}

/** Euclidean placement only. Fit, structural and electrical release are separate. */
export function panelPoses(document: GeometryDocument): readonly PanelPose[] {
	const roofs = new Map(document.roofs.map((roof) => [roof.id, roof]));
	const specs = new Map(document.module_specs.map((spec) => [spec.id, spec]));
	return document.arrays.flatMap((array) => {
		const roof = roofs.get(array.roof_id);
		const spec = specs.get(array.module_spec_id);
		if (!roof || !spec) throw new Error("geometry_reference_missing");
		const [sinAngle, cosAngle] = sinCosDegrees(array.rotation_deg);
		const [sinTilt, cosTilt] = sinCosDegrees(array.mount_tilt_deg);
		const localU: Vec3 = [cosAngle, sinAngle, 0];
		const localV: Vec3 = [-sinAngle * cosTilt, cosAngle * cosTilt, sinTilt];
		const localNormal = cross(localU, localV);
		const u = vectorFromRoof(roof, localU);
		const v = vectorFromRoof(roof, localV);
		const normal = vectorFromRoof(roof, localNormal);
		const excluded = new Set(array.excluded_slots);
		const poses: PanelPose[] = [];
		for (let row = 0; row < array.rows; row++) {
			for (let column = 0; column < array.columns; column++) {
				// Each row resets at its own lower edge. A whole sloped grid would
				// incorrectly raise every successive row on a flat mounting surface.
				const x =
					column * (spec.width_m + array.column_gap_m) + spec.width_m / 2;
				const y =
					row * (spec.length_m * cosTilt + array.row_gap_m) +
					(spec.length_m * cosTilt) / 2;
				const z = array.lower_edge_clearance_m + (spec.length_m * sinTilt) / 2;
				const centreUVN = add(
					[
						array.origin_uv[0] + x * cosAngle - y * sinAngle,
						array.origin_uv[1] + x * sinAngle + y * cosAngle,
						z,
					],
					scale(localNormal, spec.thickness_m / 2),
				);
				const centre = add(roof.origin_enu, vectorFromRoof(roof, centreUVN));
				poses.push({
					id: panelId(array.id, row, column),
					array_id: array.id,
					roof_id: roof.id,
					row,
					column,
					included: !excluded.has(slotKey(row, column)),
					centre_uvn: centreUVN,
					u_axis_uvn: localU,
					v_axis_uvn: localV,
					normal_uvn: localNormal,
					centre_enu: centre,
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

/** Rebase before adding local offsets, preserving detail at large ENU origins. */
export function panelPositionRelative(
	pose: PanelPose,
	roof: RoofFace,
	reference: Vec3,
): Vec3 {
	requireUvResolution(pose.centre_uvn);
	return add(
		add(roof.origin_enu, scale(reference, -1)),
		vectorFromRoof(roof, pose.centre_uvn),
	);
}

export function panelCornersUVN(pose: PanelPose): readonly Vec3[] {
	return panelCorners({
		...pose,
		centre_enu: pose.centre_uvn,
		u_axis_enu: pose.u_axis_uvn,
		v_axis_enu: pose.v_axis_uvn,
		normal_enu: pose.normal_uvn,
	});
}
