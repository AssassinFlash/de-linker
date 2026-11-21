import {
	clearRoofImageryConsent,
	onMapConsentChange,
} from "./data/roofImageryConsent.ts";
import { Component, StrictMode, useMemo } from "react";
import type { ErrorInfo, ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { readConfiguration } from "./data/config.ts";
import type { Configuration } from "./data/config.ts";
import { PlannerClient } from "./data/PlannerClient.ts";
import { DraftStore } from "./data/DraftStore.ts";
import { SessionBoundary } from "./components/SessionBoundary.tsx";
import { Workspace } from "./components/Workspace.tsx";
import { HomepageComparison } from "./components/HomepageComparison.tsx";
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
				<div className="sc-session-state" role="alert">
					<p>
						{__(
							"The workspace could not be displayed. Saved projects are unchanged.",
							"linker-tools",
						)}
					</p>
					<button
						className="sc-button sc-primary"
						onClick={() => location.reload()}
					>
						{__("Reload workspace", "linker-tools")}
					</button>
				</div>
			);
		return this.props.children;
	}
}
function Application({
	config,
	homepage,
}: {
	config: Configuration;
	homepage: URL | null;
}) {
	const client = useMemo(
		() => new PlannerClient({ ...config, origin: location.origin }),
		[config],
	);
	const store = useMemo(() => new DraftStore(), []);
	return (
		<SessionBoundary client={client}>
			{(session, recheck) =>
				homepage ? (
					<HomepageComparison
						key={session.query_scope}
						client={client}
						store={store}
						config={config}
						session={session}
						target={homepage}
						recheck={recheck}
					/>
				) : (
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
				)
			}
		</SessionBoundary>
	);
}
async function mount(): Promise<void> {
	onMapConsentChange(clearRoofImageryConsent);
	// The first render must see the full catalog (or its bounded failure, which
	// leaves the inline shell subset in place); rendering earlier paints the
	// untranslated form and nothing re-renders when the catalog arrives.
	await window.linkerToolsCatalog;
	for (const element of document.querySelectorAll<HTMLElement>(
		"[data-linker-planner]",
	)) {
		try {
			const config = readConfiguration(element, import.meta.url);
			const homepage = element.dataset.plannerHomeUrl
				? new URL(element.dataset.plannerHomeUrl, element.baseURI)
				: null;
			if (
				homepage &&
				(homepage.origin !== location.origin ||
					homepage.username ||
					homepage.password)
			)
				throw new Error("invalid_homepage_comparison_target");
			createRoot(element).render(
				<StrictMode>
					<ApplicationBoundary>
						<Application config={config} homepage={homepage} />
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
}

void mount();
