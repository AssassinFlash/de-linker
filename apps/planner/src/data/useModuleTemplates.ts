import { useQuery } from "@tanstack/react-query";
import type { PlannerClient } from "./PlannerClient.ts";
import { readModuleTemplates } from "./moduleTemplates.ts";
import { currentProductQuery } from "./currentProductQuery.ts";

export function useModuleTemplates(
	client: PlannerClient,
	scope: string,
	active = true,
) {
	return useQuery({
		...currentProductQuery(client, scope, active),
		select: readModuleTemplates,
	});
}
