import { useEffect, useState } from "react";
import type {
	InstallationInputs,
	PvStringLink,
	PvStringLinkStatus,
	PvStringReconciliation,
} from "../../domain/installation.ts";
import { readInstallation } from "../../domain/installation.ts";
import type { PvString, PvStringPlan } from "../../domain/pvStrings.ts";
import { formatDecimal } from "../../domain/decimal.ts";
import { __, sprintf } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";

function stringLabel(string: PvString): string {
	return sprintf(
		__("MPPT %1$d · input %2$d · %3$d modules", "linker-tools"),
		string.mppt,
		string.input,
		string.module_ids.length,
	);
}
function statusLabel(status: PvStringLinkStatus): string {
	return {
		linked: __("String linked to circuit", "linker-tools"),
		unlinked: __("No circuit selected", "linker-tools"),
		stale_string: __("Saved string unavailable", "linker-tools"),
		stale_circuit: __("Saved circuit unavailable", "linker-tools"),
		wrong_circuit_kind: __("Choose a PV DC circuit", "linker-tools"),
		inverter_endpoint_unresolved: __(
			"Inverter connection needs review",
			"linker-tools",
		),
	}[status];
}

export function PvStringLinks({
	plan,
	savedInstallation,
	savedStrings,
	stringPlanChanged,
	review,
	locale,
	disabled,
	change,
	onValidity,
}: {
	plan: InstallationInputs;
	savedInstallation: InstallationInputs;
	savedStrings: PvStringPlan | null;
	stringPlanChanged: boolean;
	review: PvStringReconciliation | null;
	locale: string;
	disabled: boolean;
	change: (value: InstallationInputs) => boolean;
	onValidity: (valid: boolean) => void;
}) {
	const links = plan.pv_string_links ?? [],
		enabled = plan.pv_string_links !== undefined,
		strings = savedStrings?.strings ?? [],
		circuits = plan.circuits.filter(
			(c) =>
				c.kind === "pv_dc" &&
				savedInstallation.circuits.some((saved) => saved.id === c.id),
		);
	const [editing, setEditing] = useState<PvStringLink | null | undefined>(),
		[stringId, setStringId] = useState(""),
		[circuitId, setCircuitId] = useState(""),
		[failed, setFailed] = useState(false);
	useEffect(() => {
		onValidity(editing === undefined);
		return () => onValidity(true);
	}, [editing, onValidity]);
	function apply(next: InstallationInputs): boolean {
		try {
			const accepted = change(readInstallation(next));
			setFailed(!accepted);
			return accepted;
		} catch {
			setFailed(true);
			return false;
		}
	}
	function edit(link: PvStringLink | null) {
		setEditing(link);
		setStringId(link?.string_id ?? "");
		setCircuitId(link?.circuit_id ?? "");
		setFailed(false);
	}
	const otherLinks = links.filter(
			(link) => link.string_id !== editing?.string_id,
		),
		availableStrings = strings.filter(
			(s) => !otherLinks.some((link) => link.string_id === s.id),
		),
		availableCircuits = circuits.filter(
			(c) => !otherLinks.some((link) => link.circuit_id === c.id),
		),
		canApply =
			!disabled &&
			!stringPlanChanged &&
			availableStrings.some((s) => s.id === stringId) &&
			availableCircuits.some((c) => c.id === circuitId);
	return (
		<section className="lp-scenario-block">
			<h3>{__("PV string connections", "linker-tools")}</h3>
			<p className="lp-profile-help">
				{__(
					"Link saved PV strings to recorded circuits. Cable sizes, conductor counts, connector compatibility and electrical approval require separate checks.",
					"linker-tools",
				)}
			</p>
			<label className="lp-check">
				<input
					type="checkbox"
					checked={enabled}
					disabled={disabled || editing !== undefined || links.length > 0}
					onChange={(event) => {
						if (event.target.checked) apply({ ...plan, pv_string_links: [] });
						else {
							const next = { ...plan };
							delete next.pv_string_links;
							apply(next);
						}
					}}
				/>
				{__("Review PV string connections", "linker-tools")}
			</label>
			{links.length > 0 && (
				<p className="lp-profile-help">
					{__(
						"Remove the links before turning off this review.",
						"linker-tools",
					)}
				</p>
			)}
			{enabled && (
				<>
					{(!strings.length || !circuits.length || stringPlanChanged) && (
						<Notice>
							{__(
								"Save the PV string plan and PV DC circuits before linking them. Changes to the string plan must be saved before reviewing links.",
								"linker-tools",
							)}
						</Notice>
					)}
					{links.map((link) => {
						const string = strings.find((s) => s.id === link.string_id),
							circuit = plan.circuits.find((c) => c.id === link.circuit_id);
						return (
							<div className="lp-selected-profile" key={link.string_id}>
								<div>
									<strong>
										{string
											? stringLabel(string)
											: sprintf(
													__("Missing PV string: %s", "linker-tools"),
													link.string_id,
												)}
									</strong>
									<p>
										{circuit?.name ??
											sprintf(
												__("Missing circuit: %s", "linker-tools"),
												link.circuit_id,
											)}
									</p>
								</div>
								<div className="lp-inline-actions">
									<button
										type="button"
										className="lp-text-button"
										disabled={disabled || editing !== undefined}
										onClick={() => edit(link)}
									>
										{__("Edit", "linker-tools")}
									</button>
									<button
										type="button"
										className="lp-text-button"
										disabled={disabled || editing !== undefined}
										onClick={() =>
											apply({
												...plan,
												pv_string_links: links.filter(
													(old) => old.string_id !== link.string_id,
												),
											})
										}
									>
										{__("Remove link", "linker-tools")}
									</button>
								</div>
							</div>
						);
					})}
					{failed && (
						<Notice error>
							{__(
								"The link could not be applied. Check the selected string and circuit.",
								"linker-tools",
							)}
						</Notice>
					)}
					{editing !== undefined ? (
						<form
							onSubmit={(event) => {
								event.preventDefault();
								if (
									canApply &&
									apply({
										...plan,
										pv_string_links: [
											...otherLinks,
											{ string_id: stringId, circuit_id: circuitId },
										],
									})
								)
									setEditing(undefined);
							}}
						>
							<div className="lp-geometry-fields">
								<label className="lp-field">
									<span>{__("PV string", "linker-tools")}</span>
									<select
										required
										value={stringId}
										onChange={(event) => setStringId(event.target.value)}
										disabled={disabled || stringPlanChanged}
									>
										<option value="">
											{__("Choose a saved PV string", "linker-tools")}
										</option>
										{stringId &&
											!availableStrings.some((s) => s.id === stringId) && (
												<option value={stringId} disabled>
													{sprintf(
														__("Missing PV string: %s", "linker-tools"),
														stringId,
													)}
												</option>
											)}
										{availableStrings.map((s) => (
											<option value={s.id} key={s.id}>
												{stringLabel(s)}
											</option>
										))}
									</select>
								</label>
								<label className="lp-field">
									<span>{__("Circuit", "linker-tools")}</span>
									<select
										required
										value={circuitId}
										onChange={(event) => setCircuitId(event.target.value)}
										disabled={disabled || stringPlanChanged}
									>
										<option value="">
											{__("Choose a saved PV DC circuit", "linker-tools")}
										</option>
										{circuitId &&
											!availableCircuits.some((c) => c.id === circuitId) && (
												<option value={circuitId} disabled>
													{sprintf(
														__("Unavailable PV DC circuit: %s", "linker-tools"),
														circuitId,
													)}
												</option>
											)}
										{availableCircuits.map((c) => (
											<option value={c.id} key={c.id}>
												{c.name}
											</option>
										))}
									</select>
								</label>
							</div>
							<div className="lp-inline-actions">
								<button className="lp-button" disabled={!canApply}>
									{__("Apply changes", "linker-tools")}
								</button>
								<button
									type="button"
									className="lp-text-button"
									onClick={() => setEditing(undefined)}
								>
									{__("Cancel", "linker-tools")}
								</button>
							</div>
						</form>
					) : (
						<button
							type="button"
							className="lp-button lp-button-secondary"
							disabled={
								disabled ||
								stringPlanChanged ||
								!availableStrings.length ||
								!availableCircuits.length
							}
							onClick={() => edit(null)}
						>
							{__("Link string to circuit", "linker-tools")}
						</button>
					)}
					{review && (
						<>
							{review.plan_status !== "available" && (
								<Notice>
									{review.plan_status === "missing"
										? __(
												"No saved PV string plan is available for this review.",
												"linker-tools",
											)
										: __(
												"The saved PV string plan contains no strings.",
												"linker-tools",
											)}
								</Notice>
							)}
							<div className="lp-table-scroll">
								<table className="lp-data-table">
									<thead>
										<tr>
											<th>{__("PV string", "linker-tools")}</th>
											<th>{__("Circuit", "linker-tools")}</th>
											<th>{__("Connection points", "linker-tools")}</th>
											<th>{__("Status", "linker-tools")}</th>
											<th>{__("Recorded cable runs", "linker-tools")}</th>
										</tr>
									</thead>
									<tbody>
										{review.rows.map((row) => (
											<tr key={row.string_id}>
												<td>
													{strings.find((s) => s.id === row.string_id)
														? stringLabel(
																strings.find((s) => s.id === row.string_id)!,
															)
														: row.string_id}
												</td>
												<td>
													{plan.circuits.find((c) => c.id === row.circuit_id)
														?.name ??
														row.circuit_id ??
														"—"}
												</td>
												<td>
													{row.endpoints
														.map((e) => {
															const instance = plan.instances.find(
																(i) => i.id === e.instance_id,
															);
															return `${instance?.name ?? e.instance_id}: ${instance?.ports.find((p) => p.id === e.port_id)?.name ?? e.port_id}`;
														})
														.join(" → ") || "—"}
												</td>
												<td>{statusLabel(row.status)}</td>
												<td>
													{row.cable_runs
														.map(
															(c) =>
																`${c.name}: ${c.quantity === null ? "—" : formatDecimal(c.quantity, locale) + " m"}`,
														)
														.join("; ") ||
														__("No cable runs recorded", "linker-tools")}
												</td>
											</tr>
										))}
									</tbody>
								</table>
							</div>
						</>
					)}
				</>
			)}
		</section>
	);
}
