/** Mutable local drawing journal. Exact compare-and-swap prevents a stale tab
 * from overwriting or deleting a newer buffer. It never grants project access. */
import { readMapDrawingDraft } from "../domain/mapDrawingDraft.ts";
import type { MapDrawingDraft } from "../domain/mapDrawingDraft.ts";
import { readObject } from "./readProtocol.ts";

export interface StoredMapDrawingDraft {
	readonly scope: string;
	readonly body: string;
	readonly drawing: MapDrawingDraft;
}
// Local resource policy, separate from survey precision and server capacity.
const DATABASE = "linker-planner-map-drawings-v1",
	STORE = "drawings";
const MAX_RECORD_BYTES = 8 * 1024 * 1024,
	MAX_SCOPE_BYTES = 32 * 1024 * 1024,
	MAX_SCOPE_RECORDS = 32;
const size = (body: string) => new TextEncoder().encode(body).length;
function scopeKey(scope: string) {
	if (!/^[a-f0-9]{64}$/.test(scope))
		throw new Error("map_drawing_recovery_invalid");
}
function decode(body: string): MapDrawingDraft {
	if (size(body) > MAX_RECORD_BYTES)
		throw new Error("map_drawing_recovery_limit");
	return readMapDrawingDraft(JSON.parse(body));
}
function row(value: unknown, scope: string): StoredMapDrawingDraft {
	const record = readObject(value, 4);
	if (
		record.schema_version !== 1 ||
		record.scope !== scope ||
		typeof record.body !== "string"
	)
		throw new Error("map_drawing_recovery_invalid");
	const drawing = decode(record.body);
	if (record.id !== scope + ":" + drawing.key)
		throw new Error("map_drawing_recovery_invalid");
	return { scope, body: record.body, drawing };
}
function scan(
	store: IDBObjectStore,
	scope: string,
	done: (rows: StoredMapDrawingDraft[]) => void,
	fail: (error: unknown) => void,
) {
	const rows: StoredMapDrawingDraft[] = [];
	let bytes = 0;
	const request = store.index("scope").openCursor(scope);
	request.onerror = () => fail(new Error("map_drawing_recovery_unavailable"));
	request.onsuccess = () => {
		try {
			const cursor = request.result;
			if (!cursor) {
				done(rows);
				return;
			}
			const item = row(cursor.value, scope);
			bytes += size(item.body);
			if (rows.length >= MAX_SCOPE_RECORDS || bytes > MAX_SCOPE_BYTES)
				throw new Error("map_drawing_recovery_limit");
			rows.push(item);
			cursor.continue();
		} catch (error) {
			fail(error);
		}
	};
}

export class MapDrawingDraftStore {
	private connection: Promise<IDBDatabase> | null = null;
	private open(): Promise<IDBDatabase> {
		if (this.connection) return this.connection;
		const pending = new Promise<IDBDatabase>((resolve, reject) => {
			let refused = false;
			const request = indexedDB.open(DATABASE, 1);
			request.onupgradeneeded = () => {
				if (refused) {
					request.transaction?.abort();
					return;
				}
				const store = request.result.createObjectStore(STORE, {
					keyPath: "id",
				});
				store.createIndex("scope", "scope", { unique: false });
			};
			request.onerror = request.onblocked = () => {
				refused = true;
				reject(new Error("map_drawing_recovery_unavailable"));
			};
			request.onsuccess = () => {
				if (refused) {
					request.result.close();
					return;
				}
				request.result.onversionchange = () => {
					request.result.close();
					if (this.connection === pending) this.connection = null;
				};
				resolve(request.result);
			};
		});
		this.connection = pending;
		void pending.catch(() => {
			if (this.connection === pending) this.connection = null;
		});
		return pending;
	}
	/** Scopes must be the current native grant, never browser-selected identities. */
	async list(
		scopes: readonly string[],
		projectId: string,
	): Promise<readonly StoredMapDrawingDraft[]> {
		if (!/^[a-f0-9]{32}$/.test(projectId))
			throw new Error("map_drawing_recovery_invalid");
		scopes.forEach(scopeKey);
		const db = await this.open(),
			results: StoredMapDrawingDraft[] = [];
		let total = 0;
		for (const scope of new Set(scopes)) {
			const rows = await new Promise<StoredMapDrawingDraft[]>(
				(resolve, reject) => {
					const transaction = db.transaction(STORE, "readonly");
					let rows: StoredMapDrawingDraft[] | null = null;
					transaction.oncomplete = () =>
						rows === null
							? reject(new Error("map_drawing_recovery_unavailable"))
							: resolve(rows);
					transaction.onerror = transaction.onabort = () =>
						reject(new Error("map_drawing_recovery_unavailable"));
					scan(
						transaction.objectStore(STORE),
						scope,
						(found) => {
							rows = found;
						},
						(error) => {
							transaction.abort();
							reject(error);
						},
					);
				},
			);
			for (const item of rows)
				if (item.drawing.project_id === projectId) {
					total += size(item.body);
					if (results.length >= MAX_SCOPE_RECORDS || total > MAX_SCOPE_BYTES)
						throw new Error("map_drawing_recovery_limit");
					results.push(item);
				}
		}
		return results.sort((a, b) =>
			(a.scope + a.drawing.key).localeCompare(b.scope + b.drawing.key),
		);
	}
	async write(
		scope: string,
		previous: string | null,
		next: string,
	): Promise<void> {
		scopeKey(scope);
		const drawing = decode(next);
		if (
			previous !== null &&
			(decode(previous).key !== drawing.key ||
				decode(previous).project_id !== drawing.project_id)
		)
			throw new Error("map_drawing_recovery_invalid");
		await this.mutate(scope, (rows, store) => {
			const existing = rows.find((item) => item.drawing.key === drawing.key);
			if (existing?.body === next) return;
			if ((existing?.body ?? null) !== previous)
				throw new Error("map_drawing_recovery_conflict");
			const others = rows.filter((item) => item !== existing);
			if (
				others.length >= MAX_SCOPE_RECORDS ||
				others.reduce((sum, item) => sum + size(item.body), 0) + size(next) >
					MAX_SCOPE_BYTES
			)
				throw new Error("map_drawing_recovery_limit");
			store.put({
				schema_version: 1,
				id: scope + ":" + drawing.key,
				scope,
				body: next,
			});
		});
	}
	async clear(scope: string, body: string): Promise<void> {
		scopeKey(scope);
		const drawing = decode(body);
		await this.mutate(scope, (rows, store) => {
			const existing = rows.find((item) => item.drawing.key === drawing.key);
			if (!existing) return;
			if (existing.body !== body)
				throw new Error("map_drawing_recovery_conflict");
			store.delete(scope + ":" + drawing.key);
		});
	}
	private async mutate(
		scope: string,
		apply: (rows: StoredMapDrawingDraft[], store: IDBObjectStore) => void,
	): Promise<void> {
		const db = await this.open();
		await new Promise<void>((resolve, reject) => {
			const transaction = db.transaction(STORE, "readwrite"),
				store = transaction.objectStore(STORE);
			let refusal: unknown = null;
			const fail = (cause: unknown) => {
				refusal = cause;
				transaction.abort();
			};
			transaction.oncomplete = () => resolve();
			transaction.onerror = transaction.onabort = () =>
				reject(refusal ?? new Error("map_drawing_recovery_unavailable"));
			scan(
				store,
				scope,
				(rows) => {
					try {
						apply(rows, store);
					} catch (error) {
						fail(error);
					}
				},
				fail,
			);
		});
	}
}

export const mapDrawingDraftStore = new MapDrawingDraftStore();
