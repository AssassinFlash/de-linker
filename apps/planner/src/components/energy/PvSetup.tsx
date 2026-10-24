import { useMemo } from "react";
import type { Draft } from "../../domain/draft.ts";
import { sameJson, isDirty } from "../../domain/draft.ts";
import {
	activePvGeometry,
	compilePv,
	preparePvInputs,
	readSolarSetup,
	solarInputs,
} from "../../domain/solarSetup.ts";
import { readObject } from "../../data/readProtocol.ts";
import type { JsonObject } from "../../data/protocol.ts";
import { ApiError } from "../../data/protocol.ts";
import { __, sprintf } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";
import { PvForm } from "./PvForm.tsx";

export function PvSetup({
	draft,
	edit,
	locale,
	disabled,
	actionsDisabled,
	valid,
	onValidity,
	onError,
	start,
	openDesign,
}: {
	draft: Draft;
	edit: (operation: (inputs: JsonObject) => JsonObject) => boolean;
	locale: string;
	disabled: boolean;
	actionsDisabled: boolean;
	valid: boolean;
	onValidity: (valid: boolean) => void;
	onError: (error: unknown) => void;
	start: () => void;
	openDesign: (() => void) | undefined;
}) {
	const inputs = draft.history.current,
		parsed = useMemo(() => {
			try {
				return {
					setup: readSolarSetup(inputs),
					layout: activePvGeometry(inputs.geometry),
				};
			} catch {
				return null;
			}
		}, [
			inputs.solar_setup,
			inputs.weather_acquisition,
			inputs.pv_generation,
			inputs.geometry,
		]);
	let prepared = false;
	try {
		prepared =
			!!parsed &&
			sameJson(
				compilePv(parsed.setup.pv, inputs.geometry),
				inputs.pv_generation,
			);
	} catch {
		/* Incomplete models and changed layouts remain editable. */
	}
	let weatherSelected = false;
	try {
		const selection = readObject(inputs.pv_preparation ?? {}),
			weatherId = selection.weather_asset_id;
		weatherSelected =
			selection.schema_version === 1 &&
			typeof weatherId === "string" &&
			/^[a-f0-9]{32}$/.test(weatherId);
	} catch {
		/* An unsupported saved selection cannot enable a new calculation. */
	}
	const dirty = isDirty(draft);
	if (!parsed)
		return (
			<Notice>
				<p>
					{__(
						"PV model settings need an editable roof layout. Saved inputs and previous calculations remain in the project.",
						"linker-tools",
					)}
				</p>
				{openDesign && (
					<button type="button" className="lp-text-button" onClick={openDesign}>
						{__("Review roof design", "linker-tools")}
					</button>
				)}
			</Notice>
		);
	return (
		<>
			<PvForm
				value={parsed.setup.pv}
				geometry={parsed.layout.geometry}
				arrays={parsed.layout.arrays}
				locale={locale}
				disabled={disabled}
				valid={valid}
				onValidity={onValidity}
				onChange={(pv) => {
					if (disabled) return;
					edit((current) =>
						solarInputs(current, { ...readSolarSetup(current), pv }),
					);
					onError(null);
				}}
			/>
			<div className="lp-scenario-sources">
				<h3>{__("Weather for this PV calculation", "linker-tools")}</h3>
				<p>
					{weatherSelected
						? __(
								"A weather source is selected in this draft. Before calculation, the saved weather record and its location are checked against the roof inputs.",
								"linker-tools",
							)
						: __(
								"A completed weather result must be selected in Saved calculations before PV generation can start.",
								"linker-tools",
							)}
				</p>
			</div>
			<div className="lp-energy-submit">
				<div>
					<strong>
						{prepared
							? __("PV model prepared in this draft", "linker-tools")
							: __("PV model settings need preparation", "linker-tools")}
					</strong>
					<p>
						{dirty || draft.pending
							? __(
									"The roof layout, PV model and weather selection must be recorded with Save project before PV generation can start.",
									"linker-tools",
								)
							: sprintf(
									__(
										"PV generation uses saved input revision %d.",
										"linker-tools",
									),
									draft.baseline.revision,
								)}
					</p>
				</div>
				<button
					type="button"
					className="lp-button lp-button-secondary"
					disabled={actionsDisabled || !valid}
					onClick={() => {
						try {
							preparePvInputs(inputs);
							if (!edit(preparePvInputs))
								throw new ApiError(409, "scenario_changed");
							onError(null);
						} catch (error) {
							onError(error);
						}
					}}
				>
					{__("Prepare PV model", "linker-tools")}
				</button>
				<button
					type="button"
					className="lp-button"
					onClick={start}
					disabled={
						actionsDisabled ||
						!valid ||
						!prepared ||
						!weatherSelected ||
						dirty ||
						!!draft.pending ||
						!!draft.conflict
					}
				>
					{__("Calculate PV for saved inputs", "linker-tools")}
				</button>
			</div>
		</>
	);
}
