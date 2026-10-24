import type { EnergyRun, RunState } from "../../data/energyProtocol.ts";
import { readObject } from "../../data/readProtocol.ts";
import { __, sprintf } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";
import { verificationLabel } from "./verificationLabel.ts";

export function runStateLabel(state: RunState): string {
	switch (state) {
		case "queued":
			return __("Queued", "linker-tools");
		case "running":
			return __("Calculating", "linker-tools");
		case "retry_wait":
			return __("Waiting to retry", "linker-tools");
		case "succeeded":
			return __("Calculation complete", "linker-tools");
		case "failed":
			return __("Calculation failed", "linker-tools");
		case "cancelled":
			return __("Calculation cancelled", "linker-tools");
	}
}
function failureText(run: EnergyRun): string {
	switch (run.error?.code) {
		case "version_unavailable":
			return __(
				"A model or source used by this calculation is unavailable. Its original inputs remain saved.",
				"linker-tools",
			);
		case "invalid_input":
			return __(
				"The saved scenario could not be calculated. Source coverage, operating periods or storage settings need attention.",
				"linker-tools",
			);
		case "resource_limit":
			return __(
				"The calculation exceeded the service's current processing limit. Its original inputs remain saved.",
				"linker-tools",
			);
		case "numerical_failure":
			return __(
				"The numerical checks could not establish a usable result. The saved inputs remain available.",
				"linker-tools",
			);
		default:
			return __(
				"The calculation stopped before a result was published. Its original inputs remain saved.",
				"linker-tools",
			);
	}
}

