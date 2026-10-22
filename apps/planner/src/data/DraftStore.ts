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
// Local recovery policy, never authority for an account/project or a saved run.
const DATABASE = "linker-planner-recovery-v1";
const STORE = "drafts";
const CREATIONS = "creations";
const MAX_RECOVERY_BYTES = 8 * 1024 * 1024;
const MAX_RECOVERY_HISTORY = 20;

export class DraftStore {
	private connection: Promise<IDBDatabase> | null = null;

	async readCreation(scope: string): Promise<string | null> {
		storageKey(scope, "0".repeat(32));
		const db = await this.open();
		const value = await request<unknown>(
			db.transaction(CREATIONS, "readonly").objectStore(CREATIONS).get(scope),
		);
		if (value === undefined) return null;
		const record = readObject(value);
		if (record.scope !== scope || typeof record.body !== "string")
			throw new Error("invalid_creation_recovery");
		validateCreation(record.body);
		return record.body;
	}

	async writeCreation(scope: string, body: string): Promise<void> {
		storageKey(scope, "0".repeat(32));
		validateCreation(body);
		const db = await this.open();
		const transaction = db.transaction(CREATIONS, "readwrite");
		const committed = complete(transaction);
		transaction.objectStore(CREATIONS).put({ scope, body });
		await committed;
	}

	async clearCreation(scope: string, body: string): Promise<void> {
		storageKey(scope, "0".repeat(32));
		validateCreation(body);
		const db = await this.open();
		const transaction = db.transaction(CREATIONS, "readwrite");
		const committed = complete(transaction);
		const store = transaction.objectStore(CREATIONS);
		const read = store.get(scope);
		read.onsuccess = () => {
			// A late acknowledgement must not erase a newer pending intent
			// written by another view in the same verified browser scope.
			if (read.result?.body === body) store.delete(scope);
		};
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
			const opened = indexedDB.open(DATABASE, 3);
			opened.onupgradeneeded = () => {
				if (!opened.result.objectStoreNames.contains(STORE))
					opened.result.createObjectStore(STORE, { keyPath: "key" });
				const drafts = opened.transaction?.objectStore(STORE);
				if (drafts && !drafts.indexNames.contains("project_id"))
					drafts.createIndex("project_id", "project_id", { unique: false });
				if (!opened.result.objectStoreNames.contains(CREATIONS))
					opened.result.createObjectStore(CREATIONS, { keyPath: "scope" });
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

function validateCreation(body: string): void {
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
