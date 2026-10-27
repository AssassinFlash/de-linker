import { DraftStore } from "../src/data/DraftStore.ts";
import { beginDraft } from "../src/domain/draft.ts";

const database = "linker-planner-recovery-v1";
const scope = "a".repeat(64),
	otherScope = "b".repeat(64);
const button = document.querySelector<HTMLButtonElement>("#run")!;
const status = document.querySelector<HTMLElement>("#status")!;
const results = document.querySelector<HTMLOListElement>("#results")!;
const creation = (title: string, key = crypto.randomUUID()) =>
	JSON.stringify({ schema_version: 1, title, inputs: {}, key });
const profileImport = (
	label: string,
	projectId = "1".repeat(32),
	key = crypto.randomUUID(),
) =>
	JSON.stringify({
		schema_version: 1,
		project_id: projectId,
		content_base64: btoa("time;power\n2024-01-01T00:00Z;1\n"),
		source_label: label,
		rights_note: "Created by this native browser fixture",
		key,
		mapping: {
			timestamp_column: "time",
			value_column: "power",
			measurement: "gross_load",
			value_kind: "interval_average_kw",
			timestamp_role: "start",
			timezone: "UTC",
			origin: "synthetic",
			interval_seconds: 900,
			delimiter: ";",
			decimal: ".",
			end_timestamp_column: null,
			fold_column: null,
			end_fold_column: null,
			offset_rule: "explicit_offset_precedes_naive_timezone",
			within_interval_assumption: "constant_mean_no_new_observations",
		},
	});
