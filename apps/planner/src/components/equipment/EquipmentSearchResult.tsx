import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { PlanningRun } from "../../data/planningProtocol.ts";
import type { JsonObject } from "../../data/protocol.ts";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import type { EquipmentCandidate } from "../../data/equipmentSearch.ts";
import { readEquipmentCandidate } from "../../data/equipmentSearch.ts";
import { readObject } from "../../data/readProtocol.ts";
import { EquipmentResult } from "./EquipmentResult.tsx";
import { equipmentStatus } from "./equipmentLabels.ts";
import { __ } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";

export function EquipmentSearchResult({
	run,
	locale,
	dirty,
	confirmedRevision,
	client,
	scope,
	disabled,
	apply,
	onError,
	plantActive = false,
}: {
	run: PlanningRun;
	locale: string;
	dirty: boolean;
	confirmedRevision: number;
	client: PlannerClient;
	scope: string;
	disabled: boolean;
	apply: (candidate: EquipmentCandidate) => Promise<void>;
	onError: (cause: unknown) => void;
	plantActive?: boolean;
}) {
	const search = run.result ? readObject(run.result.search) : null;
	const candidates = (search?.candidates ?? []) as EquipmentCandidate[];
	const products = new Map(
		((search?.products ?? []) as JsonObject[]).map((p) => [
			p.canonical_product_id,
			p,
		]),
	);
	const [selected, setSelected] = useState<string | null>(null),
		[busy, setBusy] = useState(false);
	const candidate = candidates.find((c) => c.id === selected) ?? candidates[0];
	const detail = useQuery({
		queryKey: ["equipment-candidate", scope, run.id, candidate?.id],
		enabled: !!candidate && client.isCurrentScope(scope),
		retry: false,
		staleTime: Infinity,
		refetchOnWindowFocus: false,
		queryFn: async ({ signal }) =>
			readEquipmentCandidate(
				await client.query(
					"equipment/candidates/read",
					{ schema_version: 1, run_id: run.id, candidate_id: candidate!.id },
					scope,
					signal,
				),
				run.id,
				candidate!,
			),
	});
	const names = (c: EquipmentCandidate) =>
		[c.selection.inverter_product_id, c.selection.battery_product_id]
			.filter((id) => id !== null)
			.map((id) => {
				const p = products.get(id);
				return p ? `${p.brand} ${p.model}` : "—";
			})
			.join(" + ");
	const applySelected = async () => {
		if (!candidate || busy || disabled || plantActive) return;
		setBusy(true);
		try {
			await apply(candidate);
		} catch (cause) {
			if (client.isCurrentScope(scope)) onError(cause);
		} finally {
			if (client.isCurrentScope(scope)) setBusy(false);
		}
	};
	return (
		<EquipmentResult
			run={run}
			locale={locale}
			dirty={dirty}
			confirmedRevision={confirmedRevision}
			assessmentOverride={detail.data ?? null}
		>
			{search && (
				<>
					{plantActive && (
						<Notice>
							{__(
								"This search covers a single system. Choose products within each system when editing a multi-system plan.",
								"linker-tools",
							)}
						</Notice>
					)}
					<p>
						{search.completion === "budget_exhausted"
							? __(
									"Search incomplete: the search limit was reached. Some configurations remain unchecked.",
									"linker-tools",
								)
							: __("Search complete within the stated scope.", "linker-tools")}
					</p>
					<details className="lp-comparison">
						<summary>{__("Search scope", "linker-tools")}</summary>
						<p>
							{__(
								"This search assesses combinations of one inverter and one external battery assembly. Parallel inverter systems, multiple battery ports and integrated storage systems require separate assessment.",
								"linker-tools",
							)}
						</p>
					</details>
					<p>
						{__("Combinations assessed", "linker-tools")}:{" "}
						{new Intl.NumberFormat(locale).format(candidates.length)}
					</p>
					{Object.values(readObject(readObject(search.coverage).gaps)).some(
						(v) => typeof v === "number" && v > 0,
					) && (
						<Notice>
							{__(
								"Some products or combinations lack the supporting data needed for this search.",
								"linker-tools",
							)}
						</Notice>
					)}
					{candidates.length === 0 ? (
						<Notice>
							{__(
								"No combinations were found using the available documented configurations.",
								"linker-tools",
							)}
						</Notice>
					) : (
						<label className="lp-field">
							<span>{__("Equipment combination", "linker-tools")}</span>
							<select
								value={candidate?.id ?? ""}
								onChange={(event) => {
									setSelected(event.currentTarget.value);
								}}
							>
								{["satisfied", "unresolved", "violated"]
									.filter((status) =>
										candidates.some((c) => c.status === status),
									)
									.map((status) => (
										<optgroup key={status} label={equipmentStatus(status)}>
											{candidates
												.filter((c) => c.status === status)
												.map((c) => (
													<option key={c.id} value={c.id}>
														{names(c)} ·{" "}
														{__("Battery modules per stack", "linker-tools")}:{" "}
														{c.selection.modules_per_stack ?? "—"}
													</option>
												))}
										</optgroup>
									))}
							</select>
						</label>
					)}
					{detail.error && (
						<Notice error>
							{__(
								"The combination details could not be loaded.",
								"linker-tools",
							)}
						</Notice>
					)}
					{candidate && (
						<button
							className="lp-button"
							type="button"
							disabled={
								disabled ||
								busy ||
								!detail.data ||
								detail.isFetching ||
								plantActive
							}
							onClick={() => void applySelected()}
						>
							{__("Use this combination in the project", "linker-tools")}
						</button>
					)}
				</>
			)}
		</EquipmentResult>
	);
}
