/** Thin lifecycle adapters around the version-locked official Three controls.
 * Avoids pulling unrelated three-stdlib VR/loader declaration conflicts into TS6.
 * No camera or temporary control state is persisted as project geometry. */
import { useEffect, useRef } from "react";
import type { RefObject } from "react";
import { useThree } from "@react-three/fiber";
import { TransformControls } from "three/addons/controls/TransformControls.js";
import type { Group } from "three";

export function ArrayTransform({
	object,
	frame,
	start,
	finish,
	cancel,
}: {
	object: RefObject<Group>;
	frame: string;
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
			// Selection, form opening, changed frame and unmount all cancel a
			// preview before its controller disappears. Never leave an unrecorded
			// transform on the still-mounted model group.
			abort();
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
	}, [object, frame, camera, gl, scene, invalidate]);
	return null;
}