export function RunResult({
	run,
	locale,
	dirty,
	confirmedRevision,
}: {
	run: EnergyRun;
	locale: string;
	dirty: boolean;
	confirmedRevision: number;
}) {
	const format = (value: unknown, digits = 2) =>
		typeof value === "number"
			? new Intl.NumberFormat(locale, { maximumFractionDigits: digits }).format(
					value,
				)
			: "—";
	const result = run.result,
		metrics = result ? readObject(result.metrics) : null;
	const checks = result
		? (readObject(result.verification)
				.checks as readonly import("../../data/protocol.ts").JsonObject[])
		: [];
	// Scientific display preserves nonzero arithmetic tolerances below the
	// summary's decimal precision. No model tolerance is rounded or rewritten.
	const arithmetic = (value: unknown) =>
		typeof value === "number"
			? value === 0
				? "0"
				: new Intl.NumberFormat(locale, {
						notation: "scientific",
						maximumSignificantDigits: 6,
					}).format(value)
			: "—";
	const ratio = (name: string) => {
		if (!metrics) return "—";
		const row = readObject(metrics[name]);
		return typeof row.value === "number"
			? new Intl.NumberFormat(locale, {
					style: "percent",
					maximumFractionDigits: 1,
				}).format(row.value)
			: "—";
	};
	return (
		<div className="lp-run-result">
			<div
				className="lp-run-heading lp-focus-target"
				data-action-result-context=""
			>
				<div>
					<span className="lp-eyebrow">
						{__("Saved calculation", "linker-tools")}
					</span>
					<h3 className="lp-focus-target" tabIndex={-1}>
						{runStateLabel(run.state)}
					</h3>
				</div>
				<span className="lp-run-revision">
					{sprintf(__("Input revision %d", "linker-tools"), run.revision)}
				</span>
			</div>
			{(dirty || !run.is_current || run.revision !== confirmedRevision) && (
				<Notice>
					{__(
						"This calculation uses an earlier input snapshot. Open or newer project changes are excluded from its result.",
						"linker-tools",
					)}
				</Notice>
			)}
			{["queued", "running", "retry_wait"].includes(run.state) && (
				<p role="status">
					{__(
						"Leaving this workspace does not cancel the calculation. Its status is saved on the server.",
						"linker-tools",
					)}
				</p>
			)}
			{run.state === "failed" && <Notice error>{failureText(run)}</Notice>}
			{run.state === "cancelled" && (
				<p>
					{__(
						"The server has confirmed cancellation. Any earlier saved results remain available.",
						"linker-tools",
					)}
				</p>
			)}
			{result && metrics && (
				<>
					{result.scenario_constraint_status === "violated" && (
						<Notice error>
							{__(
								"The calculation checks need attention. The detailed checks identify unmet requirements or inconsistencies.",
								"linker-tools",
							)}
							<ul>
								{checks
									.filter(
										(check) =>
											!check.passed &&
											verificationLabel(String(check.code)) !== null,
									)
									.map((check) => (
										<li key={String(check.code)}>
											{verificationLabel(String(check.code))}
										</li>
									))}
							</ul>
						</Notice>
					)}
					<dl className="lp-energy-metrics">
						<div>
							<dt>{__("Solar supplied to load", "linker-tools")}</dt>
							<dd>
								{format(metrics.solar_load_kwh)} <small>kWh</small>
							</dd>
						</div>
						<div>
							<dt>{__("Grid import", "linker-tools")}</dt>
							<dd>
								{format(metrics.grid_import_kwh)} <small>kWh</small>
							</dd>
						</div>
						<div>
							<dt>{__("Solar share of gross demand", "linker-tools")}</dt>
							<dd>{ratio("solar_autarky")}</dd>
						</div>
						<div>
							<dt>{__("PV used or stored on site", "linker-tools")}</dt>
							<dd>{ratio("pv_input_self_use")}</dd>
						</div>
					</dl>
					<p className="lp-profile-help">
						{__(
							"Figures cover the simulated periods. Solar supply includes PV-origin battery energy; grid-origin and unknown-origin inventory remain separate.",
							"linker-tools",
						)}
					</p>
					{metrics.load_measurement_scope !== "gross_load" && (
						<p className="lp-profile-help">
							{__(
								"This calculation includes critical-load periods. A whole-site gross-demand percentage is therefore undefined.",
								"linker-tools",
							)}
						</p>
					)}
					{readObject(metrics.solar_autarky).undefined_reason ===
						"gross_load_is_zero" && (
						<p className="lp-profile-help">
							{__(
								"The solar share is undefined when gross demand is zero.",
								"linker-tools",
							)}
						</p>
					)}
					{readObject(metrics.pv_input_self_use).value === null && (
						<p className="lp-profile-help">
							{__(
								"The PV-use percentage is undefined when generated PV energy is zero.",
								"linker-tools",
							)}
						</p>
					)}
					<div className="lp-run-boundaries">
						<p>
							{__(
								"Equipment suitability: not assessed by this calculation.",
								"linker-tools",
							)}
						</p>
						<p>
							{__(
								"Country requirements: not assessed by this calculation.",
								"linker-tools",
							)}
						</p>
					</div>
					<details className="lp-comparison">
						<summary>
							{__("Energy totals and definitions", "linker-tools")}
						</summary>
						<dl className="lp-field-summary">
							<div>
								<dt>{__("Simulated load demand", "linker-tools")}</dt>
								<dd>{format(metrics.load_demand_kwh)} kWh</dd>
							</div>
							<div>
								<dt>{__("Generated AC PV energy", "linker-tools")}</dt>
								<dd>{format(metrics.pv_generated_ac_kwh)} kWh</dd>
							</div>
							<div>
								<dt>{__("Unserved simulated load", "linker-tools")}</dt>
								<dd>{format(metrics.unserved_load_kwh)} kWh</dd>
							</div>
							<div>
								<dt>{__("Calculated intervals", "linker-tools")}</dt>
								<dd>{format(result.interval_count, 0)}</dd>
							</div>
						</dl>
						<p>
							{__(
								"Solar share of gross demand divides PV energy delivered to gross site load by gross site demand. It is undefined for a mixed or critical-only load scope, or zero gross demand.",
								"linker-tools",
							)}
						</p>
						<p>
							{__(
								"This percentage divides PV supplied to load, AC auxiliary demand and battery charging by generated PV after curtailment. Battery charging is counted before conversion losses, including energy still stored at the end. Curtailed PV is excluded from the denominator.",
								"linker-tools",
							)}
						</p>
					</details>
					<details className="lp-comparison">
						<summary>
							{__("Numerical verification details", "linker-tools")}
						</summary>
						<p>
							{__(
								"These checks cover the declared energy model and scenario. Their numerical allowances address floating-point arithmetic; they are not installation safety margins.",
								"linker-tools",
							)}
						</p>
						<div className="lp-table-scroll" tabIndex={0}>
							<table>
								<caption>
									{__("Checks recorded with this result", "linker-tools")}
								</caption>
								<thead>
									<tr>
										<th>{__("Check reference", "linker-tools")}</th>
										<th>{__("Outcome", "linker-tools")}</th>
										<th>{__("Largest deviation", "linker-tools")}</th>
										<th>{__("Arithmetic tolerance", "linker-tools")}</th>
									</tr>
								</thead>
								<tbody>
									{checks.map((check, index) => {
										return (
											<tr key={String(check.code) + index}>
												<td>
													{verificationLabel(String(check.code)) && (
														<p>{verificationLabel(String(check.code))}</p>
													)}
													<code>{String(check.code)}</code>
												</td>
												<td>
													{check.passed === true
														? __("Met", "linker-tools")
														: __("Needs attention", "linker-tools")}
												</td>
												<td>
													{arithmetic(check.worst_violation)}{" "}
													{String(check.unit)}
												</td>
												<td>
													{arithmetic(check.allowance)} {String(check.unit)}
												</td>
											</tr>
										);
									})}
								</tbody>
							</table>
						</div>
					</details>
					<details className="lp-comparison">
						<summary>{__("Calculation records", "linker-tools")}</summary>
						<dl className="lp-run-records">
							<div>
								<dt>{__("Input SHA-256", "linker-tools")}</dt>
								<dd>
									<code>{String(run.manifest.input_sha256)}</code>
								</dd>
							</div>
							<div>
								<dt>{__("Manifest SHA-256", "linker-tools")}</dt>
								<dd>
									<code>{run.manifest_sha256}</code>
								</dd>
							</div>
							<div>
								<dt>{__("Result SHA-256", "linker-tools")}</dt>
								<dd>
									<code>{run.result_sha256}</code>
								</dd>
							</div>
							<div>
								<dt>{__("Runtime SHA-256", "linker-tools")}</dt>
								<dd>
									<code>{String(result.runtime_sha256)}</code>
								</dd>
							</div>
							<div>
								<dt>{__("Energy trace SHA-256", "linker-tools")}</dt>
								<dd>
									<code>{String(result.trace_sha256)}</code>
								</dd>
							</div>
						</dl>
					</details>
				</>
			)}
		</div>
	);
}
