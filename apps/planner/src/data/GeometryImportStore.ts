/** Exact source intents survive unknown acknowledgements. Scope grants come from
 * the native session; this browser journal never grants project ownership. */
import { readGeometryImportCommand } from "../domain/geometryImports.ts";
import policy from "../contracts/geometry-import-policy.json" with { type: "json" };
import { readObject } from "./readProtocol.ts";

export interface GeometryImportIntent {
	readonly scope: string;
	readonly projectId: string;
	readonly key: string;
	readonly label: string;
	readonly body: string;
	readonly createdAt: number;
	readonly assetId: string | null;
}
const DATABASE = "linker-planner-geometry-intents-v1",
	STORE = "intents",
	uuid =
		/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/i,
	hex = (value: string, length: number) =>
		value.length === length && /^[a-f0-9]+$/.test(value),
	bytes = (body: string) => new TextEncoder().encode(body).length;

function command(body: string) {
	if (bytes(body) > policy.max_scope_intent_bytes)
		throw new Error("geometry_recovery_limit");
	const value = readGeometryImportCommand(JSON.parse(body));
	if (!uuid.test(value.key)) throw new Error("geometry_recovery_invalid");
	return value;
}
function record(value: unknown, scope: string): GeometryImportIntent {
	const row = readObject(value);
	if (
		row.schema_version !== 1 ||
		row.scope !== scope ||
		typeof row.body !== "string" ||
		!Number.isSafeInteger(row.created_at) ||
		(row.created_at as number) < 0 ||
		(row.asset_id !== null &&
			(typeof row.asset_id !== "string" || !hex(row.asset_id, 32)))
	)
		throw new Error("geometry_recovery_invalid");
	const request = command(row.body);
	if (row.id !== scope + ":" + request.key.toLowerCase())
		throw new Error("geometry_recovery_invalid");
	return {
		scope,
		projectId: request.project_id,
		key: request.key.toLowerCase(),
		label: request.options.source.label,
		body: row.body,
		createdAt: row.created_at as number,
		assetId: row.asset_id as string | null,
	};
}
function complete(transaction: IDBTransaction): Promise<void> {
	return new Promise((resolve, reject) => {
		transaction.oncomplete = () => resolve();
		transaction.onerror = transaction.onabort = () =>
			reject(new Error("geometry_recovery_unavailable"));
	});
}
function scan(
	store: IDBObjectStore,
	scope: string,
	done: (records: GeometryImportIntent[]) => void,
	fail: (error: unknown) => void,
) {
	const records: GeometryImportIntent[] = [];
	let size = 0;
	const request = store.index("scope").openCursor(scope);
	request.onerror = () => fail(new Error("geometry_recovery_unavailable"));
	request.onsuccess = () => {
		try {
			const cursor = request.result;
			if (!cursor) {
				done(records);
				return;
			}
			const item = record(cursor.value, scope);
			size += bytes(item.body);
			if (
				records.length >= policy.max_scope_intents ||
				size > policy.max_scope_intent_bytes
			)
				throw new Error("geometry_recovery_limit");
			records.push(item);
			cursor.continue();
		} catch (error) {
			fail(error);
		}
	};
}

export class GeometryImportStore {
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
				reject(new Error("geometry_recovery_unavailable"));
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

	async list(
		scopes: readonly string[],
		projectId: string,
	): Promise<readonly GeometryImportIntent[]> {
		if (!hex(projectId, 32) || scopes.some((scope) => !hex(scope, 64)))
			throw new Error("geometry_recovery_invalid");
		const db = await this.open(),
			results: GeometryImportIntent[] = [];
		let size = 0;
		for (const scope of new Set(scopes)) {
			const records = await new Promise<GeometryImportIntent[]>(
				(resolve, reject) => {
					const transaction = db.transaction(STORE, "readonly");
					let scanned: GeometryImportIntent[] | null = null;
					transaction.oncomplete = () =>
						scanned === null
							? reject(new Error("geometry_recovery_unavailable"))
							: resolve(scanned);
					transaction.onerror = transaction.onabort = () =>
						reject(new Error("geometry_recovery_unavailable"));
					scan(
						transaction.objectStore(STORE),
						scope,
						(records) => {
							scanned = records;
						},
						(error) => {
							reject(error);
							transaction.abort();
						},
					);
				},
			);
			for (const item of records) {
				if (item.projectId !== projectId) continue;
				size += bytes(item.body);
				if (
					results.length >= policy.max_scope_intents ||
					size > policy.max_scope_intent_bytes
				)
					throw new Error("geometry_recovery_limit");
				results.push(item);
			}
		}
		return results.sort(
			(a, b) =>
				a.createdAt - b.createdAt ||
				(a.scope + a.key).localeCompare(b.scope + b.key),
		);
	}

	async write(scope: string, body: string): Promise<void> {
		if (!hex(scope, 64)) throw new Error("geometry_recovery_invalid");
		const request = command(body),
			db = await this.open(),
			transaction = db.transaction(STORE, "readwrite"),
			committed = complete(transaction),
			store = transaction.objectStore(STORE);
		let refusal: unknown = null;
		const fail = (error: unknown) => {
			refusal = error;
			transaction.abort();
		};
		scan(
			store,
			scope,
			(records) => {
				const prior = records.find(
					(value) => value.key === request.key.toLowerCase(),
				);
				if (prior) {
					if (prior.body !== body)
						fail(new Error("geometry_recovery_conflict"));
					return;
				}
				if (
					records.length >= policy.max_scope_intents ||
					records.reduce(
						(total, item) => total + bytes(item.body),
						bytes(body),
					) > policy.max_scope_intent_bytes
				) {
					fail(new Error("geometry_recovery_limit"));
					return;
				}
				store.put({
					schema_version: 1,
					id: scope + ":" + request.key.toLowerCase(),
					scope,
					body,
					created_at: Date.now(),
					asset_id: null,
				});
			},
			fail,
		);
		await committed.catch((error) => {
			throw refusal ?? error;
		});
	}

	async acknowledge(
		scope: string,
		body: string,
		assetId: string,
	): Promise<void> {
		if (!hex(assetId, 32)) throw new Error("geometry_recovery_invalid");
		await this.change(scope, body, assetId);
	}
	async clear(scope: string, body: string): Promise<void> {
		await this.change(scope, body, null);
	}
	private async change(
		scope: string,
		body: string,
		assetId: string | null,
	): Promise<void> {
		if (!hex(scope, 64)) throw new Error("geometry_recovery_invalid");
		const request = command(body),
			db = await this.open(),
			transaction = db.transaction(STORE, "readwrite"),
			committed = complete(transaction),
			store = transaction.objectStore(STORE),
			key = scope + ":" + request.key.toLowerCase();
		let refusal: unknown = null;
		const row = store.get(key);
		row.onsuccess = () => {
			try {
				if (row.result === undefined) {
					if (assetId !== null) throw new Error("geometry_recovery_absent");
					return;
				}
				const existing = record(row.result, scope);
				if (
					existing.body !== body ||
					(assetId !== null &&
						existing.assetId !== null &&
						existing.assetId !== assetId)
				)
					throw new Error("geometry_recovery_conflict");
				if (assetId === null) store.delete(key);
				else store.put({ ...row.result, asset_id: assetId });
			} catch (error) {
				refusal = error;
				transaction.abort();
			}
		};
		await committed.catch((error) => {
			throw refusal ?? error;
		});
	}
}

export const geometryImportStore = new GeometryImportStore();
