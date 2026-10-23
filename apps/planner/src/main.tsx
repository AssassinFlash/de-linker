import { Component, StrictMode, useMemo } from "react";
import type { ErrorInfo, ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { readConfiguration } from "./data/config.ts";
import type { Configuration } from "./data/config.ts";
import { PlannerClient } from "./data/PlannerClient.ts";
import { DraftStore } from "./data/DraftStore.ts";
import { SessionBoundary } from "./components/SessionBoundary.tsx";
import { Workspace } from "./components/Workspace.tsx";
import { ToolIdentity } from "./components/ToolIdentity.tsx";
import { __ } from "./i18n.ts";

class ApplicationBoundary extends Component<
	{ children: ReactNode },
	{ failed: boolean }
> {
	override state = { failed: false };
	static getDerivedStateFromError() {
		return { failed: true };
	}
	override componentDidCatch(_error: Error, _info: ErrorInfo): void {
		/* Private inputs are never written to the console. */
	}
	override render() {
		if (this.state.failed)
			return (
				<div className="lp-session-state" role="alert">
					<p>
						{__(
							"The workspace could not be displayed. Saved projects are unchanged.",
							"linker-tools",
						)}
					</p>
					<button className="lp-button" onClick={() => location.reload()}>
						{__("Reload workspace", "linker-tools")}
					</button>
				</div>
			);
		return this.props.children;
	}
}
function Application({ config }: { config: Configuration }) {
	const client = useMemo(
		() => new PlannerClient({ ...config, origin: location.origin }),
		[config],
	);
	const store = useMemo(() => new DraftStore(), []);
	return (
		<SessionBoundary client={client}>
			{(session, recheck) => (
				<>
					<Workspace
						key={session.query_scope}
						client={client}
						store={store}
						config={config}
						session={session}
						recheck={recheck}
					/>
					<ToolIdentity />
				</>
			)}
		</SessionBoundary>
	);
}
for (const element of document.querySelectorAll<HTMLElement>(
	"[data-linker-planner]",
)) {
	try {
		const config = readConfiguration(element, import.meta.url);
		createRoot(element).render(
			<StrictMode>
				<ApplicationBoundary>
					<Application config={config} />
				</ApplicationBoundary>
			</StrictMode>,
		);
	} catch {
		element.setAttribute("role", "alert");
		element.textContent = __(
			"The workspace could not be displayed. Saved projects are unchanged.",
			"linker-tools",
		);
	}
}
