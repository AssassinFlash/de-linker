import type { PlannerClient } from "./PlannerClient.ts";
import { readObject } from "./readProtocol.ts";

/** One scope-bound Woo read serves module and equipment projections. */
export function currentProductQuery(
	client: PlannerClient,
	scope: string,
	active: boolean,
) {
	return {
		queryKey: ["planner-current-products", scope] as const,
		enabled: active && client.isCurrentScope(scope),
		retry: false as const,
		staleTime: 0,
		refetchOnMount: "always" as const,
		refetchOnWindowFocus: false,
		refetchOnReconnect: false,
		queryFn: async ({ signal }: { signal: AbortSignal }) =>
			readObject(
				await client.query(
					"products/current",
					{ schema_version: 1 },
					scope,
					signal,
				),
			),
	};
}
