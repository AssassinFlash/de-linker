import { useLayoutEffect, useRef } from "react";
import { useThree } from "@react-three/fiber";
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
	framing,
	request,
}: {
	framing: SceneFraming;
	request: number;
}) {
	const { camera, size, invalidate } = useThree();
	const previous = useRef<{ framing: SceneFraming; request: number } | null>(
		null,
	);
	useLayoutEffect(() => {
		const perspective = camera as PerspectiveCamera;
		if (!perspective.isPerspectiveCamera || size.width <= 0 || size.height <= 0)
			return;
		const preserveDirection =
			previous.current?.framing === framing &&
			previous.current.request === request;
		const direction = preserveDirection
			? camera.getWorldDirection(new Vector3()).negate()
			: new Vector3(...framing.direction);
		const radius = framing.size / 2,
			distance = sceneFitDistance(radius, size.width / size.height);
		perspective.aspect = size.width / size.height;
		perspective.position
			.copy(framing.centre)
			.addScaledVector(direction, distance);
		// Display clipping policy scales with the scene instead of imposing a
		// metre-based minimum that would hide a small but supported drawing.
		perspective.near = radius / 10000;
		perspective.far = distance + radius * 3;
		perspective.lookAt(framing.centre);
		perspective.updateProjectionMatrix();
		previous.current = { framing, request };
		invalidate();
	}, [camera, framing, request, size.width, size.height, invalidate]);
	return null;
}
