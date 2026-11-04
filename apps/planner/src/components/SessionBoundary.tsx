import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { flushSync } from "react-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ApiError } from "../data/protocol.ts";
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
	const confirmed = useRef<Session | null>(null);
	const [, setPulse] = useState(0);
	// The workspace is gated (hidden+inert) only while no session is confirmed
	// yet and after a probe confirms the identity changed. Revalidation of a
	// confirmed session is stale-while-revalidate: the workspace stays visible
	// and interactive, and a failed refresh never becomes an opening failure.
	const [gate, setGate] = useState(true);
	const [failed, setFailed] = useState(false);
	const [refreshFailed, setRefreshFailed] = useState(false);
	const busy = useRef(false);
	const queued = useRef(false);
	const verifyRef = useRef<(mode: "probe" | "full") => void>(() => {});

	const adopt = useCallback(
		(value: Session) => {
			if (
				confirmed.current &&
				confirmed.current.query_scope !== value.query_scope
			)
				cache.clear();
			confirmed.current = value;
			setSession(value);
			setGate(false);
			setFailed(false);
		},
		[cache],
	);

	const verify = useCallback(
		(mode: "probe" | "full") => {
			if (busy.current) {
				queued.current = true;
				return;
			}
			busy.current = true;
			setRefreshFailed(false);
			const controller = new AbortController();
			const done = () => {
				busy.current = false;
				if (queued.current) {
					queued.current = false;
					verifyRef.current("probe");
				}
			};
			const full = (reason: "initial" | "removal" | "reauth") => {
				// No cache.cancelQueries() here: a revalidation must not cancel
				// the live same-scope queries running under it, and the
				// scope-change path clears the whole cache on adoption.
				client.invalidate();
				setFailed(false);
				// Commit the dropped admission before the new bootstrap runs,
				// so enabled-gated consumers see enabled=false -> true across
				// exactly one revalidation cycle. Without this, the admission
				// drop can batch with the re-adoption render and the retry
				// never fires.
				flushSync(() => {
					setPulse((value) => value + 1);
				});
				void client
					.bootstrap(controller.signal)
					.then((value) => {
						adopt(value);
						done();
					})
					.catch(() => {
						if (controller.signal.aborted) return;
						// Only the ungated opening and a confirmed identity
						// change may show the opening failure; a refresh of a
						// still-confirmed session stays non-blocking.
						if (reason === "reauth") setRefreshFailed(true);
						else setFailed(true);
						done();
					});
			};
			if (mode === "full" || confirmed.current === null) {
				full(confirmed.current === null ? "initial" : "reauth");
				return;
			}
			const current = confirmed.current;
			void client
				.probeScope(controller.signal)
				.then((scope) => {
					if (scope === current.query_scope) {
						done();
						return;
					}
					// The identity changed under the workspace: gate the
					// former editor before the new session is admitted.
					setGate(true);
					full("removal");
				})
				.catch((error) => {
					if (controller.signal.aborted) return;
					if (
						error instanceof ApiError &&
						(error.status === 401 || error.status === 403)
					) {
						// The probe cannot authenticate (for example an expired
						// nonce); one full bootstrap re-admits or replaces the
						// session without gating the workspace.
						full("reauth");
						return;
					}
					setRefreshFailed(true);
					done();
				});
		},
		[adopt, cache, client],
	);
	useEffect(() => {
		verifyRef.current = verify;
	}, [verify]);

	const initial = useRef(false);
	const startInitial = useCallback(() => {
		// StrictMode remounts must not queue a second verification on top of
		// the initial bootstrap that is already in flight.
		if (initial.current) return;
		initial.current = true;
		verify("probe");
	}, [verify]);
	useEffect(() => {
		startInitial();
	}, [startInitial]);
	useEffect(() => () => cache.clear(), [cache]);

	useEffect(() => {
		let timer: ReturnType<typeof setTimeout> | undefined;
		const request = () => {
			// focus and visibilitychange both fire on one tab switch; a
			// single coalesced revalidation covers them.
			if (timer !== undefined) return;
			timer = setTimeout(() => {
				timer = undefined;
				verify("probe");
			}, 0);
		};
		const visible = () => {
			if (document.visibilityState === "visible") request();
		};
		const restored = (event: PageTransitionEvent) => {
			if (event.persisted) request();
		};
		window.addEventListener("focus", request);
		window.addEventListener("online", request);
		window.addEventListener("pageshow", restored);
		document.addEventListener("visibilitychange", visible);
		return () => {
			if (timer !== undefined) clearTimeout(timer);
			window.removeEventListener("focus", request);
			window.removeEventListener("online", request);
			window.removeEventListener("pageshow", restored);
			document.removeEventListener("visibilitychange", visible);
		};
	}, [verify]);

	const recheck = useCallback(() => verify("full"), [verify]);

	return (
		<>
			{gate && (
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
			)}
			{session && (
				<QueryClientProvider client={cache}>
					<div hidden={gate} inert={gate}>
						{children(session, recheck)}
					</div>
				</QueryClientProvider>
			)}
			{refreshFailed && !gate && (
				<div className="lp-session-state" role="status">
					<Notice error>
						<p>
							{__(
								"Your session could not be rechecked. Your edits are preserved.",
								"linker-tools",
							)}
						</p>
						<button className="lp-button" onClick={() => verify("probe")}>
							{__("Try again", "linker-tools")}
						</button>
					</Notice>
				</div>
			)}
		</>
	);
}
