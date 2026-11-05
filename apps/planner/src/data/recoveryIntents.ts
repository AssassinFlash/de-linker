import type {
	CreationIntent,
	DraftStore,
	ProfileImportIntent,
} from "./DraftStore.ts";

export interface ScopedCreation extends CreationIntent {
	readonly scope: string;
}
export interface ScopedProfileImport extends ProfileImportIntent {
	readonly scope: string;
}

/** These scopes must come from the current native account grant read.
 * Aggregate resource bounds match DraftStore's single-scope policies. Hitting
 * one reports an error; stored records are never truncated or deleted.
 */
export async function creationIntents(
	store: DraftStore,
	scopes: readonly string[],
): Promise<readonly ScopedCreation[]> {
	const records: ScopedCreation[] = [];
	let bytes = 0;
	for (const scope of new Set(scopes)) {
		for (const intent of await store.readCreations(scope)) {
			bytes += new TextEncoder().encode(intent.body).length;
			if (records.length >= 128 || bytes > 8 * 1024 * 1024)
				throw new Error("recovery_storage_limit");
			records.push({ ...intent, scope });
		}
	}
	return records.sort(
		(a, b) =>
			a.createdAt - b.createdAt || intentId(a).localeCompare(intentId(b)),
	);
}

export async function profileIntents(
	store: DraftStore,
	scopes: readonly string[],
	projectId: string,
): Promise<readonly ScopedProfileImport[]> {
	const records: ScopedProfileImport[] = [];
	let bytes = 0;
	for (const scope of new Set(scopes)) {
		for (const intent of await store.readProfileImports(scope, projectId)) {
			bytes += new TextEncoder().encode(intent.body).length;
			if (records.length >= 32 || bytes > 32 * 1024 * 1024)
				throw new Error("recovery_storage_limit");
			records.push({ ...intent, scope });
		}
	}
	return records.sort(
		(a, b) =>
			a.createdAt - b.createdAt || intentId(a).localeCompare(intentId(b)),
	);
}

export function intentId(intent: {
	readonly scope: string;
	readonly key: string;
}): string {
	return intent.scope + ":" + intent.key;
}

/** After a project is deleted, its stored creation-recovery hints are stale
 * retries whose replay names a project that no longer exists. Intents do not
 * record the resulting project id, so the stored command's title identifies
 * them. A title another listed project still uses is ambiguous: that intent
 * may be a live, unsent creation of its own, so it is left untouched and the
 * workspace keeps offering it. Clearing a hint never removes server data. */
export async function clearCreationsForTitle(
	store: DraftStore,
	scopes: readonly string[],
	title: string,
	remainingTitles: readonly string[],
): Promise<void> {
	if (remainingTitles.includes(title)) return;
	for (const intent of await creationIntents(store, scopes)) {
		if (intent.title === title) {
			await store.clearCreation(intent.scope, intent.body);
		}
	}
}
