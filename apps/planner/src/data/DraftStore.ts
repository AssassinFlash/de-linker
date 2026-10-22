import type { Draft, SaveIntent } from "../domain/draft.ts";
import { sameJson } from "../domain/draft.ts";
import type { JsonObject, Project } from "./protocol.ts";
import { readObject, readProject } from "./readProtocol.ts";

interface StoredDraft {
	schema_version: 1;
	key: string;
	scope: string;
	project_id: string;
	draft: Draft;
	updated_at: number;
}
export interface RecoveryCandidate {
	readonly scope: string;
	readonly draft: Draft;
	readonly updatedAt: number;
}
export interface CreationIntent {
	readonly key: string;
	readonly title: string;
	readonly body: string;
	readonly createdAt: number;
}
// Local recovery policy, never authority for an account/project or a saved run.
const DATABASE = "linker-planner-recovery-v1";
const STORE = "drafts";
const CREATIONS = "creations";
const CREATION_INTENTS = "creation_intents";
const MAX_RECOVERY_BYTES = 8 * 1024 * 1024;
const MAX_RECOVERY_HISTORY = 20;
// Browser recovery resource policy, not a project/account capacity limit.
const MAX_CREATION_INTENTS = 128;

export class DraftStore {
	private connection: Promise<IDBDatabase> | null = null;

	async readCreations(scope: string): Promise<readonly CreationIntent[]> {
		storageKey(scope, "0".repeat(32));
		const db = await this.open();
		const transaction = db.transaction(
			[CREATIONS, CREATION_INTENTS],
			"readonly",
		);
		const legacy = request<unknown>(
			transaction.objectStore(CREATIONS).get(scope),
		);
		const queued = new Promise<CreationIntent[]>((resolve, reject) =>
			scanCreations(
				transaction.objectStore(CREATION_INTENTS),
				scope,
				resolve,
				reject,
			),
		);
		const [value, records] = await Promise.all([legacy, queued]);
		if (value !== undefined) {
			// A malformed old record is retained and reported, never silently
			// discarded by an upgrade. Valid records were atomically migrated.
			const old = legacyCreation(value, scope);
			const queued = records.find((record) => record.key === old.key);
			if (queued && queued.body !== old.body)
				throw new Error("creation_intent_conflict");
			if (!queued) records.push(old);
		}
		return records.sort(
			(a, b) => a.createdAt - b.createdAt || a.key.localeCompare(b.key),
		);
	}

	async writeCreation(scope: string, body: string): Promise<void> {
		storageKey(scope, "0".repeat(32));
		const command = validateCreation(body);
		const db = await this.open();
		const transaction = db.transaction(CREATION_INTENTS, "readwrite");
		const committed = complete(transaction);
		const store = transaction.objectStore(CREATION_INTENTS);
		let refusal: Error | null = null;
		const refuse = (error: Error) => {
			refusal = error;
			transaction.abort();
		};
		scanCreations(
			store,
			scope,
			(records) => {
				const existing = records.find((record) => record.key === command.key);
				if (existing) {
					if (existing.body !== body)
						refuse(new Error("creation_intent_conflict"));
					return;
				}
				const bytes = records.reduce(
					(sum, record) => sum + new TextEncoder().encode(record.body).length,
					0,
				);
				if (
					records.length >= MAX_CREATION_INTENTS ||
					bytes + new TextEncoder().encode(body).length > MAX_RECOVERY_BYTES
				) {
					refuse(new Error("recovery_storage_limit"));
					return;
				}
				store.put({
					id: scope + ":" + command.key,
					scope,
					body,
					created_at: Date.now(),
				});
			},
			refuse,
		);
		await committed.catch((error: unknown) => {
			throw refusal ?? error;
		});
	}

	async clearCreation(scope: string, body: string): Promise<void> {
		storageKey(scope, "0".repeat(32));
		const command = validateCreation(body);
		const db = await this.open();
		const transaction = db.transaction(
			[CREATIONS, CREATION_INTENTS],
			"readwrite",
		);
		const committed = complete(transaction);
		for (const [name, id] of [
			[CREATIONS, scope],
			[CREATION_INTENTS, scope + ":" + command.key],
		] as const) {
			const store = transaction.objectStore(name);
			const read = store.get(id);
			read.onsuccess = () => {
				if (read.result?.body === body) store.delete(id);
			};
		}
		await committed;
	}

	async read(scope: string, projectId: string): Promise<Draft | null> {
		const db = await this.open();
		const value = await request<unknown>(
			db
				.transaction(STORE, "readonly")
				.objectStore(STORE)
				.get(storageKey(scope, projectId)),
		);
		return value === undefined ? null : decodeDraft(value, scope, projectId);
	}

