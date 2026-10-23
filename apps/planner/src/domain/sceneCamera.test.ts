import assert from "node:assert/strict";
import { test } from "node:test";
import { Box3, PerspectiveCamera, Vector3 } from "three/webgpu";
import flat from "../../../../fixtures/planning/geometry-flat.json" with { type: "json" };
import policy from "../contracts/geometry-policy.json" with { type: "json" };
import { readGeometry } from "./validateGeometry.ts";
import { roofPlane } from "./geometryEditing.ts";
import { add, cross, dot, scale, toRender } from "./coordinates.ts";
import { panelPoses } from "./panelPoses.ts";
import { renderBoundsPoints } from "./renderGeometry.ts";
import {
	SCENE_FOV_DEG,
	sceneFitDistance,
	sceneViewDirection,
} from "./sceneCamera.ts";

test("initial roof view remains above and faces flat/steep roofs in every bearing without editing geometry", () => {
	const original = readGeometry(structuredClone(flat), policy);
	for (const pitch of [0, 36.86989764584402, 60, 89.9])
		for (const bearing of [0, 90, 180, 270]) {
			const plane = {
				...original.roofs[0]!,
				...roofPlane(pitch, bearing, [0, 0, 5]),
			};
			for (const angle of [0, Math.PI / 2, Math.PI, (3 * Math.PI) / 2]) {
				const roof = {
						...plane,
						u_axis_enu: add(
							scale(plane.u_axis_enu, Math.cos(angle)),
							scale(plane.v_axis_enu, Math.sin(angle)),
						),
						v_axis_enu: add(
							scale(plane.u_axis_enu, -Math.sin(angle)),
							scale(plane.v_axis_enu, Math.cos(angle)),
						),
					},
					document = { ...original, roofs: [roof] },
					before = JSON.stringify(document),
					direction = sceneViewDirection(document, null),
					normal = toRender(cross(roof.u_axis_enu, roof.v_axis_enu));
				assert.ok(
					direction[1] > 0,
					"camera starts above the project height datum",
				);
				assert.ok(dot(direction, normal) > 0.5, "roof must not start edge-on");
				assert.ok(Math.abs(Math.hypot(...direction) - 1) < 1e-14);
				assert.equal(JSON.stringify(document), before);
			}
		}
});

test("explicit framing follows the selected child's roof while retaining every scene extent", () => {
	const original = readGeometry(structuredClone(flat), policy),
		second = {
			...original.roofs[0]!,
			id: "second",
			...roofPlane(60, 180, [0, 0, 10]),
		},
		array = { ...original.arrays[0]!, roof_id: second.id },
		document = {
			...original,
			roofs: [...original.roofs, second],
			arrays: [array],
		};
	assert.deepEqual(
		sceneViewDirection(document, array.id),
		sceneViewDirection(document, second.id),
	);
	const points = renderBoundsPoints(
			document,
			panelPoses(document),
			original.roofs[0]!.origin_enu,
		).map((point) => new Vector3(...point)),
		box = new Box3().setFromPoints(points),
		centre = box.getCenter(new Vector3()),
		radius = box.getSize(new Vector3()).length() / 2,
		direction = new Vector3(...sceneViewDirection(document, array.id));
	for (const aspect of [0.3, 0.65, 1, 1.8, 3]) {
		const distance = sceneFitDistance(radius, aspect),
			camera = new PerspectiveCamera(
				SCENE_FOV_DEG,
				aspect,
				0.001,
				distance + 3 * radius,
			);
		camera.position.copy(centre).addScaledVector(direction, distance);
		camera.lookAt(centre);
		camera.updateMatrixWorld();
		for (const point of points) {
			const ndc = point.clone().project(camera);
			assert.ok(
				Math.abs(ndc.x) < 1 && Math.abs(ndc.y) < 1 && Math.abs(ndc.z) < 1,
				`actual point must fit the ${aspect} aspect viewport`,
			);
		}
	}
	for (const aspect of [0, -1, Infinity, NaN])
		assert.throws(() => sceneFitDistance(radius, aspect));
});
