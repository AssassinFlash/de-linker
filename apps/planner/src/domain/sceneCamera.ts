/** Camera presentation only; these choices never alter saved geometry or fit. */
import type { GeometryDocument, Vec3 } from "./geometry.ts";
import { add, cross, scale, toRender } from "./coordinates.ts";

// Internal display policy: retain the existing 75-degree perspective lens and
// leave 10% distance margin around the scene's enclosing sphere.
export const SCENE_FOV_DEG = 75;
const FIT_MARGIN = 1.1;

/** Face the selected object's roof instead of looking almost along its plane.
 * The normal, a 0.5 U-axis offset and 0.75 project-Up offset are composition
 * weights, not dimensions or engineering assumptions. */
export function sceneViewDirection(
	document: GeometryDocument,
	selected: string | null,
): Vec3 {
	const child = [
		...document.arrays,
		...document.obstacles,
		...document.keepouts,
	].find((item) => item.id === selected);
	const roof =
		document.roofs.find((item) => item.id === (child?.roof_id ?? selected)) ??
		document.roofs[0];
	if (!roof) throw new Error("scene_has_no_roof");
	const normal = cross(roof.u_axis_enu, roof.v_axis_enu),
		direction = toRender(
			add(add(normal, scale(roof.u_axis_enu, 0.5)), [0, 0, 0.75]),
		),
		length = Math.hypot(...direction);
	if (!Number.isFinite(length) || length === 0)
		throw new Error("scene_invalid_view_direction");
	return scale(direction, 1 / length);
}

/** Enclosing-sphere perspective fit, using the smaller horizontal/vertical
 * half field of view; a narrow phone viewport must not crop the scene width. */
export function sceneFitDistance(radius: number, aspect: number): number {
	if (![radius, aspect].every((value) => Number.isFinite(value) && value > 0))
		throw new Error("scene_invalid_viewport");
	const vertical = (SCENE_FOV_DEG * Math.PI) / 360,
		horizontal = Math.atan(Math.tan(vertical) * aspect);
	return (radius / Math.sin(Math.min(vertical, horizontal))) * FIT_MARGIN;
}