	async write(scope: string, draft: Draft): Promise<void> {
		const projectId = draft.baseline.id;
		const record: StoredDraft = {
			schema_version: 1,
			key: storageKey(scope, projectId),
			scope,
			project_id: projectId,
			draft: {
				...draft,
				history: {
					...draft.history,
					past: draft.history.past.slice(-MAX_RECOVERY_HISTORY),
					future: draft.history.future.slice(0, MAX_RECOVERY_HISTORY),
				},
			},
			updated_at: Date.now(), // Local recovery ordering, never a server revision/time.
		};
		if (
			new TextEncoder().encode(JSON.stringify(record)).length >
			MAX_RECOVERY_BYTES
		)
			throw new Error("recovery_storage_limit");
		const db = await this.open();
		const transaction = db.transaction(STORE, "readwrite");
		const committed = complete(transaction);
		transaction.objectStore(STORE).put(record);
		await committed;
	}

	/** Call only after an authenticated server read has granted this project.
	 * Session-scoped query caches are never re-used. Local drafts for the same
	 * currently owned project can survive a login/renewal; unrelated project
	 * records are neither enumerated nor returned to the interface.
	 */
	async candidates(
		scope: string,
		authorized: Project,
	): Promise<readonly RecoveryCandidate[]> {
		storageKey(scope, authorized.id);
		const db = await this.open();
		const records = await request<unknown[]>(
			db
				.transaction(STORE, "readonly")
				.objectStore(STORE)
				.index("project_id")
				.getAll(authorized.id),
		);
		return records.flatMap((value) => {
			const record = readObject(value, 40);
			if (record.scope === scope) return [];
			if (typeof record.scope !== "string")
				throw new Error("invalid_recovery_scope");
			return [
				{
					scope: record.scope,
					draft: decodeDraft(value, record.scope, authorized.id),
					updatedAt:
						typeof record.updated_at === "number" ? record.updated_at : 0,
				},
			];
		});
	}

	private open(): Promise<IDBDatabase> {
		if (this.connection) return this.connection;
		const opening = new Promise<IDBDatabase>((resolve, reject) => {
			let refused = false;
			const opened = indexedDB.open(DATABASE, 4);
			opened.onupgradeneeded = () => {
				if (!opened.result.objectStoreNames.contains(STORE))
					opened.result.createObjectStore(STORE, { keyPath: "key" });
				const drafts = opened.transaction?.objectStore(STORE);
				if (drafts && !drafts.indexNames.contains("project_id"))
					drafts.createIndex("project_id", "project_id", { unique: false });
				if (!opened.result.objectStoreNames.contains(CREATIONS))
					opened.result.createObjectStore(CREATIONS, { keyPath: "scope" });
				if (!opened.result.objectStoreNames.contains(CREATION_INTENTS)) {
					const intents = opened.result.createObjectStore(CREATION_INTENTS, {
						keyPath: "id",
					});
					intents.createIndex("scope", "scope", { unique: false });
					const legacy = opened.transaction
						?.objectStore(CREATIONS)
						.openCursor();
					if (legacy)
						legacy.onsuccess = () => {
							const cursor = legacy.result;
							if (!cursor) return;
							try {
								const record = legacyCreation(
									cursor.value,
									String(cursor.primaryKey),
								);
								intents.put({
									id: String(cursor.primaryKey) + ":" + record.key,
									scope: cursor.primaryKey,
									body: record.body,
									created_at: 0,
								});
							} catch {
								// Preserve invalid legacy bytes for the visible recovery error.
							}
							cursor.continue();
						};
				}
			};
			opened.onsuccess = () => {
				const db = opened.result;
				if (refused) {
					db.close();
					return;
				}
				db.onversionchange = () => {
					db.close();
					if (this.connection === opening) this.connection = null;
				};
				resolve(db);
			};
			opened.onerror = () => {
				refused = true;
				reject(new Error("recovery_unavailable"));
			};
			opened.onblocked = () => {
				refused = true;
				reject(new Error("recovery_blocked"));
			};
		});
		this.connection = opening;
		void opening.catch(() => {
			if (this.connection === opening) this.connection = null;
		});
		return opening;
	}
}

function validateCreation(body: string): { key: string; title: string } {
	if (new TextEncoder().encode(body).length > MAX_RECOVERY_BYTES)
		throw new Error("recovery_storage_limit");
	const command = readObject(JSON.parse(body));
	if (
		command.schema_version !== 1 ||
		typeof command.title !== "string" ||
		!command.title.trim() ||
		command.title.length > 256 ||
		typeof command.key !== "string" ||
		!/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/i.test(
			command.key,
		) ||
		Object.keys(command).sort().join() !== "inputs,key,schema_version,title"
	)
		throw new Error("invalid_creation_recovery");
	readObject(command.inputs);
	return { key: command.key.toLowerCase(), title: command.title };
}

