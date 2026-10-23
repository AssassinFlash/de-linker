import { useCallback, useEffect, useRef, useState } from "react";
import type { GeometryDocument } from "../domain/geometry.ts";
import type {
	MapDrawingDraft,
	MapDrawingIntent,
} from "../domain/mapDrawingDraft.ts";
import { startMapDrawingDraft } from "../domain/mapDrawingDraft.ts";
import { sameJson } from "../domain/draft.ts";
import { mapDrawingDraftStore } from "./MapDrawingDraftStore.ts";
import type {
	MapDrawingDraftStore,
	StoredMapDrawingDraft,
} from "./MapDrawingDraftStore.ts";
import type { PlannerClient } from "./PlannerClient.ts";
import type { Session } from "./protocol.ts";

interface DrawingWriter {
	readonly scope: string;
	readonly key: string;
	body: string | null;
	pending: { previous: string | null; next: string } | null;
	chain: Promise<void>;
}
export type DrawingJournal = Pick<
	MapDrawingDraftStore,
	"list" | "write" | "clear"
>;

/** Restoring bytes requires a verified native project and scope grant. Partial
 * points stay outside project history, including across route/provider changes. */
export function useMapDrawingDraft({
	projectId,
	geometry,
	confirmedGeometry,
	locale,
	session,
	client,
	recoveryScopes,
	recoveryChecking = false,
	store = mapDrawingDraftStore,
}: {
	projectId: string;
	geometry: GeometryDocument;
	confirmedGeometry: GeometryDocument | null;
	locale: string;
	session: Session;
	client: PlannerClient;
	recoveryScopes?: readonly string[] | undefined;
	recoveryChecking?: boolean | undefined;
	store?: DrawingJournal;
}) {
	const [drawing, setDrawing] = useState<MapDrawingDraft | null>(null),
		[records, setRecords] = useState<readonly StoredMapDrawingDraft[]>([]),
		[active, setActive] = useState(false),
		[checking, setChecking] = useState(true),
		[storageFailed, setStorageFailed] = useState(false),
		[writing, setWriting] = useState(false),
		[refresh, setRefresh] = useState(0);
	const latest = useRef<MapDrawingDraft | null>(null),
		writer = useRef<DrawingWriter | null>(null),
		mounted = useRef(true);
	const owner = useRef(projectId + ":" + session.query_scope);
	const ownerKey = projectId + ":" + session.query_scope;
	const sameOwner = owner.current === ownerKey;
	const scopeKey = JSON.stringify([
		...new Set([session.query_scope, ...(recoveryScopes ?? [])]),
	]);
	const context = useRef({ scopeKey, session, projectId });
	context.current = { scopeKey, session, projectId };
	const admitted = useCallback(
		(scope: string) =>
			client.isCurrentScope(session.query_scope) &&
			(JSON.parse(context.current.scopeKey) as string[]).includes(scope),
		[client, session.query_scope],
	);
	useEffect(() => {
		mounted.current = true;
		return () => {
			mounted.current = false;
		};
	}, []);
	useEffect(() => {
		if (owner.current === ownerKey) return;
		owner.current = ownerKey;
		writer.current = null;
		latest.current = null;
		setDrawing(null);
		setRecords([]);
		setActive(false);
		setChecking(true);
		setWriting(false);
		setStorageFailed(false);
	}, [ownerKey]);
	useEffect(() => {
		if (recoveryChecking || !client.isCurrentScope(session.query_scope)) return;
		let current = true;
		setChecking(true);
		void (async () => {
			const found = await store.list(
				JSON.parse(scopeKey) as string[],
				projectId,
			);
			const retained: StoredMapDrawingDraft[] = [];
			for (const record of found) {
				if (!current || !admitted(record.scope)) return;
				if (
					record.drawing.prepared_geometry &&
					confirmedGeometry &&
					sameJson(record.drawing.prepared_geometry, confirmedGeometry) &&
					writer.current?.key !== record.drawing.key
				) {
					await store.clear(record.scope, record.body);
				} else retained.push(record);
			}
			if (current && client.isCurrentScope(session.query_scope)) {
				setRecords(retained);
				if (!writer.current) setStorageFailed(false);
			}
		})()
			.catch(() => {
				if (current) setStorageFailed(true);
			})
			.finally(() => {
				if (current) setChecking(false);
			});
		return () => {
			current = false;
		};
	}, [
		projectId,
		scopeKey,
		recoveryChecking,
		client,
		session.query_scope,
		admitted,
		store,
		refresh,
		confirmedGeometry,
	]);

	async function acknowledge(
		target: DrawingWriter,
		intent: NonNullable<DrawingWriter["pending"]>,
	) {
		if (!admitted(target.scope) || writer.current !== target)
			throw new Error("session_changed");
		target.pending = intent;
		try {
			await store.write(target.scope, intent.previous, intent.next);
		} catch (error) {
			// These journal refusals occur before mutation (or abort its transaction).
			// Unknown acknowledgements retain their exact bytes until confirmed.
			if (
				error instanceof Error &&
				[
					"map_drawing_recovery_invalid",
					"map_drawing_recovery_limit",
					"map_drawing_recovery_conflict",
				].includes(error.message)
			)
				target.pending = null;
			throw error;
		}
		target.body = intent.next;
		target.pending = null;
	}
	function persist(
		next: MapDrawingDraft,
		target: DrawingWriter,
	): Promise<void> {
		const body = JSON.stringify(next);
		setWriting(true);
		const operation = target.chain
			.catch(() => undefined)
			.then(async () => {
				const pending = target.pending;
				if (pending) await acknowledge(target, pending);
				if (pending?.next !== body)
					await acknowledge(target, { previous: target.body, next: body });
			});
		target.chain = operation;
		void operation.then(
			() => {
				if (
					mounted.current &&
					writer.current === target &&
					target.chain === operation
				) {
					setStorageFailed(false);
					setWriting(false);
				}
			},
			() => {
				if (
					mounted.current &&
					writer.current === target &&
					target.chain === operation
				) {
					setStorageFailed(true);
					setWriting(false);
				}
			},
		);
		return operation;
	}
	function update(next: MapDrawingDraft): Promise<void> {
		const target = writer.current;
		if (
			!target ||
			!admitted(target.scope) ||
			next.key !== target.key ||
			next.project_id !== projectId
		)
			return Promise.reject(new Error("session_changed"));
		latest.current = next;
		setDrawing(next);
		return persist(next, target);
	}
	function begin(
		input:
			MapDrawingIntent | { kind: "restore"; record: StoredMapDrawingDraft },
	) {
		if (
			writer.current ||
			active ||
			checking ||
			recoveryChecking ||
			!client.isCurrentScope(session.query_scope)
		)
			return false;
		const record = input.kind === "restore" ? input.record : null;
		if (record && (!records.includes(record) || !admitted(record.scope)))
			return false;
		const next =
			input.kind === "restore"
				? input.record.drawing
				: startMapDrawingDraft(projectId, geometry, locale, input);
		const target: DrawingWriter = {
			scope: record?.scope ?? session.query_scope,
			key: next.key,
			body: record?.body ?? null,
			pending: null,
			chain: Promise.resolve(),
		};
		writer.current = target;
		latest.current = next;
		setDrawing(next);
		setActive(true);
		setStorageFailed(false);
		if (!record) void persist(next, target).catch(() => undefined);
		return true;
	}
	async function flush(): Promise<boolean> {
		const target = writer.current;
		if (!target || !latest.current || !admitted(target.scope)) return false;
		try {
			await persist(latest.current, target);
			return writer.current === target && admitted(target.scope);
		} catch {
			return false;
		}
	}
	async function pause(): Promise<boolean> {
		if (!(await flush())) return false;
		setActive(false);
		return true;
	}
	async function discard() {
		const target = writer.current;
		if (!target || !admitted(target.scope)) return;
		setWriting(true);
		const operation = target.chain
			.catch(() => undefined)
			.then(async () => {
				if (!admitted(target.scope) || writer.current !== target)
					throw new Error("session_changed");
				if (target.pending) await acknowledge(target, target.pending);
				if (target.body !== null) await store.clear(target.scope, target.body);
				if (writer.current !== target || !admitted(target.scope)) return;
				writer.current = null;
				latest.current = null;
				setDrawing(null);
				setActive(false);
				setStorageFailed(false);
				setWriting(false);
				setRefresh((value) => value + 1);
			});
		target.chain = operation;
		try {
			await operation;
		} catch {
			if (mounted.current && writer.current === target) {
				setStorageFailed(true);
				setWriting(false);
			}
		}
	}
	function fork() {
		if (!latest.current || !client.isCurrentScope(session.query_scope)) return;
		const next = {
			...latest.current,
			key: crypto.randomUUID(),
			prepared_geometry: null,
		};
		const target: DrawingWriter = {
			scope: session.query_scope,
			key: next.key,
			body: null,
			pending: null,
			chain: Promise.resolve(),
		};
		writer.current = target;
		latest.current = next;
		setDrawing(next);
		setActive(true);
		void persist(next, target).catch(() => undefined);
	}
	function resume() {
		const target = writer.current;
		if (
			target &&
			latest.current &&
			admitted(target.scope) &&
			!checking &&
			!recoveryChecking
		)
			setActive(true);
	}
	function hide() {
		if (writing) return;
		writer.current = null;
		latest.current = null;
		setDrawing(null);
		setActive(false);
		setRefresh((value) => value + 1);
	}
	// A protected result is retired only after native project read/save confirms
	// those exact geometry bytes, never just because a React command returned true.
	useEffect(() => {
		const target = writer.current,
			value = latest.current;
		if (
			active ||
			!target ||
			!value?.prepared_geometry ||
			!confirmedGeometry ||
			!sameJson(value.prepared_geometry, confirmedGeometry)
		)
			return;
		let current = true;
		void target.chain
			.then(async () => {
				if (!current || !admitted(target.scope) || target.body === null) return;
				await store.clear(target.scope, target.body);
				if (!current || writer.current !== target || !admitted(target.scope))
					return;
				writer.current = null;
				latest.current = null;
				setDrawing(null);
				setStorageFailed(false);
				setRefresh((n) => n + 1);
			})
			.catch(() => {
				if (current) setStorageFailed(true);
			});
		return () => {
			current = false;
		};
	}, [active, confirmedGeometry, admitted, store, drawing, refresh]);
	return {
		drawing: sameOwner ? drawing : null,
		records: sameOwner ? records : [],
		active: sameOwner && active,
		checking: !sameOwner || checking || recoveryChecking,
		storageFailed,
		writing,
		begin,
		update,
		flush,
		retry: async () => {
			if (await flush()) setRefresh((n) => n + 1);
		},
		reload: () => setRefresh((n) => n + 1),
		pause,
		resume,
		hide,
		discard,
		fork,
		deactivate: () => setActive(false),
		latest,
	};
}
