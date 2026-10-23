import { useLayoutEffect, useRef } from "react";
import { useThree } from "@react-three/fiber";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { Vector3 } from "three/webgpu";
import type { PerspectiveCamera } from "three";
import type { Vec3 } from "../../domain/geometry.ts";
import { sceneFitDistance } from "../../domain/sceneCamera.ts";

export interface SceneFraming {
	centre: Vector3;
	size: number;
	direction: Vec3;
}

/** Fit moves the existing camera, not the geometry or GPU renderer. Resizing
 * preserves the user's viewing direction while fitting the new aspect ratio. */
export function SceneCamera({
	extent,
	request,
}: {
	extent: SceneFraming;
	request: number;
}) {
	const { camera, gl, size, invalidate } = useThree();
	const orbit = useRef<OrbitControls | null>(null);
	const previous = useRef<{
		request: number;
		width: number;
		height: number;
	} | null>(null);
	useLayoutEffect(() => {
		const controls = new OrbitControls(camera, gl.domElement);
		orbit.current = controls;
		previous.current = null;
		const changed = () => invalidate(),
			pause = () => {
				controls.enabled = false;
			},
			resume = () => {
				controls.enabled = true;
			};
		controls.addEventListener("change", changed);
		gl.domElement.addEventListener("planner-transform-start", pause);
		gl.domElement.addEventListener("planner-transform-end", resume);
		return () => {
			controls.removeEventListener("change", changed);
			gl.domElement.removeEventListener("planner-transform-start", pause);
			gl.domElement.removeEventListener("planner-transform-end", resume);
			controls.dispose();
			orbit.current = null;
			previous.current = null;
		};
	}, [camera, gl, invalidate]);
	useLayoutEffect(() => {
		const perspective = camera as PerspectiveCamera;
		const controls = orbit.current;
		if (
			!controls ||
			!perspective.isPerspectiveCamera ||
			size.width <= 0 ||
			size.height <= 0
		)
			return;
		const resetDirection =
			!previous.current || previous.current.request !== request;
		const resized =
			previous.current?.width !== size.width ||
			previous.current.height !== size.height;
		// New geometry/selection alone must not move the user's view. When a
		// fit is requested or the viewport resizes, use the latest full extent.
		if (!resetDirection && !resized) return;
		const preserveDirection = !resetDirection;
		const direction = preserveDirection
			? camera.getWorldDirection(new Vector3()).negate()
			: new Vector3(...extent.direction);
		const radius = extent.size / 2,
			distance = sceneFitDistance(radius, size.width / size.height);
		perspective.aspect = size.width / size.height;
		perspective.position
			.copy(extent.centre)
			.addScaledVector(direction, distance);
		// Display clipping policy scales with the scene instead of imposing a
		// metre-based minimum that would hide a small but supported drawing.
		perspective.near = radius / 10000;
		perspective.far = distance + radius * 3;
		controls.target.copy(extent.centre);
		perspective.lookAt(extent.centre);
		perspective.updateProjectionMatrix();
		controls.update();
		previous.current = { request, width: size.width, height: size.height };
		invalidate();
	}, [camera, gl, extent, request, size.width, size.height, invalidate]);
	return null;
}
