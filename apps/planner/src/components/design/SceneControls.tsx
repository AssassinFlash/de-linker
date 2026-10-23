/** Thin lifecycle adapters around the version-locked official Three controls.
 * Avoids pulling unrelated three-stdlib VR/loader declaration conflicts into TS6.
 * No camera or temporary control state is persisted as project geometry. */
import { useEffect, useRef } from "react";
import type { RefObject } from "react";
import { useThree } from "@react-three/fiber";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { TransformControls } from "three/addons/controls/TransformControls.js";
import type { Group, Vector3 } from "three";

export function OrbitController({ target }: { target: Vector3 }) {
	const { camera, gl, invalidate } = useThree();
	const orbit = useRef<OrbitControls | null>(null);
	// Construct on effect, so StrictMode's mount/dispose cycle never reuses disposed resources.
	useEffect(() => {
		const controls = new OrbitControls(camera, gl.domElement);
		orbit.current = controls;
		controls.target.copy(target);
		controls.update();
		const changed = () => invalidate();
		controls.addEventListener("change", changed);
		const pause = () => {
				controls.enabled = false;
			},
			resume = () => {
				controls.enabled = true;
			};
		gl.domElement.addEventListener("planner-transform-start", pause);
		gl.domElement.addEventListener("planner-transform-end", resume);
		return () => {
			controls.removeEventListener("change", changed);
			gl.domElement.removeEventListener("planner-transform-start", pause);
			gl.domElement.removeEventListener("planner-transform-end", resume);
			controls.dispose();
			orbit.current = null;
		};
	}, [camera, gl, invalidate, target]);
	return null;
}

export function ArrayTransform({
	object,
	start,
	finish,
	cancel,
}: {
	object: RefObject<Group>;
	start: () => void;
	finish: () => void;
	cancel: () => void;
}) {
	const { camera, gl, scene, invalidate } = useThree();
	const handlers = useRef({ start, finish, cancel });
	handlers.current = { start, finish, cancel };
	useEffect(() => {
		const controls = new TransformControls(camera, gl.domElement);
		controls.setMode("translate");
		controls.setSpace("local");
		controls.showZ = false;
		controls.attach(object.current);
		const helper = controls.getHelper();
		scene.add(helper);
		const begin = () => {
			gl.domElement.dispatchEvent(new Event("planner-transform-start"));
			handlers.current.start();
		};
		let cancelling = false;
		const end = () => {
			if (!cancelling) handlers.current.finish();
			gl.domElement.dispatchEvent(new Event("planner-transform-end"));
		};
		const abort = () => {
			if (!controls.dragging) return;
			controls.reset();
			cancelling = true;
			controls.pointerUp(null);
			cancelling = false;
			handlers.current.cancel();
			gl.domElement.dispatchEvent(new Event("planner-transform-end"));
			controls.disconnect();
			controls.connect(gl.domElement);
			invalidate();
		};
		const escape = (event: KeyboardEvent) => {
			if (event.key === "Escape") abort();
		};
		const changed = () => invalidate();
		controls.addEventListener("change", changed);
		controls.addEventListener("mouseDown", begin);
		controls.addEventListener("mouseUp", end);
		window.addEventListener("keydown", escape);
		window.addEventListener("blur", abort);
		gl.domElement.addEventListener("pointercancel", abort);
		gl.domElement.addEventListener("lostpointercapture", abort);
		return () => {
			controls.removeEventListener("change", changed);
			controls.removeEventListener("mouseDown", begin);
			controls.removeEventListener("mouseUp", end);
			window.removeEventListener("keydown", escape);
			window.removeEventListener("blur", abort);
			gl.domElement.removeEventListener("pointercancel", abort);
			gl.domElement.removeEventListener("lostpointercapture", abort);
			controls.detach();
			scene.remove(helper);
			controls.dispose();
			gl.domElement.dispatchEvent(new Event("planner-transform-end"));
		};
	}, [object, camera, gl, scene, invalidate]);
	return null;
}