function legacyCreation(value: unknown, scope: string): CreationIntent {
	storageKey(scope, "0".repeat(32));
	const record = readObject(value);
	if (record.scope !== scope || typeof record.body !== "string")
		throw new Error("invalid_creation_recovery");
	return { ...validateCreation(record.body), body: record.body, createdAt: 0 };
}

function scanCreations(
	store: IDBObjectStore,
	scope: string,
	done: (records: CreationIntent[]) => void,
	fail: (error: Error) => void,
): void {
	const records: CreationIntent[] = [];
	let bytes = 0;
	const cursor = store.index("scope").openCursor(scope);
	cursor.onerror = () => fail(new Error("recovery_unavailable"));
	cursor.onsuccess = () => {
		try {
			const row = cursor.result;
			if (!row) {
				done(records);
				return;
			}
			const value = readObject(row.value);
			if (
				value.scope !== scope ||
				typeof value.body !== "string" ||
				typeof value.created_at !== "number" ||
				!Number.isSafeInteger(value.created_at) ||
				value.created_at < 0
			)
				throw new Error("invalid_creation_recovery");
			const command = validateCreation(value.body);
			if (value.id !== scope + ":" + command.key)
				throw new Error("invalid_creation_recovery");
			bytes += new TextEncoder().encode(value.body).length;
			if (records.length >= MAX_CREATION_INTENTS || bytes > MAX_RECOVERY_BYTES)
				throw new Error("recovery_storage_limit");
			records.push({
				...command,
				body: value.body,
				createdAt: value.created_at,
			});
			row.continue();
		} catch (error) {
			fail(
				error instanceof Error ? error : new Error("invalid_creation_recovery"),
			);
		}
	};
}

function storageKey(scope: string, projectId: string): string {
	if (!/^[a-f0-9]{64}$/.test(scope) || !/^[a-f0-9]{32}$/.test(projectId))
		throw new Error("invalid_recovery_scope");
	return scope + ":" + projectId;
}
function request<T>(value: IDBRequest<T>): Promise<T> {
	return new Promise((resolve, reject) => {
		value.onsuccess = () => resolve(value.result);
		value.onerror = () => reject(new Error("recovery_unavailable"));
	});
}
function complete(transaction: IDBTransaction): Promise<void> {
	return new Promise((resolve, reject) => {
		transaction.oncomplete = () => resolve();
		transaction.onerror = transaction.onabort = () =>
			reject(new Error("recovery_unavailable"));
	});
}

/** Browser storage is untrusted, and is never read before native confirmation. */
export function decodeDraft(
	value: unknown,
	scope: string,
	projectId: string,
): Draft {
	const record = readObject(value, 40);
	if (
		record.schema_version !== 1 ||
		record.scope !== scope ||
		record.project_id !== projectId ||
		record.key !== storageKey(scope, projectId)
	)
		throw new Error("invalid_recovery_record");
	const data = readObject(record.draft, 40);
	const baseline = readProject(data.baseline);
	if (baseline.id !== projectId) throw new Error("invalid_recovery_project");
	const history = readObject(data.history, 40);
	if (
		!Array.isArray(history.past) ||
		!Array.isArray(history.future) ||
		history.past.length > MAX_RECOVERY_HISTORY ||
		history.future.length > MAX_RECOVERY_HISTORY ||
		!Number.isSafeInteger(history.serial) ||
		typeof history.serial !== "number" ||
		history.serial < 0
	)
		throw new Error("invalid_recovery_history");
	const current = readObject(history.current);
	let pending: SaveIntent | null = null;
	if (data.pending !== null) {
		const intent = readObject(data.pending);
		if (
			typeof intent.key !== "string" ||
			typeof intent.body !== "string" ||
			typeof intent.expectedRevision !== "number" ||
			intent.expectedRevision !== baseline.revision ||
			intent.projectId !== projectId
		)
			throw new Error("invalid_recovery_intent");
		const inputs = readObject(intent.inputs);
		const command = readObject(JSON.parse(intent.body));
		const expected: JsonObject = {
			schema_version: 1,
			project_id: projectId,
			expected_revision: intent.expectedRevision,
			inputs,
			key: intent.key,
		};
		if (!sameJson(command, expected))
			throw new Error("invalid_recovery_intent");
		pending = {
			key: intent.key,
			projectId,
			expectedRevision: intent.expectedRevision,
			inputs,
			body: intent.body,
		};
	}
	const conflict = data.conflict === null ? null : readProject(data.conflict);
	if (
		conflict &&
		(conflict.id !== projectId || conflict.revision < baseline.revision)
	)
		throw new Error("invalid_recovery_conflict");
	return {
		baseline,
		history: {
			current,
			past: history.past.map((value) => readObject(value)),
			future: history.future.map((value) => readObject(value)),
			serial: history.serial,
		},
		pending,
		conflict,
	};
}
