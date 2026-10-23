import { lazy, Suspense, useMemo, useState } from "react";
import type { ComponentProps } from "react";
import type MapViewport from "./MapViewport.tsx";
import { __ } from "../../i18n.ts";
import { loadMapModule } from "../../data/mapModule.ts";
import { ViewportBoundary } from "./ViewportBoundary.tsx";

export function LazyMapViewport({
	mapModuleUrl,
	...props
}: ComponentProps<typeof MapViewport> & { mapModuleUrl: string | null }) {
	const [attempt, setAttempt] = useState(0);
	const View = useMemo(
		() => lazy(() => loadMapModule(mapModuleUrl)),
		[attempt, mapModuleUrl],
	);
	return (
		<ViewportBoundary
			key={attempt}
			retry={() => setAttempt((value) => value + 1)}
			failure={__(
				"The map could not be loaded. You can still switch views or edit numeric properties.",
				"linker-tools",
			)}
			retryLabel={__("Retry loading map", "linker-tools")}
		>
			<Suspense
				fallback={<p role="status">{__("Loading map…", "linker-tools")}</p>}
			>
				<View {...props} />
			</Suspense>
		</ViewportBoundary>
	);
}
