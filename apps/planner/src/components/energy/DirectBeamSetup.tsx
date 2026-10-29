import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { Draft } from "../../domain/draft.ts";
import { isDirty } from "../../domain/draft.ts";
import { sameJson } from "../../domain/draft.ts";
import type { JsonObject, Session } from "../../data/protocol.ts";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import { readObject } from "../../data/readProtocol.ts";
import {
	directBeamDraft,
	readDirectBeam,
	compileDirectBeam,
	DIRECT_BEAM_TASK,
} from "../../domain/directBeam.ts";
import type { DirectBeamDraft } from "../../domain/directBeam.ts";
import { readDirectBeamLimits } from "../../data/directBeamResult.ts";
import { readBeamWeatherPreview } from "../../data/directBeamWeather.ts";
import { useRetainedWeather } from "../../data/useRetainedWeather.ts";
import { referenceRoof } from "../../domain/pvgisReference.ts";
import { useModuleTemplates } from "../../data/useModuleTemplates.ts";
import { matchesModule } from "../../domain/productModules.ts";
import { panelPoses } from "../../domain/panelPoses.ts";
import { __, sprintf } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";

export function DirectBeamSetup({
	draft,
	edit,
	session,
	client,
	active,
	disabled,
	actionsDisabled,
	onValidity,
	start,
	openWeather,
	openDesign,
	locale,
}: {
	draft: Draft;
	edit: (operation: (inputs: JsonObject) => JsonObject) => boolean;
	session: Session;
	client: PlannerClient;
	active: boolean;
	disabled: boolean;
	actionsDisabled: boolean;
	onValidity: (valid: boolean) => void;
	start: () => void;
	openWeather: () => void;
	openDesign: (() => void) | undefined;
	locale: string;
}) {
	const inputs = draft.history.current,
		projectId = draft.baseline.id,
		scope = session.query_scope;
	const [offset, setOffset] = useState(0);
	const [jump, setJump] = useState(""),
		[requestedUtc, setRequestedUtc] = useState<string | null>(null),
		[jumpInvalid, setJumpInvalid] = useState(false);
	const parsed = useMemo(() => {
		try {
			return directBeamDraft(inputs);
		} catch {
			return null;
		}
	}, [inputs.direct_beam_visibility]);
	const limits = useMemo(() => {
		try {
			return readDirectBeamLimits(
				session.runtime.limits.direct_beam_visibility,
			);
		} catch {
			return null;
		}
	}, [session.runtime]);
	const supported =
		session.runtime.models.direct_beam_visibility === DIRECT_BEAM_TASK &&
		limits !== null;
	const pageSize = Math.min(24, session.runtime.limits.max_page_size); // Visible source-page policy, never a calculation time step.
	const owned = client.isCurrentScope(scope);
	const weather = useRetainedWeather(
		client,
		session,
		projectId,
		parsed?.weather_asset_id ?? null,
		active && supported,
		{ pageSize },
	);
	const { sources, assets, selected, binding } = weather;
	const bindingMetadata = binding.data?.metadata;
	const compatibleRequest =
		inputs.weather_acquisition === undefined ||
		(!!bindingMetadata &&
			sameJson(
				readObject(inputs.weather_acquisition).request,
				bindingMetadata.weather_request,
			) &&
			sameJson(
				readObject(inputs.weather_acquisition).interpretation,
				bindingMetadata.weather_interpretation,
			));
	const preview = useQuery({
		queryKey: [
			scope,
			"beam-weather-preview",
			projectId,
			selected?.asset_id,
			selected?.metadata_sha256,
			offset,
		],
		enabled: active && owned && selected !== undefined,
		retry: false,
		queryFn: async ({ signal }) => {
			if (!selected) throw new Error("weather_selection_required");
			return readBeamWeatherPreview(
				await client.query(
					"weather/preview",
					{
						schema_version: 1,
						project_id: projectId,
						asset_id: selected.asset_id,
						offset,
						page_size: pageSize,
					},
					scope,
					signal,
				),
				projectId,
				selected,
				offset,
				pageSize,
			);
		},
	});
	const catalog = useModuleTemplates(client, scope, active);
	const roof = useMemo(() => {
		try {
			return referenceRoof(inputs);
		} catch {
			return null;
		}
	}, [inputs.geometry]);
	const currentModules =
		roof &&
		catalog.data &&
		!catalog.error &&
		!catalog.isFetching &&
		roof.arrays.every((a) => {
			const spec = roof.geometry.module_specs.find(
				(s) => s.id === a.module_spec_id,
			);
			return (
				spec && catalog.data.some((template) => matchesModule(spec, template))
			);
		});
	const sourceMatchesRoof =
		!!roof &&
		!!binding.data &&
		readObject(binding.data.weather).latitude_deg ===
			roof.geometry.coordinate_system.anchor?.latitude_deg &&
		readObject(binding.data.weather).longitude_deg ===
			roof.geometry.coordinate_system.anchor?.longitude_deg;
	let valid = inputs.direct_beam_visibility === undefined,
		complete = false,
		samples: number | null = null;
	if (parsed) {
		try {
			// Saved syntax is independent of this service's optional method availability.
			readDirectBeam(parsed);
			valid = true;
			if (limits) {
				compileDirectBeam(parsed, limits);
				complete = true;
			}
		} catch {
			/* Incomplete local values stay in the native draft. */
		}
		if (complete && roof)
			samples =
				(Number(parsed.sampling.coarse_cells_per_edge) ** 2 +
					Number(parsed.sampling.fine_cells_per_edge) ** 2) *
				panelPoses(roof.geometry).filter((p) => p.included).length *
				parsed.row_indices.length;
	}
	useEffect(() => {
		onValidity(valid);
		return () => onValidity(true);
	}, [valid, onValidity]);
	const change = (next: DirectBeamDraft) => {
		if (!disabled && owned)
			edit((current) => ({
				...current,
				direct_beam_visibility: readObject(next),
			}));
	};
	const remove = () =>
		edit((current) => {
			const next = { ...current };
			delete next.direct_beam_visibility;
			return next;
		});
	const rows = parsed?.row_indices ?? [];
	const pageSelection = [
		...new Set([
			...rows,
			...(preview.data?.rows.map((r) => r.source_row_index) ?? []),
		]),
	].sort((a, b) => a - b);
	const allowedSamples =
		limits &&
		samples !== null &&
		Number.isSafeInteger(samples) &&
		samples <= limits.max_samples;
	const jumpMismatch =
		jumpInvalid ||
		(!!requestedUtc &&
			!!preview.data &&
			Date.parse(preview.data.rows[0]?.interval_start_utc ?? "") !==
				Date.parse(requestedUtc));
	function jumpToDate() {
		const first = preview.data?.rows[0];
		if (!first || !selected || !jump) return;
		// Navigation uses the verified interval width; the returned source page
		// must confirm the exact UTC start before any new row can be selected.
		const instant = Date.parse(jump + "Z"),
			width =
				Date.parse(first.interval_end_utc) -
				Date.parse(first.interval_start_utc);
		const index =
			offset + (instant - Date.parse(first.interval_start_utc)) / width;
		if (
			!Number.isSafeInteger(index) ||
			index < 0 ||
			index >= selected.interval_count
		) {
			setJumpInvalid(true);
			return;
		}
		setJumpInvalid(false);
		setRequestedUtc(new Date(instant).toISOString());
		setOffset(index);
	}
	if (!owned)
		return (
			<Notice>
				{__(
					"The saved result is hidden until this session is verified.",
					"linker-tools",
				)}
			</Notice>
		);
	return (
		<section className="lp-scenario-block">
			<h3>{__("Geometric direct-beam visibility", "linker-tools")}</h3>
			<p>
				{__(
					"Sample the direct path from each included module to the sun at selected weather timestamps. Declared roofs, obstacle volumes and other modules are treated as opaque. Diffuse light, electrical losses and annual generation are not calculated by this method.",
					"linker-tools",
				)}
			</p>
			{!supported && (
				<Notice>
					{__(
						"This geometric method is unavailable in the current service version. Saved selections and earlier results remain available.",
						"linker-tools",
					)}
				</Notice>
			)}
			{!roof || !currentModules ? (
				<Notice>
					<p>
						{__(
							"A georeferenced roof with a defined north direction and current module data is required. Review the roof design and its module selection.",
							"linker-tools",
						)}
					</p>
					<button type="button" className="lp-text-button" onClick={openDesign}>
						{__("Open roof design", "linker-tools")}
					</button>
				</Notice>
			) : null}
			{sources.error && (
				<Notice error>
					<p>
						{__(
							"Weather sources for this project could not be loaded. Your saved selection has been retained.",
							"linker-tools",
						)}
					</p>
					<button
						type="button"
						className="lp-text-button"
						onClick={() => void sources.refetch()}
					>
						{__("Try again", "linker-tools")}
					</button>
				</Notice>
			)}
			{sources.isPending && supported && active && (
				<p role="status">
					{__("Loading project weather sources…", "linker-tools")}
				</p>
			)}
			{sources.isSuccess && !assets.length && (
				<Notice>
					<p>
						{__(
							"This project has no retained weather source for this method. Prepare weather data first.",
							"linker-tools",
						)}
					</p>
					<button
						type="button"
						className="lp-text-button"
						onClick={openWeather}
					>
						{__("Open weather preparation", "linker-tools")}
					</button>
				</Notice>
			)}
			{selected &&
				inputs.weather_acquisition !== undefined &&
				!compatibleRequest && (
					<Notice>
						<p>
							{__(
								"The retained weather source must match the project's saved weather request and interpretation. Review the weather settings or choose the matching retained source; historical data is not replaced automatically.",
								"linker-tools",
							)}
						</p>
						<button
							type="button"
							className="lp-text-button"
							onClick={openWeather}
						>
							{__("Open weather preparation", "linker-tools")}
						</button>
					</Notice>
				)}
			{selected && roof && binding.isSuccess && !sourceMatchesRoof && (
				<Notice error>
					<p>
						{__(
							"The retained weather coordinates do not match the saved roof location. Review the weather settings or the roof location before calculating.",
							"linker-tools",
						)}
					</p>
					<button
						type="button"
						className="lp-text-button"
						onClick={openWeather}
					>
						{__("Open weather preparation", "linker-tools")}
					</button>
					<button type="button" className="lp-text-button" onClick={openDesign}>
						{__("Open roof design", "linker-tools")}
					</button>
				</Notice>
			)}
			{binding.error && selected && (
				<Notice error>
					{__(
						"The selected weather source could not be verified. Review the source selection before calculating.",
						"linker-tools",
					)}
				</Notice>
			)}
			{!parsed ? (
				<Notice error>
					{__(
						"The saved geometric selection could not be read. It can be removed from the draft and entered again.",
						"linker-tools",
					)}
				</Notice>
			) : (
				<fieldset disabled={disabled || !owned}>
					<label className="lp-field">
						<span>{__("Project weather source", "linker-tools")}</span>
						<select
							value={parsed.weather_asset_id ?? ""}
							onChange={(e) => {
								setOffset(0);
								setRequestedUtc(null);
								setJumpInvalid(false);
								setJump("");
								change({
									...parsed,
									weather_asset_id: e.currentTarget.value || null,
									row_indices: [],
								});
							}}
						>
							<option value="">
								{__("Choose a weather source", "linker-tools")}
							</option>
							{parsed.weather_asset_id && !selected && (
								<option value={parsed.weather_asset_id}>
									{__(
										"Saved source — load further sources to inspect it",
										"linker-tools",
									)}
								</option>
							)}
							{assets.map((a) => (
								<option key={a.asset_id} value={a.asset_id}>
									{a.label} · {a.synthetic_year}
								</option>
							))}
						</select>
					</label>
					{sources.hasNextPage && (
						<button
							type="button"
							className="lp-text-button"
							disabled={sources.isFetchingNextPage}
							onClick={() => void sources.fetchNextPage()}
						>
							{__("More weather sources", "linker-tools")}
						</button>
					)}
					<div className="lp-geometry-fields">
						{(["coarse_cells_per_edge", "fine_cells_per_edge"] as const).map(
							(key) => (
								<label className="lp-field" key={key}>
									<span>
										{key === "coarse_cells_per_edge"
											? __("Coarse grid cells per module edge", "linker-tools")
											: __("Fine grid cells per module edge", "linker-tools")}
									</span>
									<input
										type="number"
										inputMode="numeric"
										min="1"
										step="1"
										value={parsed.sampling[key] ?? ""}
										onChange={(e) =>
											change({
												...parsed,
												sampling: {
													...parsed.sampling,
													[key]:
														e.currentTarget.value === ""
															? null
															: Number(e.currentTarget.value),
												},
											})
										}
									/>
								</label>
							),
						)}
					</div>
					<p>
						{__(
							"Both equal-area midpoint grids must be specified. The fine grid must have more cells per edge. Their observed difference is not an error bound.",
							"linker-tools",
						)}
					</p>
					{selected && preview.data && (
						<div className="lp-geometry-fields">
							<label className="lp-field">
								<span>
									{__("Go to synthetic interval (UTC)", "linker-tools")}
								</span>
								<input
									type="datetime-local"
									value={jump}
									onChange={(e) => setJump(e.currentTarget.value)}
								/>
							</label>
							<button
								type="button"
								className="lp-button lp-button-secondary"
								disabled={!jump || preview.isFetching}
								onClick={jumpToDate}
							>
								{__("Show interval page", "linker-tools")}
							</button>
						</div>
					)}
					{jumpMismatch && (
						<Notice error>
							{__(
								"The requested date could not be located exactly in this source. Check the displayed UTC intervals before selecting rows.",
								"linker-tools",
							)}
						</Notice>
					)}
					{selected && (
						<label className="lp-field">
							<span>
								{__("First source interval on this page", "linker-tools")}
							</span>
							<input
								type="number"
								min="1"
								max={selected.interval_count}
								step="1"
								value={offset + 1}
								onChange={(e) => {
									const n = Number(e.currentTarget.value);
									if (
										Number.isSafeInteger(n) &&
										n > 0 &&
										n <= selected.interval_count
									) {
										setRequestedUtc(null);
										setJumpInvalid(false);
										setOffset(n - 1);
									}
								}}
							/>
						</label>
					)}
					{preview.error && (
						<Notice error>
							<p>
								{__(
									"The weather interval page could not be verified. No rows have been replaced or selected automatically.",
									"linker-tools",
								)}
							</p>
							<button
								type="button"
								className="lp-text-button"
								onClick={() => void preview.refetch()}
							>
								{__("Try again", "linker-tools")}
							</button>
						</Notice>
					)}
					{preview.data && (
						<>
							<button
								type="button"
								className="lp-text-button"
								disabled={
									jumpMismatch ||
									!limits ||
									pageSelection.length > limits.max_selected_rows
								}
								onClick={() =>
									change({ ...parsed, row_indices: pageSelection })
								}
							>
								{__("Select this page", "linker-tools")}
							</button>
							<p>
								{preview.data.source.radiation_database} ·{" "}
								{preview.data.source.meteo_database} ·{" "}
								{preview.data.source.start_year}–{preview.data.source.end_year}
							</p>
							<p>
								{__(
									"The source combines selected typical months. The synthetic interval calendar and the source irradiance timestamp have different meanings; both are shown in UTC.",
									"linker-tools",
								)}
							</p>
							<div className="lp-table-scroll">
								<table className="lp-data-table">
									<thead>
										<tr>
											<th>{__("Select", "linker-tools")}</th>
											<th>{__("Synthetic interval (UTC)", "linker-tools")}</th>
											<th>
												{__(
													"Source irradiance timestamp (UTC)",
													"linker-tools",
												)}
											</th>
										</tr>
									</thead>
									<tbody>
										{preview.data.rows.map((row) => (
											<tr key={row.source_row_index}>
												<td>
													<input
														type="checkbox"
														aria-label={sprintf(
															__(
																"Select interval beginning %s",
																"linker-tools",
															),
															row.interval_start_utc,
														)}
														checked={rows.includes(row.source_row_index)}
														disabled={
															jumpMismatch ||
															(!rows.includes(row.source_row_index) &&
																rows.length >=
																	Number(limits?.max_selected_rows))
														}
														onChange={(e) =>
															change({
																...parsed,
																row_indices: (e.currentTarget.checked
																	? [...rows, row.source_row_index]
																	: rows.filter(
																			(n) => n !== row.source_row_index,
																		)
																).sort((a, b) => a - b),
															})
														}
													/>
												</td>
												<td>
													<time>{row.interval_start_utc}</time>
													<br />
													<time>{row.interval_end_utc}</time>
												</td>
												<td>
													<time>{row.irradiance_at_utc}</time>
												</td>
											</tr>
										))}
									</tbody>
								</table>
							</div>
							<div className="lp-actions">
								<button
									type="button"
									className="lp-text-button"
									disabled={offset === 0}
									onClick={() => {
										setRequestedUtc(null);
										setJumpInvalid(false);
										setOffset(Math.max(0, offset - pageSize));
									}}
								>
									{__("Previous intervals", "linker-tools")}
								</button>
								<button
									type="button"
									className="lp-text-button"
									disabled={preview.data.next === null}
									onClick={() => {
										setRequestedUtc(null);
										setJumpInvalid(false);
										setOffset(preview.data!.next!);
									}}
								>
									{__("Next intervals", "linker-tools")}
								</button>
							</div>
						</>
					)}
					<p>
						{sprintf(
							__("Selected source intervals: %d", "linker-tools"),
							rows.length,
						)}
						{limits ? ` / ${limits.max_selected_rows}` : ""}
					</p>
					{rows.length > 0 && (
						<button
							type="button"
							className="lp-text-button"
							onClick={() => change({ ...parsed, row_indices: [] })}
						>
							{__("Clear selected intervals", "linker-tools")}
						</button>
					)}
				</fieldset>
			)}
			{inputs.direct_beam_visibility !== undefined && (
				<button
					type="button"
					className="lp-text-button"
					disabled={disabled || !owned}
					onClick={remove}
				>
					{__("Remove direct-beam settings from draft", "linker-tools")}
				</button>
			)}
			{!valid && (
				<Notice>
					{__(
						"Complete the source, interval selection and sampling fields, or remove this setup before saving the project.",
						"linker-tools",
					)}
				</Notice>
			)}
			{samples !== null && (
				<p>
					{sprintf(
						__("Maximum requested midpoint samples: %s", "linker-tools"),
						samples.toLocaleString(locale),
					)}
					{limits ? ` / ${limits.max_samples.toLocaleString(locale)}` : ""}
				</p>
			)}
			{samples !== null && !allowedSamples && (
				<Notice error>
					{__(
						"The requested sampling exceeds this service's sample budget. Reduce the selected intervals or grid sizes.",
						"linker-tools",
					)}
				</Notice>
			)}
			{isDirty(draft) && (
				<p>
					{__(
						"Save the project before requesting this geometric calculation.",
						"linker-tools",
					)}
				</p>
			)}
			<button
				type="button"
				className="lp-button"
				disabled={
					actionsDisabled ||
					disabled ||
					!supported ||
					!complete ||
					!currentModules ||
					!selected ||
					!compatibleRequest ||
					!sourceMatchesRoof ||
					binding.isFetching ||
					!!preview.error ||
					!preview.data ||
					!allowedSamples ||
					isDirty(draft) ||
					!!draft.pending ||
					!!draft.conflict
				}
				onClick={start}
			>
				{__("Calculate direct-beam visibility", "linker-tools")}
			</button>
		</section>
	);
}
