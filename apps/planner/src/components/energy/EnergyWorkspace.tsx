import { useEffect, useMemo, useRef, useState } from "react";
import type { Draft } from "../../domain/draft.ts";
import { isDirty, sameJson } from "../../domain/draft.ts";
import {
	BATTERY_FIELDS,
	compileScenario,
	emptyScenario,
	readScenarioDraft,
	readBatteryParameters,
	readEnergyInputs,
	scenarioInputs,
	scenarioParts,
} from "../../domain/energyScenario.ts";
import type { ScenarioDraft } from "../../domain/energyScenario.ts";
import {
	readAsset,
	readPreview,
	readSelections,
} from "../../domain/profiles.ts";
import type { Measurement } from "../../domain/profiles.ts";
import { sharedProfileRange } from "../../domain/profileCoverage.ts";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import type { JsonObject, Session } from "../../data/protocol.ts";
import { ApiError } from "../../data/protocol.ts";
import { replacePlannerLocation } from "../../data/plannerLocation.ts";
import { useEnergyOperations } from "../../data/useEnergyOperations.ts";
import { useEnergyRuns } from "../../data/useEnergyRuns.ts";
import { readEnergyOperation, runPending } from "../../data/energyProtocol.ts";
import type { EnergyIntent } from "../../data/EnergyIntentStore.ts";
import { __, sprintf } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";
import { revealActionResult } from "../revealActionResult.ts";
import { measurementLabel } from "../ProfileLabels.ts";
import { ScenarioForm } from "./ScenarioForm.tsx";
import { EnergyError } from "./EnergyError.tsx";
import { RunResult, runStateLabel } from "./RunResult.tsx";
import { RunBasis } from "./RunBasis.tsx";

