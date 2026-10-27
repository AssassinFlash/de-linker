import { Children, createElement, useEffect } from "react";
export const useThree = () => globalThis.__cameraProbe.state;
export function Canvas({ children, ...props }) {
  const fixture = globalThis.__cameraProbe;
  fixture.canvasProps = props;
  useEffect(() => {
    fixture.mounts++;
    return () => { fixture.unmounts++; };
  }, []);
  const camera = Children.toArray(children).find(child => child?.type?.name === "SceneCamera");
  if (!camera) throw new Error("Actual SceneCamera child missing");
  fixture.framing = camera.props.framing;
  return createElement("div", { "data-controlled-canvas": true }, camera);
}
