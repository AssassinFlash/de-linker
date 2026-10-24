import { useQuery } from "@tanstack/react-query";
import type { PlannerClient } from "./PlannerClient.ts";
import { readModuleTemplates } from "./moduleTemplates.ts";

export function useModuleTemplates(
	client: PlannerClient,
	scope: string,
	active = true,
) {
	return useQuery({
		queryKey: ["planner-module-templates", scope],
		enabled: active && client.isCurrentScope(scope),
		retry: false,
		staleTime: 0,
		refetchOnMount: "always",
		refetchOnWindowFocus: false,
		refetchOnReconnect: false,
		queryFn: async ({ signal }) =>
			readModuleTemplates(
				await client.query(
					"products/current",
					{ schema_version: 1 },
					scope,
					signal,
				),
			),
	});
}
