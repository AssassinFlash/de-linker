import type { PlannerClient } from "./PlannerClient.ts";
import { ApiError } from "./protocol.ts";
import { readObject } from "./readProtocol.ts";

/** Native account grants, not browser-selected prior identities. */
export async function recoveryScopes(
	client: PlannerClient,
	scope: string,
	signal?: AbortSignal,
): Promise<readonly string[]> {
	const scopes = new Set([scope]);
	let after: string | null = null;
	do {
		const page = readObject(
			await client.query(
				"recovery/scopes",
				{ schema_version: 1, after },
				scope,
				signal,
			),
		);
		if (
			!client.isCurrentScope(scope) ||
			Object.keys(page).sort().join() !== "next,schema_version,scopes" ||
			page.schema_version !== 1 ||
			!Array.isArray(page.scopes) ||
			page.scopes.length > 32 || // Matches native RecoveryScopes::PAGE_SIZE; transport policy.
			(page.next !== null && typeof page.next !== "string")
		)
			throw new ApiError(502, "invalid_recovery_scopes");
		let previous = after ?? "";
		for (const entry of page.scopes) {
			if (
				typeof entry !== "string" ||
				!/^[a-f0-9]{64}$/.test(entry) ||
				entry <= previous
			)
				throw new ApiError(502, "invalid_recovery_scopes");
			scopes.add(entry);
			previous = entry;
		}
		if (
			page.next !== null &&
			(page.scopes.length !== 32 || page.next !== previous)
		)
			throw new ApiError(502, "invalid_recovery_scopes");
		after = page.next as string | null;
	} while (after !== null);
	return [...scopes];
}