export function EnergyWorkspace({
	draft,
	edit,
	flush,
	session,
	client,
	recheck,
	locale,
	blocked,
	active,
	recoveryScopes,
	recoveryChecking = false,
	onValidity,
	openProfiles,
}: {
	draft: Draft;
	edit: (operation: (inputs: JsonObject) => JsonObject) => boolean;
	flush: () => Promise<boolean>;
	session: Session;
	client: PlannerClient;
	recheck: () => void;
	locale: string;
	blocked: boolean;
	active: boolean;
	recoveryScopes?: readonly string[] | undefined;
	recoveryChecking?: boolean;
	onValidity: (valid: boolean) => void;
	openProfiles: () => void;
}) {
	const parsed = useMemo(() => {
		try {
			return {
				value:
					draft.history.current.energy_scenario === undefined
						? emptyScenario()
						: readScenarioDraft(draft.history.current.energy_scenario),
				error: null,
			};
		} catch (error) {
			return { value: null, error };
		}
	}, [draft.history.current.energy_scenario]);
	const setupDocument = draft.history.current.energy_scenario;
	const setup = parsed.value,
		selections = readSelections(draft.history.current.profile_selections);
	const [view, setView] = useState<"scenario" | "runs">(() =>
			new URL(window.location.href).searchParams.has("run")
				? "runs"
				: "scenario",
		),
		[section, setSection] = useState<"storage" | "initial" | "operation">(
			"storage",
		),
		[syntaxValid, setSyntaxValid] = useState(true),
		[error, setError] = useState<unknown>(null),
		[rangeBusy, setRangeBusy] = useState(false);
	useEffect(() => {
		// Undo/redo and profile edits also change the effective scenario, without
		// passing through this form's onChange handler.
		setError(null);
	}, [setupDocument, draft.history.current.profile_selections]);
	const lifetime = useRef(0),
		rangeFlight = useRef<AbortController | null>(null);
	const projectId = draft.baseline.id,
		admitted = client.isCurrentScope(session.query_scope),
		dirty = isDirty(draft);
	useEffect(() => {
		lifetime.current++;
		return () => {
			lifetime.current++;
			rangeFlight.current?.abort();
		};
	}, [projectId, session.query_scope]);
	useEffect(() => {
		onValidity(syntaxValid);
		return () => onValidity(true);
	}, [syntaxValid, onValidity]);
	const confirmedBatteryId = useMemo(() => {
		try {
			return readEnergyInputs(draft.baseline.inputs.energy_replay)
				.battery_parameters_asset_id;
		} catch {
			return null;
		}
	}, [draft.baseline.inputs.energy_replay]);
	const operations = useEnergyOperations({
		projectId,
		session,
		client,
		recheck,
		recoveryScopes,
		recoveryChecking,
		confirmedBatteryId,
	});
	const actionError = error ?? operations.error,
		errorTarget = useRef<HTMLDivElement>(null);
	useEffect(() => {
		if (actionError && active)
			revealActionResult(errorTarget.current, () =>
				client.isCurrentScope(session.query_scope),
			);
	}, [actionError, active, client, session.query_scope]);
	const runs = useEnergyRuns({
		projectId,
		session,
		client,
		recheck,
		active: active && view === "runs",
	});
	const runTarget = useRef<HTMLDivElement>(null),
		visibleRunId = runs.run.data?.id;
	useEffect(() => {
		if (
			!active ||
			view !== "runs" ||
			!visibleRunId ||
			visibleRunId !== runs.runId
		)
			return;
		// Let the parent/native bar layout commit before restoring a result route.
		const frame = window.requestAnimationFrame(() =>
			revealActionResult(
				runTarget.current?.querySelector<HTMLElement>(".lp-run-result h3") ??
					null,
				() => client.isCurrentScope(session.query_scope),
			),
		);
		return () => window.cancelAnimationFrame(frame);
		// Changing a selected calculation reveals its heading. Polling the same
		// calculation never takes focus back from the reader's current control.
	}, [view, visibleRunId, runs.runId, active, client, session.query_scope]);
	let prepared = false;
	try {
		prepared =
			setup !== null &&
			sameJson(
				compileScenario(setup, selections),
				draft.history.current.energy_replay,
			);
	} catch {
		/* Incomplete settings stay editable. */
	}
	const unconfirmed = operations.records.filter(
		(record) => record.resultId === null,
	);
	const canCalculate =
		prepared &&
		!dirty &&
		!draft.pending &&
		!draft.conflict &&
		!blocked &&
		syntaxValid &&
		admitted &&
		!operations.busy &&
		!operations.checking &&
		!operations.storageFailed &&
		!unconfirmed.length;
	function change(next: ScenarioDraft) {
		if (blocked || !client.isCurrentScope(session.query_scope)) return;
		edit((inputs) => scenarioInputs(inputs, next));
		setError(null);
	}
	async function prepare() {
		if (
			!setup ||
			blocked ||
			!syntaxValid ||
			operations.busy ||
			operations.checking ||
			operations.storageFailed ||
			unconfirmed.length ||
			!admitted
		)
			return;
		setError(null);
		try {
			const parts = scenarioParts(setup, selections),
				instance = lifetime.current;
			let bound = setup;
			try {
				compileScenario(setup, selections);
			} catch (cause) {
				if (
					!(cause instanceof ApiError) ||
					cause.code !== "battery_not_prepared"
				)
					throw cause;
				const reply = await operations.start("battery/scenario", {
					source_note: setup.source_note,
					parameters: parts.parameters,
				});
				if (
					!reply ||
					reply.path !== "battery/scenario" ||
					instance !== lifetime.current ||
					!client.isCurrentScope(session.query_scope)
				)
					return;
				bound = {
					...setup,
					battery_binding: {
						asset_id: reply.asset.id,
						parameters: parts.parameters,
						source_note: setup.source_note,
					},
				};
			}
			const replay = compileScenario(bound, selections);
			const applied = edit((inputs) => {
				if (
					!sameJson(inputs.energy_scenario, setupDocument) ||
					!sameJson(readSelections(inputs.profile_selections), selections)
				)
					throw new Error("scenario_changed");
				return { ...scenarioInputs(inputs, bound), energy_replay: replay };
			});
			if (!applied) throw new ApiError(409, "scenario_changed");
			await flush();
		} catch (cause) {
			if (client.isCurrentScope(session.query_scope)) setError(cause);
		}
	}
	async function recover(record: EnergyIntent) {
		if (
			blocked ||
			!syntaxValid ||
			operations.busy ||
			!client.isCurrentScope(session.query_scope)
		)
			return;
		setError(null);
		try {
			if (record.path === "runs/energy") {
				const reply = await operations.retry(record);
				if (reply?.path === "runs/energy") {
					runs.accepted(reply.run);
					setView("runs");
				}
				return;
			}
			if (!setup) return;
			const command = readEnergyOperation(record.path, record.body),
				parameters = readBatteryParameters(command.parameters);
			const restored = readScenarioDraft({
				...setup,
				battery: Object.fromEntries(
					BATTERY_FIELDS.map((key) => [key, parameters[key]]),
				),
				source_note: command.source_note,
				battery_binding: null,
			});
			if (!edit((inputs) => scenarioInputs(inputs, restored))) return;
			const instance = lifetime.current,
				reply = await operations.retry(record);
			if (
				!reply ||
				reply.path !== "battery/scenario" ||
				instance !== lifetime.current ||
				!client.isCurrentScope(session.query_scope)
			)
				return;
			const applied = edit((inputs) => {
				const current = readScenarioDraft(inputs.energy_scenario);
				if (
					!sameJson(current.battery, restored.battery) ||
					current.source_note !== restored.source_note
				)
					throw new Error("scenario_changed");
				return scenarioInputs(inputs, {
					...current,
					battery_binding: {
						asset_id: reply.asset.id,
						parameters,
						source_note: restored.source_note,
					},
				});
			});
			if (!applied) throw new ApiError(409, "scenario_changed");
			await flush();
		} catch (cause) {
			if (client.isCurrentScope(session.query_scope)) setError(cause);
		}
	}
	async function calculate() {
		if (!canCalculate) return;
		const reply = await operations.start("runs/energy", {
			expected_revision: draft.baseline.revision,
		});
		if (reply?.path === "runs/energy") {
			runs.accepted(reply.run);
			setView("runs");
		}
	}
	function chooseView(next: "scenario" | "runs") {
		setView(next);
		if (next === "runs") {
			if (runs.runId) runs.select(runs.runId);
		} else {
			const url = new URL(window.location.href);
			url.searchParams.delete("run");
			replacePlannerLocation(url);
		}
	}
	async function useRange() {
		if (!setup || rangeFlight.current || !admitted) return;
		const controller = new AbortController(),
			instance = lifetime.current;
		rangeFlight.current = controller;
		setRangeBusy(true);
		setError(null);
		try {
			const roles: Measurement[] = [
				"gross_load",
				"pv_available_ac",
				"aux_ac",
				...(setup.schedule.some((period) => period.mode === "outage")
					? ["critical_load" as const]
					: []),
			];
			const ranges = await Promise.all(
				roles.map(async (role) => {
					const id = selections.selected[role];
					if (!id) throw new ApiError(422, "scenario_profiles_required");
					const asset = readAsset(
						await client.query(
							"assets/read",
							{ schema_version: 1, project_id: projectId, asset_id: id },
							session.query_scope,
							controller.signal,
						),
						projectId,
					);
					const preview = readPreview(
						await client.query(
							"profiles/preview",
							{
								schema_version: 1,
								project_id: projectId,
								asset_id: id,
								offset: 0,
								page_size: 1,
							},
							session.query_scope,
							controller.signal,
						),
						asset,
					);
					if (asset.id !== id || preview.measurement !== role)
						throw new ApiError(502, "profile_role_mismatch");
					return preview.summary;
				}),
			);
			if (
				instance !== lifetime.current ||
				!client.isCurrentScope(session.query_scope)
			)
				return;
			const range = sharedProfileRange(ranges),
				last = setup.schedule.length - 1;
			const applied = edit((inputs) => {
				if (
					!sameJson(inputs.energy_scenario, setupDocument) ||
					!sameJson(readSelections(inputs.profile_selections), selections)
				)
					throw new Error("scenario_changed");
				return scenarioInputs(inputs, {
					...setup,
					schedule: setup.schedule.map((period, index) => ({
						...period,
						...(index === 0 ? { start_utc: range.start_utc } : {}),
						...(index === last ? { end_utc: range.end_utc } : {}),
					})),
				});
			});
			if (!applied) throw new ApiError(409, "scenario_changed");
		} catch (cause) {
			if (
				cause instanceof ApiError &&
				([401, 403].includes(cause.status) || cause.code === "session_changed")
			)
				recheck();
			if (
				instance === lifetime.current &&
				client.isCurrentScope(session.query_scope)
			)
				setError(cause);
		} finally {
			if (rangeFlight.current === controller) {
				rangeFlight.current = null;
				if (instance === lifetime.current) setRangeBusy(false);
			}
		}
	}
	return (
		<section
			className="lp-section lp-energy-workspace"
			id="lp-calculations"
			tabIndex={-1}
			aria-labelledby="lp-calculations-heading"
		>
			<div className="lp-section-heading">
				<span className="lp-index">07</span>
				<div>
					<h2 id="lp-calculations-heading">
						{__("Energy calculation", "linker-tools")}
					</h2>
					<p>
						{__(
							"Calculate this project's energy flows over the selected periods. Each saved result keeps the inputs, sources and model used.",
							"linker-tools",
						)}
					</p>
				</div>
			</div>
			<div
				className="lp-energy-switch"
				role="group"
				aria-label={__("Calculation workspace view", "linker-tools")}
			>
				<button
					type="button"
					aria-pressed={view === "scenario"}
					onClick={() => chooseView("scenario")}
				>
					{__("Scenario settings", "linker-tools")}
				</button>
				<button
					type="button"
					aria-pressed={view === "runs"}
					onClick={() => chooseView("runs")}
				>
					{__("Saved calculations", "linker-tools")}
				</button>
			</div>
			{Boolean(actionError) && (
				<div ref={errorTarget} className="lp-focus-target" tabIndex={-1}>
					<EnergyError error={actionError} />
				</div>
			)}
			{operations.storageFailed && (
				<Notice error>
					<p>
						{__(
							"This browser could not save or read the information needed to recover calculation requests. New requests are paused until this is available.",
							"linker-tools",
						)}
					</p>
					<button
						type="button"
						className="lp-text-button"
						onClick={operations.refresh}
					>
						{__("Check browser storage", "linker-tools")}
					</button>
				</Notice>
			)}
			{operations.records.length > 0 && (
				<details
					className="lp-comparison lp-energy-recovery"
					open={unconfirmed.length > 0}
				>
					<summary>{__("Stored requests", "linker-tools")}</summary>
					<p>
						{__(
							"Retrying a calculation uses its original request and saved input revision. Restoring storage settings replaces those settings in your open draft.",
							"linker-tools",
						)}
					</p>
					{operations.records.map((record) => (
						<div
							key={record.scope + record.path + record.key}
							className="lp-energy-recovery-row"
						>
							<span>
								{record.path === "battery/scenario"
									? __("Saved storage settings", "linker-tools")
									: sprintf(
											__("Calculation request · revision %d", "linker-tools"),
											Number(
												readEnergyOperation(record.path, record.body)
													.expected_revision,
											),
										)}
							</span>
							<button
								type="button"
								className="lp-button lp-button-secondary"
								disabled={operations.busy || blocked || !syntaxValid}
								onClick={() => void recover(record)}
							>
								{record.path === "battery/scenario"
									? __("Restore and retry storage settings", "linker-tools")
									: __("Retry original calculation request", "linker-tools")}
							</button>
							{record.resultId !== null && (
								<button
									type="button"
									className="lp-text-button"
									disabled={operations.busy || operations.checking}
									onClick={() => void operations.dismissAcknowledged(record)}
								>
									{__("Dismiss confirmed request", "linker-tools")}
								</button>
							)}
						</div>
					))}
				</details>
			)}
			<div hidden={view !== "scenario"}>
				{Boolean(parsed.error) && (
					<Notice error>
						{__(
							"This scenario-settings format cannot be edited here. Its saved input and calculation history remain available.",
							"linker-tools",
						)}
					</Notice>
				)}
				{setup && (
					<>
						<div className="lp-scenario-sources">
							<h3>{__("Interval sources", "linker-tools")}</h3>
							<ul>
								{(["gross_load", "pv_available_ac", "aux_ac"] as const).map(
									(role) => (
										<li key={role}>
											<span>{measurementLabel(role)}</span>
											<strong>
												{selections.selected[role]
													? __("Selected in this draft", "linker-tools")
													: __("Required", "linker-tools")}
											</strong>
										</li>
									),
								)}
							</ul>
							<button
								type="button"
								className="lp-text-button"
								onClick={openProfiles}
								disabled={!syntaxValid}
							>
								{__("Review energy inputs", "linker-tools")}
							</button>
						</div>
						<ol className="lp-scenario-steps">
							{(["storage", "initial", "operation"] as const).map(
								(step, index) => (
									<li
										key={step}
										aria-current={section === step ? "step" : undefined}
									>
										<button
											type="button"
											disabled={!syntaxValid}
											onClick={() => setSection(step)}
										>
											<span>{String(index + 1).padStart(2, "0")}</span>
											{step === "storage"
												? __("Storage", "linker-tools")
												: step === "initial"
													? __("Starting state", "linker-tools")
													: __("Operation", "linker-tools")}
										</button>
									</li>
								),
							)}
						</ol>
						<ScenarioForm
							value={setup}
							section={section}
							locale={locale}
							disabled={blocked || operations.busy || !admitted}
							onChange={change}
							onValidity={setSyntaxValid}
							useProfileRange={() => void useRange()}
							rangeBusy={rangeBusy}
						/>
						<div className="lp-energy-submit">
							<div>
								<strong>
									{prepared
										? __("Scenario prepared in this draft", "linker-tools")
										: __("Scenario settings need preparation", "linker-tools")}
								</strong>
								<p>
									{dirty || draft.pending
										? __(
												"Save project records these inputs before a new calculation can start.",
												"linker-tools",
											)
										: sprintf(
												__(
													"A new calculation uses saved input revision %d.",
													"linker-tools",
												),
												draft.baseline.revision,
											)}
								</p>
							</div>
							<button
								type="button"
								className="lp-button lp-button-secondary"
								disabled={
									blocked ||
									!syntaxValid ||
									operations.busy ||
									operations.checking ||
									operations.storageFailed ||
									unconfirmed.length > 0
								}
								onClick={() => void prepare()}
							>
								{operations.busy
									? __("Confirming request…", "linker-tools")
									: __("Prepare scenario settings", "linker-tools")}
							</button>
							<button
								type="button"
								className="lp-button"
								disabled={!canCalculate}
								onClick={() => void calculate()}
							>
								{__("Calculate saved scenario", "linker-tools")}
							</button>
						</div>
					</>
				)}
			</div>
			<div className="lp-energy-runs" hidden={view !== "runs"}>
				{runs.page.error && (
					<Notice error>
						<p>
							{__(
								"Saved calculation history could not be refreshed.",
								"linker-tools",
							)}
						</p>
						<button
							type="button"
							className="lp-text-button"
							onClick={() => void runs.page.refetch()}
						>
							{__("Refresh calculation history", "linker-tools")}
						</button>
					</Notice>
				)}
				{!runs.page.data && !runs.page.error && (
					<p role="status">
						{__("Reading saved calculations…", "linker-tools")}
					</p>
				)}
				{runs.page.data && (
					<aside className="lp-run-history">
						<h3>{__("Calculation history", "linker-tools")}</h3>
						{!runs.page.data.items.length && (
							<p>
								{__(
									"No saved calculation is available on this page.",
									"linker-tools",
								)}
							</p>
						)}
						{runs.page.data.items.map((run) => (
							<button
								type="button"
								key={run.id}
								aria-pressed={runs.runId === run.id}
								onClick={() => runs.select(run.id)}
							>
								<strong>
									{sprintf(__("Revision %d", "linker-tools"), run.revision)}
								</strong>
								<span>{runStateLabel(run.state)}</span>
								<small>
									{new Intl.DateTimeFormat(locale, {
										dateStyle: "short",
										timeStyle: "short",
									}).format(run.created_at * 1000)}
								</small>
							</button>
						))}
						<div className="lp-inline-actions">
							{runs.hasPrevious && (
								<button
									type="button"
									className="lp-text-button"
									onClick={runs.first}
								>
									{__("Latest calculations", "linker-tools")}
								</button>
							)}
							{runs.page.data.next && (
								<button
									type="button"
									className="lp-text-button"
									onClick={runs.next}
								>
									{__("Earlier calculations", "linker-tools")}
								</button>
							)}
						</div>
					</aside>
				)}
				<div ref={runTarget} className="lp-run-content">
					{runs.run.error && (
						<Notice error>
							<p>
								{__(
									"The selected calculation could not be refreshed. Any visible state is the last confirmed response.",
									"linker-tools",
								)}
							</p>
							<button
								type="button"
								className="lp-text-button"
								onClick={() => void runs.run.refetch()}
							>
								{__("Refresh calculation status", "linker-tools")}
							</button>
						</Notice>
					)}
					{runs.runId && !runs.run.data && !runs.run.error && (
						<p role="status">
							{__("Reading the saved calculation…", "linker-tools")}
						</p>
					)}
					{runs.run.data && (
						<>
							<RunResult
								run={runs.run.data}
								locale={locale}
								dirty={dirty || Boolean(draft.pending)}
								confirmedRevision={draft.baseline.revision}
							/>
							<RunBasis
								key={runs.run.data.id}
								run={runs.run.data}
								session={session}
								client={client}
								recheck={recheck}
								locale={locale}
							/>
							{runPending(runs.run.data.state) && (
								<button
									type="button"
									className="lp-button lp-button-secondary"
									disabled={runs.cancelPending}
									onClick={() => void runs.cancel()}
								>
									{runs.cancelBusy
										? __("Confirming cancellation…", "linker-tools")
										: __("Cancel calculation", "linker-tools")}
								</button>
							)}
							{runs.cancelError && (
								<Notice error>
									{__(
										"Cancellation could not be confirmed. The calculation may still be running; its server status can be refreshed.",
										"linker-tools",
									)}
								</Notice>
							)}
						</>
					)}
				</div>
			</div>
		</section>
	);
}
