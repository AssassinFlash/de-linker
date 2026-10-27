// Adapted host for the new owned OrbitControls lifecycle. React, application,
// Three projection and the installed official controls remain real. No GPU.
import { Children, createElement, useEffect } from "react";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
const update = OrbitControls.prototype.update;
const dispose = OrbitControls.prototype.dispose;
OrbitControls.prototype.update = function (...args) {
  const fixture = globalThis.__cameraProbe;
  if (fixture) (fixture.orbits ??= new Set()).add(this);
  return update.apply(this, args);
};
OrbitControls.prototype.dispose = function (...args) {
  const fixture = globalThis.__cameraProbe;
  if (fixture) (fixture.disposed ??= new Set()).add(this);
  return dispose.apply(this, args);
};
export const useThree = () => globalThis.__cameraProbe.state;
export function Canvas({ children, ...props }) {
  const fixture = globalThis.__cameraProbe;
  fixture.canvasProps = props;
  if (!fixture.state.gl) {
    const canvas = document.createElement("canvas");
    document.body.append(canvas);
    fixture.plannerListeners = new Map();
    const add = canvas.addEventListener.bind(canvas), remove = canvas.removeEventListener.bind(canvas);
    canvas.addEventListener = (name, listener, ...args) => {
      if (name.startsWith("planner-")) {
        if (!fixture.plannerListeners.has(name)) fixture.plannerListeners.set(name, new Set());
        fixture.plannerListeners.get(name).add(listener);
      }
      return add(name, listener, ...args);
    };
    canvas.removeEventListener = (name, listener, ...args) => {
      fixture.plannerListeners.get(name)?.delete(listener);
      return remove(name, listener, ...args);
    };
    fixture.state.gl = { domElement: canvas };
  }
  useEffect(() => {
    fixture.mounts++;
    return () => { fixture.unmounts++; };
  }, []);
  const camera = Children.toArray(children).find(child => child?.type?.name === "SceneCamera");
  if (!camera) throw new Error("Actual SceneCamera child missing");
  // Only host adaptation: new prop is extent. Original test assertions remain
  // byte-identical and receive the currently mounted camera aggregate.
  fixture.framing = camera.props.framing ?? camera.props.extent;
  return createElement("div", { "data-controlled-canvas": true }, camera);
}
