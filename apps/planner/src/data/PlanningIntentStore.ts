/** Browser recovery of exact battery/run requests, never project/job authority. */
import type { PlanningOperation } from "./planningProtocol.ts";
import {
	readPlanningOperation,
	isPlanningOperation,
} from "./planningProtocol.ts";
import { readObject } from "./readProtocol.ts";

export interface PlanningIntent {
	readonly scope: string;
	readonly path: PlanningOperation;
	readonly projectId: string;
	readonly key: string;
	readonly body: string;
	readonly createdAt: number;
	readonly resultId: string | null;
}
// Same browser recovery envelope as project creations: 128 intents / 8 MiB.
// These are local resource limits, not a calculation/site capacity claim.
const MAX_INTENTS = 128,
	MAX_BYTES = 8 * 1024 * 1024;
const DATABASE = "linker-planner-energy-intents-v1",
	STORE = "intents";
const hex = (value: unknown, length: number): value is string =>
	typeof value === "string" && new RegExp(`^[a-f0-9]{${length}}$`).test(value);
const bytes = (body: string) => new TextEncoder().encode(body).length;
function identity(scope: string, path: PlanningOperation, body: string) {
	if (!hex(scope, 64) || !isPlanningOperation(path) || bytes(body) > MAX_BYTES)
		throw new Error("energy_recovery_invalid");
	const command = readPlanningOperation(path, body);
	return {
		id: scope + ":" + path + ":" + String(command.key).toLowerCase(),
		command,
	};
}
function record(value: unknown, scope: string): PlanningIntent {
	const row = readObject(value);
	if (
		row.schema_version !== 1 ||
		row.scope !== scope ||
		!isPlanningOperation(row.path) ||
		typeof row.body !== "string" ||
		!Number.isSafeInteger(row.created_at) ||
		(row.created_at as number) < 0 ||
		(row.result_id !== null && !hex(row.result_id, 32))
	)
		throw new Error("energy_recovery_invalid");
	const request = identity(scope, row.path, row.body);
	if (row.id !== request.id) throw new Error("energy_recovery_invalid");
	return {
		scope,
		path: row.path,
		projectId: String(request.command.project_id),
		key: String(request.command.key).toLowerCase(),
		body: row.body,
		createdAt: row.created_at as number,
		resultId: row.result_id as string | null,
	};
}
function completed(transaction: IDBTransaction): Promise<void> {
	return new Promise((resolve, reject) => {
		transaction.oncomplete = () => resolve();
		transaction.onerror = transaction.onabort = () =>
			reject(new Error("energy_recovery_unavailable"));
	});
}
function scan(
	store: IDBObjectStore,
	scope: string,
	done: (records: PlanningIntent[]) => void,
	fail: (error: unknown) => void,
) {
	const result: PlanningIntent[] = [];
	let size = 0;
	const cursor = store.index("scope").openCursor(scope);
	cursor.onerror = () => fail(new Error("energy_recovery_unavailable"));
	cursor.onsuccess = () => {
		try {
			if (!cursor.result) {
				done(result);
				return;
			}
			const item = record(cursor.result.value, scope);
			size += bytes(item.body);
			if (result.length >= MAX_INTENTS || size > MAX_BYTES)
				throw new Error("energy_recovery_limit");
			result.push(item);
			cursor.result.continue();
		} catch (error) {
			fail(error);
		}
	};
}

export class PlanningIntentStore {
	private connection: Promise<IDBDatabase> | null = null;
	private open(): Promise<IDBDatabase> {
		if (this.connection) return this.connection;
		const opening = new Promise<IDBDatabase>((resolve, reject) => {
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
				reject(new Error("energy_recovery_unavailable"));
			};
			request.onsuccess = () => {
				if (refused) {
					request.result.close();
					return;
				}
				request.result.onversionchange = () => {
					request.result.close();
					if (this.connection === opening) this.connection = null;
				};
				resolve(request.result);
			};
		});
		this.connection = opening;
		void opening.catch(() => {
			if (this.connection === opening) this.connection = null;
		});
		return opening;
	}
	async list(
		scopes: readonly string[],
		projectId: string,
	): Promise<readonly PlanningIntent[]> {
		if (!hex(projectId, 32) || scopes.some((scope) => !hex(scope, 64)))
			throw new Error("energy_recovery_invalid");
		const db = await this.open(),
			records: PlanningIntent[] = [];
		let size = 0;
		for (const scope of new Set(scopes)) {
			const found = await new Promise<PlanningIntent[]>((resolve, reject) => {
				const transaction = db.transaction(STORE, "readonly");
				let rows: PlanningIntent[] | null = null;
				transaction.oncomplete = () =>
					rows === null
						? reject(new Error("energy_recovery_unavailable"))
						: resolve(rows);
				transaction.onerror = transaction.onabort = () =>
					reject(new Error("energy_recovery_unavailable"));
				scan(
					transaction.objectStore(STORE),
					scope,
					(value) => {
						rows = value;
					},
					reject,
				);
			});
			for (const row of found) {
				size += bytes(row.body);
				if (records.length >= MAX_INTENTS || size > MAX_BYTES)
					throw new Error("energy_recovery_limit");
				records.push(row);
			}
		}
		return records
			.filter((row) => row.projectId === projectId)
			.sort((a, b) => a.createdAt - b.createdAt || a.key.localeCompare(b.key));
	}
	async write(
		scope: string,
		path: PlanningOperation,
		body: string,
	): Promise<void> {
		const request = identity(scope, path, body),
			db = await this.open();
		const transaction = db.transaction(STORE, "readwrite"),
			committed = completed(transaction),
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
				const old = records.find(
					(row) =>
						row.path === path &&
						row.key === String(request.command.key).toLowerCase(),
				);
				if (old) {
					if (old.body !== body) fail(new Error("energy_recovery_conflict"));
					return;
				}
				if (
					records.length >= MAX_INTENTS ||
					records.reduce((n, row) => n + bytes(row.body), bytes(body)) >
						MAX_BYTES
				) {
					fail(new Error("energy_recovery_limit"));
					return;
				}
				store.put({
					id: request.id,
					schema_version: 1,
					scope,
					path,
					body,
					created_at: Date.now(),
					result_id: null,
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
		path: PlanningOperation,
		body: string,
		resultId: string,
	): Promise<void> {
		if (!hex(resultId, 32)) throw new Error("energy_recovery_invalid");
		await this.change(scope, path, body, resultId);
	}
	async clear(
		scope: string,
		path: PlanningOperation,
		body: string,
	): Promise<void> {
		await this.change(scope, path, body, null);
	}
	private async change(
		scope: string,
		path: PlanningOperation,
		body: string,
		resultId: string | null,
	): Promise<void> {
		const request = identity(scope, path, body),
			db = await this.open();
		const transaction = db.transaction(STORE, "readwrite"),
			committed = completed(transaction),
			store = transaction.objectStore(STORE);
		const read = store.get(request.id);
		read.onsuccess = () => {
			try {
				if (read.result === undefined) return;
				const row = record(read.result, scope);
				if (row.body !== body) return;
				if (resultId === null) store.delete(request.id);
				else if (row.resultId === null || row.resultId === resultId)
					store.put({ ...read.result, result_id: resultId });
				else transaction.abort();
			} catch {
				transaction.abort();
			}
		};
		await committed;
	}
}
export const planningIntentStore = new PlanningIntentStore();
