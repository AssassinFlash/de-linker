import type SceneViewport from "../components/design/SceneViewport.tsx";
import { retryableModule } from "./retryableModule.ts";

export const loadSceneModule = retryableModule<{
	default: typeof SceneViewport;
}>(() => import("../components/design/SceneViewport.tsx"));
