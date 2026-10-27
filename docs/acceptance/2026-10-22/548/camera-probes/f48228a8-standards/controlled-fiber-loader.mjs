// Test boundary only: real React, SceneViewport, SceneCamera and Three math;
// controlled useThree/Canvas without claiming a native renderer/GPU result.
export async function resolve(specifier, context, nextResolve) {
  if (specifier === "@react-three/fiber") {
    return { url: new URL("./controlled-fiber.mjs", import.meta.url).href, shortCircuit: true };
  }
  return nextResolve(specifier, context);
}
