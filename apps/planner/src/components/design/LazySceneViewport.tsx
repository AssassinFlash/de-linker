import { Component, lazy, Suspense, useMemo, useState } from "react";
import type { ComponentProps, ReactNode } from "react";
import type SceneViewport from "./SceneViewport.tsx";
import { __ } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";
import { loadSceneModule } from "../../data/sceneModule.ts";

class ChunkBoundary extends Component<
	{ children: ReactNode; retry: () => void },
	{ failed: boolean }
> {
	state = { failed: false };
	static getDerivedStateFromError() {
		return { failed: true };
	}
	render() {
		return this.state.failed ? (
			<Notice error>
				<p>
					{__(
						"The 3D workspace could not be loaded. Plan view and numeric properties remain available.",
						"linker-tools",
					)}
				</p>
				<button
					type="button"
					className="lp-button lp-button-secondary"
					onClick={this.props.retry}
				>
					{__("Retry loading 3D", "linker-tools")}
				</button>
			</Notice>
		) : (
			this.props.children
		);
	}
}

/** This boundary lives outside the chunk that can fail to download. */
export function LazySceneViewport({
	sceneModuleUrl,
	...props
}: ComponentProps<typeof SceneViewport> & { sceneModuleUrl: string | null }) {
	const [attempt, setAttempt] = useState(0);
	const Scene = useMemo(
		() => lazy(() => loadSceneModule(sceneModuleUrl)),
		[attempt, sceneModuleUrl],
	);
	return (
		<ChunkBoundary key={attempt} retry={() => setAttempt((value) => value + 1)}>
			<Suspense
				fallback={
					<p role="status">{__("Loading 3D workspace…", "linker-tools")}</p>
				}
			>
				<Scene {...props} />
			</Suspense>
		</ChunkBoundary>
	);
}
