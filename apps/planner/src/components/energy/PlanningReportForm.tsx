import { isEnergyTask } from "../../data/readEnergyResult.ts";
import { useEffect, useRef, useState } from "react";
import type { RunSummary } from "../../data/planningProtocol.ts";
import type { ReportOptions } from "../../data/planningReport.ts";
import { __, sprintf } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";

export function PlanningReportForm({
	runs,
	locale,
	hasCandidate,
	hasInstallation = false,
	disabled,
	generate,
}: {
	runs: readonly RunSummary[];
	locale: string;
	hasCandidate: boolean;
	hasInstallation?: boolean;
	disabled: boolean;
	generate: (options: ReportOptions) => Promise<void>;
}) {
	const [energy, setEnergy] = useState(""),
		[pv, setPv] = useState(""),
		[equipment, setEquipment] = useState(""),
		[logo, setLogo] = useState<string | null>(null),
		[error, setError] = useState(false),
		[reading, setReading] = useState(false);
	const reader = useRef<FileReader | null>(null);
	const [installation, setInstallation] = useState(false);
	const [certificates, setCertificates] = useState(false);
	useEffect(() => () => reader.current?.abort(), []);
	const [chosenRows, setChosenRows] = useState<Record<string, RunSummary>>({});
	// Keep only the three explicit selections across history pages.
	const completed = [
		...new Map(
			[...runs, ...Object.values(chosenRows)]
				.filter((run) => run.state === "succeeded")
				.map((run) => [run.id, run]),
		).values(),
	];
	const choose = (
		kind: string,
		value: string,
		set: (v: string) => void,
		label: string,
	) => (
		<label className="lp-field">
			<span>{label}</span>
			<select
				value={value}
				disabled={disabled}
				onChange={(event) => {
					const id = event.currentTarget.value;
					set(id);
					setChosenRows((previous) => {
						const next = { ...previous };
						const found = completed.find((row) => row.id === id);
						if (found) next[kind] = found;
						else delete next[kind];
						return next;
					});
				}}
			>
				<option value="">{__("Not included", "linker-tools")}</option>
				{completed
					.filter((run) =>
						kind === "single_ac_energy_replay_v1"
							? isEnergyTask(run.task_kind)
							: run.task_kind === kind,
					)
					.map((run) => (
						<option key={run.id} value={run.id}>
							{sprintf(
								__("Input revision %s", "linker-tools"),
								String(run.revision),
							)}{" "}
							·{" "}
							{new Intl.DateTimeFormat(locale, {
								dateStyle: "short",
								timeStyle: "short",
							}).format(run.created_at * 1000)}
						</option>
					))}
			</select>
		</label>
	);
	const options: ReportOptions = {
		locale: locale.startsWith("de") ? "de" : "en",
		energy_run_id: energy || null,
		pv_run_id: pv || null,
		equipment_run_id: equipment || null,
		logo,
		...(installation && hasInstallation ? { include_installation: true } : {}),
		...(certificates && (hasCandidate || equipment)
			? { inspect_certificate_declarations: true }
			: {}),
	};
	return (
		<section className="lp-scenario-block">
			<h3>{__("Planning report", "linker-tools")}</h3>
			<p>
				{__(
					"Choose the saved results to include. Save project changes before generating the report.",
					"linker-tools",
				)}
			</p>
			<div className="lp-scenario-fields">
				{hasInstallation && (
					<label className="lp-field">
						<span>
							<input
								type="checkbox"
								checked={installation}
								disabled={disabled}
								onChange={(e) => setInstallation(e.currentTarget.checked)}
							/>
							{__(
								"Include installation routes from the saved project",
								"linker-tools",
							)}
						</span>
					</label>
				)}
				{choose(
					"single_ac_energy_replay_v1",
					energy,
					setEnergy,
					__("Energy calculation", "linker-tools"),
				)}
				{choose(
					"prepare_roof_pv_reference_v1",
					pv,
					setPv,
					__("PV generation", "linker-tools"),
				)}
				{hasCandidate ? (
					<p>
						{__(
							"The report includes the equipment combination selected for this project.",
							"linker-tools",
						)}
					</p>
				) : (
					choose(
						"qualify_woo_equipment_v1",
						equipment,
						setEquipment,
						__("Equipment checks", "linker-tools"),
					)
				)}
				{(hasCandidate || equipment) && (
					<label className="lp-field">
						<span>
							<input
								type="checkbox"
								checked={certificates}
								disabled={disabled}
								onChange={(e) => setCertificates(e.currentTarget.checked)}
							/>
							{__(
								"Include information from the linked certificate files",
								"linker-tools",
							)}
						</span>
						<small>
							{__(
								"If the selected equipment result contains a device review, the report retains that review. Changed project entries require a new equipment check before they can be included.",
								"linker-tools",
							)}{" "}
							{__(
								"The report includes readable model, firmware and standard information from labelled fields on the first page, and flags references to unverified annexes. It does not confirm that the equipment or project meets the stated conditions.",
								"linker-tools",
							)}
						</small>
					</label>
				)}
				<label className="lp-field">
					<span>{__("Your logo on the PDF (optional)", "linker-tools")}</span>
					<input
						type="file"
						accept="image/png,image/jpeg"
						disabled={disabled}
						onChange={(event) => {
							reader.current?.abort();
							setLogo(null);
							setReading(false);
							setError(false);
							const file = event.currentTarget.files?.[0];
							if (!file) return;
							if (
								file.size > 500000 ||
								!["image/png", "image/jpeg"].includes(file.type)
							) {
								setError(true);
								return;
							}
							const next = new FileReader();
							reader.current = next;
							setReading(true);
							next.onload = () => {
								if (
									reader.current === next &&
									typeof next.result === "string"
								) {
									setLogo(next.result);
									setReading(false);
								}
							};
							next.onerror = () => {
								if (reader.current === next) {
									setError(true);
									setReading(false);
								}
							};
							next.readAsDataURL(file);
						}}
					/>
					<small>{__("PNG or JPG, up to 500 kB.", "linker-tools")}</small>
				</label>
			</div>
			{error && (
				<Notice error>
					{__(
						"The logo could not be used. Choose a PNG or JPG of up to 500 kB.",
						"linker-tools",
					)}
				</Notice>
			)}
			<button
				type="button"
				className="lp-button"
				disabled={
					disabled ||
					error ||
					reading ||
					(!hasCandidate &&
						!energy &&
						!pv &&
						!equipment &&
						!(installation && hasInstallation))
				}
				onClick={() => void generate(options)}
			>
				{__("Generate planning report", "linker-tools")}
			</button>
		</section>
	);
}
