import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { Session } from "../data/protocol.ts";
import type { PlannerClient } from "../data/PlannerClient.ts";
import { __ } from "../i18n.ts";
import { Notice } from "./Notice.tsx";

export function SessionBoundary({
	client,
	children,
}: {
	client: PlannerClient;
	children: (session: Session, recheck: () => void) => ReactNode;
}) {
	const cache = useMemo(
		() =>
			new QueryClient({
				defaultOptions: {
					queries: { retry: false, refetchOnWindowFocus: false },
					mutations: { retry: false },
				},
			}),
		[],
	);
	const [session, setSession] = useState<Session | null>(null);
	const [failed, setFailed] = useState(false);
	const [check, setCheck] = useState(0);
	const recheck = useCallback(() => {
		client.invalidate();
		setSession(null);
		setCheck((value) => value + 1);
	}, [client]);

	useEffect(() => {
		const controller = new AbortController();
		let active = true;
		client.invalidate();
		void cache.cancelQueries();
		cache.clear();
		setSession(null);
		setFailed(false);
		void client
			.bootstrap(controller.signal)
			.then((value) => {
				if (active) setSession(value);
			})
			.catch(() => {
				if (active && !controller.signal.aborted) setFailed(true);
			});
		return () => {
			active = false;
			controller.abort();
			client.invalidate();
			void cache.cancelQueries();
			cache.clear();
		};
	}, [cache, client, check]);

	useEffect(() => {
		const visible = () => {
			if (document.visibilityState === "visible") recheck();
		};
		const restored = (event: PageTransitionEvent) => {
			if (event.persisted) recheck();
		};
		window.addEventListener("focus", recheck);
		window.addEventListener("online", recheck);
		window.addEventListener("pageshow", restored);
		document.addEventListener("visibilitychange", visible);
		return () => {
			window.removeEventListener("focus", recheck);
			window.removeEventListener("online", recheck);
			window.removeEventListener("pageshow", restored);
			document.removeEventListener("visibilitychange", visible);
		};
	}, [recheck]);

	if (!session)
		return (
			<div className="lp-session-state">
				<span className="lp-eyebrow">
					{__("Solution Configurator", "linker-tools")}
				</span>
				{failed ? (
					<Notice error>
						<p>
							{__(
								"Your workspace could not be opened. Your saved projects are unchanged.",
								"linker-tools",
							)}
						</p>
						<button className="lp-button" onClick={recheck}>
							{__("Try again", "linker-tools")}
						</button>
					</Notice>
				) : (
					<p role="status">{__("Opening your workspace…", "linker-tools")}</p>
				)}
			</div>
		);
	return (
		<QueryClientProvider client={cache}>
			{children(session, recheck)}
		</QueryClientProvider>
	);
}
