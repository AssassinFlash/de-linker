# Controlled camera harness

Attempt1 supplied a vanilla Zustand StoreApi object to the real R3F context. The installed real `useThree` expects a callable bound store hook, so all component checks failed before valid camera execution. Corrected only the host to use installed Zustand `create`, preserving real R3F `context/useThree`. The original host, full log and SHA metadata are retained. No implementation source changed.

Canvas/GPU drawing is controlled; the actual SceneViewport, SceneCamera, OrbitController, RendererLifecycle, Three camera math and renderer-factory ownership callback execute. Real R3F selectors consume the bound store. This does not claim native GPU or browser viewport acceptance.
