import type { GeometryDocument, PanelPose } from "../../domain/geometry.ts";
import { __, sprintf } from "../../i18n.ts";

/** Explicit selection and sequence; no electrical destination is inferred. */
export function PvModuleSelection({
	geometry,
	poses,
	selected,
	labels,
	assigned,
	disabled,
	change,
}: {
	geometry: GeometryDocument;
	poses: readonly PanelPose[];
	selected: string[];
	labels: ReadonlyMap<string, string>;
	assigned: ReadonlyMap<string, string>;
	disabled: boolean;
	change: (ids: string[]) => void;
}) {
	const byId = new Map(poses.map((p) => [p.id, p]));
	const select = (modules: readonly PanelPose[]) =>
		change([
			...new Set([
				...selected,
				...modules.filter((p) => !assigned.has(p.id)).map((p) => p.id),
			]),
		]);
	const order = (axis: "row" | "column") => {
		const arrays = new Map(geometry.arrays.map((a, i) => [a.id, i]));
		change(
			[...selected].sort((a, b) => {
				const first = byId.get(a),
					second = byId.get(b);
				if (!first || !second) return Number(!first) - Number(!second);
				return (
					arrays.get(first.array_id)! - arrays.get(second.array_id)! ||
					first[axis] - second[axis] ||
					first[axis === "row" ? "column" : "row"] -
						second[axis === "row" ? "column" : "row"]
				);
			}),
		);
	};
	const move = (index: number, offset: number) => {
		const next = [...selected],
			other = index + offset;
		if (other < 0 || other >= next.length) return;
		[next[index], next[other]] = [next[other]!, next[index]!];
		change(next);
	};
	return (
		<>
			<p>
				{__(
					"Choose modules and review their order to match your planned wiring. Enter the MPPT and inverter input for each string.",
					"linker-tools",
				)}
			</p>
			{geometry.arrays.map((array, index) => {
				const modules = poses.filter((p) => p.array_id === array.id);
				const free = modules.filter((p) => !assigned.has(p.id));
				const rows = [...new Set(modules.map((p) => p.row))];
				const arrayLabel = sprintf(
					__("Array %1$d · %2$s", "linker-tools"),
					index + 1,
					array.name,
				);
				return (
					<details key={array.id}>
						<summary>{arrayLabel}</summary>
						<p>
							{sprintf(
								__("Roof: %s", "linker-tools"),
								geometry.roofs.find((r) => r.id === array.roof_id)?.name ??
									array.roof_id,
							)}
						</p>
						<p role="status">
							{sprintf(
								__("%1$d available · %2$d selected", "linker-tools"),
								free.length,
								free.filter((pose) => selected.includes(pose.id)).length,
							)}
						</p>
						<div className="lp-inline-actions">
							<button
								type="button"
								className="lp-text-button"
								disabled={
									disabled || !free.some((p) => !selected.includes(p.id))
								}
								aria-label={sprintf(
									__("Select available modules in %s", "linker-tools"),
									arrayLabel,
								)}
								onClick={() => select(modules)}
							>
								{__("Select all available modules", "linker-tools")}
							</button>
							<button
								type="button"
								className="lp-text-button"
								disabled={
									disabled || !modules.some((p) => selected.includes(p.id))
								}
								onClick={() =>
									change(
										selected.filter(
											(id) => byId.get(id)?.array_id !== array.id,
										),
									)
								}
							>
								{__("Clear this array selection", "linker-tools")}
							</button>
						</div>
						<div className="lp-inline-actions">
							{rows.map((row) => (
								<button
									key={row}
									type="button"
									className="lp-text-button"
									disabled={
										disabled ||
										!free.some((p) => p.row === row && !selected.includes(p.id))
									}
									aria-label={sprintf(
										__("Select row %1$d in %2$s", "linker-tools"),
										row + 1,
										arrayLabel,
									)}
									onClick={() => select(modules.filter((p) => p.row === row))}
								>
									{sprintf(__("Select row %d", "linker-tools"), row + 1)}
								</button>
							))}
						</div>
						<details>
							<summary>
								{__("Choose individual modules", "linker-tools")}
							</summary>
							<div className="lp-scenario-fields">
								{modules.map((pose) => (
									<label className="lp-field" key={pose.id}>
										<span>
											<input
												type="checkbox"
												disabled={disabled || assigned.has(pose.id)}
												checked={
													selected.includes(pose.id) && !assigned.has(pose.id)
												}
												onChange={(event) =>
													change(
														event.currentTarget.checked
															? [...new Set([...selected, pose.id])]
															: selected.filter((id) => id !== pose.id),
													)
												}
											/>
											{labels.get(pose.id)}
										</span>
										{assigned.has(pose.id) && (
											<small>{assigned.get(pose.id)}</small>
										)}
									</label>
								))}
							</div>
						</details>
					</details>
				);
			})}
			{selected.length > 0 && (
				<details>
					<summary>
						{sprintf(
							__("Review selected order (%d modules)", "linker-tools"),
							selected.length,
						)}
					</summary>
					<p>
						{__(
							"The selected sequence is used when you add modules. The roof layout stays unchanged.",
							"linker-tools",
						)}
					</p>
					<div className="lp-inline-actions">
						<button
							type="button"
							className="lp-text-button"
							disabled={disabled}
							onClick={() => order("row")}
						>
							{__("Order by rows", "linker-tools")}
						</button>
						<button
							type="button"
							className="lp-text-button"
							disabled={disabled}
							onClick={() => order("column")}
						>
							{__("Order by columns", "linker-tools")}
						</button>
						<button
							type="button"
							className="lp-text-button"
							disabled={disabled}
							onClick={() => change([...selected].reverse())}
						>
							{__("Reverse order", "linker-tools")}
						</button>
						<button
							type="button"
							className="lp-text-button"
							disabled={disabled}
							onClick={() => change([])}
						>
							{__("Clear selection", "linker-tools")}
						</button>
					</div>
					<ol>
						{selected.map((id, index) => {
							const label = labels.get(id) ?? id;
							return (
								<li key={id}>
									<span>{label}</span>
									{assigned.has(id) && <strong> · {assigned.get(id)}</strong>}
									<div className="lp-inline-actions">
										<button
											type="button"
											className="lp-text-button"
											aria-label={sprintf(
												__("Move %s earlier", "linker-tools"),
												label,
											)}
											disabled={disabled || index === 0}
											onClick={() => move(index, -1)}
										>
											{__("Earlier", "linker-tools")}
										</button>
										<button
											type="button"
											className="lp-text-button"
											aria-label={sprintf(
												__("Move %s later", "linker-tools"),
												label,
											)}
											disabled={disabled || index === selected.length - 1}
											onClick={() => move(index, 1)}
										>
											{__("Later", "linker-tools")}
										</button>
										<button
											type="button"
											className="lp-text-button"
											aria-label={sprintf(
												__("Remove %s from selection", "linker-tools"),
												label,
											)}
											disabled={disabled}
											onClick={() =>
												change(selected.filter((value) => value !== id))
											}
										>
											{__("Remove", "linker-tools")}
										</button>
									</div>
								</li>
							);
						})}
					</ol>
				</details>
			)}
		</>
	);
}
