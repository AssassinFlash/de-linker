import type MapViewport from "../components/design/MapViewport.tsx";
import { retryableModule } from "./retryableModule.ts";

export const loadMapModule = retryableModule<{ default: typeof MapViewport }>(
	() => import("../components/design/MapViewport.tsx"),
);
