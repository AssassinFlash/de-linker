import type MapViewport from "../components/design/MapViewport.tsx";
import { retryableModule } from "./retryableModule.ts";

const loadViewport = retryableModule<{ default: typeof MapViewport }>(
	() => import("../components/design/MapViewport.tsx"),
);

let stylesheet: Promise<void> | undefined;

function loadStyles(url: string): Promise<void> {
	if (!stylesheet) {
		stylesheet = new Promise<void>((resolve, reject) => {
			const link = document.createElement("link");
			link.rel = "stylesheet";
			link.href = url;
			link.onload = () => resolve();
			link.onerror = () => {
				stylesheet = undefined;
				link.remove();
				reject(new Error("map_stylesheet_unavailable"));
			};
			document.head.append(link);
		});
	}
	return stylesheet;
}

export async function loadMapModule(
	moduleUrl: string | null,
	styleUrl: string | null,
) {
	const [module] = await Promise.all([
		loadViewport(moduleUrl),
		styleUrl && loadStyles(styleUrl),
	]);
	return module;
}
