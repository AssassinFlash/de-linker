import { lazy, Suspense, useMemo, useState } from "react";
import type { ComponentProps } from "react";
import type SceneViewport from "./SceneViewport.tsx";
import { __ } from "../../i18n.ts";
import { loadSceneModule } from "../../data/sceneModule.ts";
import { ViewportBoundary } from "./ViewportBoundary.tsx";

export function LazySceneViewport({
	sceneModuleUrl,
	...props
}: ComponentProps<typeof SceneViewport> & { sceneModuleUrl: string | null }) {
	const [attempt, setAttempt] = useState(0);
	const View = useMemo(
		() => lazy(() => loadSceneModule(sceneModuleUrl)),
		[attempt, sceneModuleUrl],
	);
	return (
		<ViewportBoundary
			key={attempt}
			retry={() => setAttempt((value) => value + 1)}
			failure={__(
				"The 3D workspace could not be loaded. Plan view and numeric properties remain available.",
				"linker-tools",
			)}
			retryLabel={__("Retry loading 3D", "linker-tools")}
		>
			<Suspense
				fallback={
					<p role="status">{__("Loading 3D workspace…", "linker-tools")}</p>
				}
			>
				<View {...props} />
			</Suspense>
		</ViewportBoundary>
	);
}