function equal(actual: unknown, expected: unknown): void {
	if (JSON.stringify(actual) !== JSON.stringify(expected))
		throw new Error("fixture_assertion_failed");
}
async function refuses(
	operation: Promise<unknown>,
	reason: string,
): Promise<void> {
	try {
		await operation;
	} catch (error) {
		if (error instanceof Error && error.message === reason) return;
		throw error;
	}
	throw new Error("expected_refusal_missing");
}
function open(version?: number): Promise<IDBDatabase> {
	return new Promise((resolve, reject) => {
		const request = indexedDB.open(database, version);
		request.onsuccess = () => resolve(request.result);
		request.onerror = () => reject(request.error);
	});
}
function remove(): Promise<void> {
	return new Promise((resolve, reject) => {
		const request = indexedDB.deleteDatabase(database);
		request.onsuccess = () => resolve();
		request.onerror = () => reject(request.error);
		request.onblocked = () => reject(new Error("fixture_cleanup_blocked"));
	});
}
function commit(transaction: IDBTransaction): Promise<void> {
	return new Promise((resolve, reject) => {
		transaction.oncomplete = () => resolve();
		transaction.onerror = transaction.onabort = () =>
			reject(new Error("fixture_transaction_failed"));
	});
}
async function fixture(name: string, run: () => Promise<void>): Promise<void> {
	await run();
	const result = document.createElement("li");
	result.textContent = "PASS · " + name;
	results.append(result);
}
button.addEventListener("click", async () => {
	button.disabled = true;
	status.textContent = "Running";
	results.replaceChildren();
	try {
		await remove();
		const oldBody = creation("Synthetic legacy creation");
		const project = {
			id: "1".repeat(32),
			title: "Synthetic stored project",
			revision: 1,
			input_sha256: "2".repeat(64),
			inputs: { value: 3 },
		};
		const oldDb = await new Promise<IDBDatabase>((resolve, reject) => {
			const request = indexedDB.open(database, 3);
			request.onupgradeneeded = () => {
				const drafts = request.result.createObjectStore("drafts", {
					keyPath: "key",
				});
				drafts.createIndex("project_id", "project_id", { unique: false });
				request.result.createObjectStore("creations", { keyPath: "scope" });
			};
			request.onsuccess = () => resolve(request.result);
			request.onerror = () => reject(request.error);
		});
		const tx = oldDb.transaction(["creations", "drafts"], "readwrite");
		const committed = commit(tx);
		tx.objectStore("creations").put({ scope, body: oldBody });
		tx.objectStore("drafts").put({
			schema_version: 1,
			key: scope + ":" + project.id,
			scope,
			project_id: project.id,
			draft: beginDraft(project),
			updated_at: 1,
		});
		await committed;
		const first = new DraftStore(),
			second = new DraftStore();
		await fixture(
			"blocked upgrade refuses visibly and the same store retries after the old page closes",
			async () => {
				await refuses(first.readCreations(scope), "recovery_blocked");
				oldDb.close();
				const upgraded = await open(5);
				upgraded.close();
				equal(
					(await first.readCreations(scope)).map((item) => item.body),
					[oldBody],
				);
			},
		);
		await fixture(
			"version 3 creation and project draft survive the atomic upgrade",
			async () => {
				equal((await first.read(scope, project.id))?.baseline, project);
				equal((await first.readCreations(scope))[0]?.body, oldBody);
			},
		);
		const a = creation("Synthetic parallel A"),
			b = creation("Synthetic parallel B");
		await fixture(
			"two independent connections retain both concurrent creation intents",
			async () => {
				await Promise.all([
					first.writeCreation(scope, a),
					second.writeCreation(scope, b),
				]);
				equal(
					new Set((await first.readCreations(scope)).map((item) => item.body))
						.size,
					3,
				);
				for (const body of [oldBody, a, b])
					equal(
						(await second.readCreations(scope)).some(
							(item) => item.body === body,
						),
						true,
					);
			},
		);
		await fixture(
			"a UUID cannot be overwritten with different bytes and a late acknowledgement cannot delete another intent",
			async () => {
				const changed = JSON.stringify({
					...JSON.parse(a),
					title: "Changed intent",
				});
				await refuses(
					second.writeCreation(scope, changed),
					"creation_intent_conflict",
				);
				await first.clearCreation(scope, changed);
				equal(
					(await second.readCreations(scope)).some((item) => item.body === a),
					true,
				);
				await Promise.all([
					first.clearCreation(scope, a),
					second.writeCreation(scope, b),
				]);
				equal(
					(await second.readCreations(scope)).some((item) => item.body === a),
					false,
				);
				equal(
					(await second.readCreations(scope)).some((item) => item.body === b),
					true,
				);
			},
		);
		await fixture(
			"scope isolation and acknowledgement remove only the matching migrated bytes",
			async () => {
				equal(await second.readCreations(otherScope), []);
				await second.writeCreation(
					otherScope,
					creation("Synthetic other scope"),
				);
				equal((await first.readCreations(scope)).length, 2);
				await first.clearCreation(scope, oldBody);
				equal(
					(await second.readCreations(scope)).map((item) => item.body),
					[b],
				);
				equal((await second.readCreations(otherScope)).length, 1);
			},
		);
		await fixture(
			"bounded recovery refuses a 129th intent without erasing the first 128",
			async () => {
				await first.clearCreation(scope, b);
				for (let index = 0; index < 128; index++)
					await first.writeCreation(
						scope,
						creation("Synthetic intent " + index),
					);
				await refuses(
					second.writeCreation(scope, creation("Over the recovery policy")),
					"recovery_storage_limit",
				);
				equal((await first.readCreations(scope)).length, 128);
			},
		);
		await fixture(
			"concurrent upload intents preserve exact bytes and stay isolated by project and native scope",
			async () => {
				const a = profileImport("Synthetic upload A"),
					b = profileImport("Synthetic upload B"),
					other = profileImport("Synthetic other project", "2".repeat(32));
				await Promise.all([
					first.writeProfileImport(scope, a),
					second.writeProfileImport(scope, b),
					second.writeProfileImport(scope, other),
					first.writeProfileImport(otherScope, a),
				]);
				equal(
					(await first.readProfileImports(scope, project.id))
						.map((record) => record.body)
						.sort(),
					[a, b].sort(),
				);
				equal(
					(await first.readProfileImports(scope, "2".repeat(32))).map(
						(record) => record.body,
					),
					[other],
				);
				equal(
					(await first.readProfileImports(otherScope, project.id)).map(
						(record) => record.body,
					),
					[a],
				);
				const changed = JSON.stringify({
					...JSON.parse(a),
					source_label: "Different bytes for one key",
				});
				await refuses(
					second.writeProfileImport(scope, changed),
					"profile_intent_conflict",
				);
				await second.clearProfileImport(scope, changed);
				equal((await first.readProfileImports(scope, project.id)).length, 2);
				await Promise.all([
					first.clearProfileImport(scope, a),
					second.writeProfileImport(scope, b),
				]);
				equal(
					(await first.readProfileImports(scope, project.id)).map(
						(record) => record.body,
					),
					[b],
				);
				equal(
					(await first.readProfileImports(otherScope, project.id)).map(
						(record) => record.body,
					),
					[a],
				);
				equal((await first.read(scope, project.id))?.baseline, project);
			},
		);
		await fixture(
			"upload recovery refuses its capacity limit without erasing unconfirmed requests",
			async () => {
				const boundedScope = "c".repeat(64);
				for (let i = 0; i < 32; i++)
					await first.writeProfileImport(
						boundedScope,
						profileImport("Synthetic bounded " + i),
					);
				await refuses(
					second.writeProfileImport(
						boundedScope,
						profileImport("Synthetic over limit"),
					),
					"recovery_storage_limit",
				);
				equal(
					(await first.readProfileImports(boundedScope, project.id)).length,
					32,
				);
			},
		);
		await fixture(
			"invalid legacy data stays intact and is reported instead of being silently dropped",
			async () => {
				await remove();
				const invalid = creation("");
				const old = await new Promise<IDBDatabase>((resolve, reject) => {
					const request = indexedDB.open(database, 3);
					request.onupgradeneeded = () =>
						request.result.createObjectStore("creations", { keyPath: "scope" });
					request.onsuccess = () => resolve(request.result);
					request.onerror = () => reject(request.error);
				});
				const transaction = old.transaction("creations", "readwrite");
				const committed = commit(transaction);
				transaction.objectStore("creations").put({ scope, body: invalid });
				await committed;
				old.close();
				await refuses(
					new DraftStore().readCreations(scope),
					"invalid_creation_recovery",
				);
				const restored = await open();
				const raw = await new Promise<{ body: string }>((resolve, reject) => {
					const read = restored
						.transaction("creations", "readonly")
						.objectStore("creations")
						.get(scope);
					read.onsuccess = () => resolve(read.result);
					read.onerror = () => reject(read.error);
				});
				equal(raw.body, invalid);
				restored.close();
			},
		);
		await remove();
		status.textContent = `Passed · ${results.children.length} native IndexedDB fixtures`;
	} catch (error) {
		status.textContent =
			"FAILED · " +
			(error instanceof Error ? error.message : "unknown fixture error");
	} finally {
		button.disabled = false;
	}
});
