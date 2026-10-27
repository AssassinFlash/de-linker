import { useMemo } from "react";
import type { Draft } from "../../domain/draft.ts";
import { sameJson, isDirty } from "../../domain/draft.ts";
import {
	readSolarSetup,
	solarInputs,
	compileWeather,
	prepareWeatherInputs,
} from "../../domain/solarSetup.ts";
import { readGeometry } from "../../domain/validateGeometry.ts";
import geometryPolicy from "../../contracts/geometry-policy.json" with { type: "json" };
import type { JsonObject } from "../../data/protocol.ts";
import { ApiError } from "../../data/protocol.ts";
import type { GeometryDocument } from "../../domain/geometry.ts";
import { __, sprintf } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";
import { WeatherForm } from "./WeatherForm.tsx";

export function WeatherSetup({
	draft,
	edit,
	locale,
	disabled,
	actionsDisabled,
	valid,
	onValidity,
	onError,
	start,
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
}) {
	const inputs = draft.history.current,
		parsed = useMemo(() => {
			try {
				return { value: readSolarSetup(inputs), error: null };
			} catch (error) {
				return { value: null, error };
			}
		}, [inputs.solar_setup, inputs.weather_acquisition, inputs.pv_generation]);
	const anchor = useMemo<
		GeometryDocument["coordinate_system"]["anchor"]
	>(() => {
		try {
			return inputs.geometry === undefined
				? null
				: readGeometry(inputs.geometry, geometryPolicy).coordinate_system
						.anchor;
		} catch {
			return null; /* An uneditable geometry cannot supply a location. */
		}
	}, [inputs.geometry]);
	const setup = parsed.value;
	let prepared = false;
	try {
		prepared =
			!!setup &&
			sameJson(compileWeather(setup.weather), inputs.weather_acquisition);
	} catch {
		/* Incomplete inputs stay editable. */
	}
	const dirty = isDirty(draft);
	if (!setup)
		return (
			<Notice error>
				{__(
					"These weather settings cannot be edited here. The saved inputs and task history remain available.",
					"linker-tools",
				)}
			</Notice>
		);
	return (
		<>
			<WeatherForm
				value={setup.weather}
				anchor={anchor}
				locale={locale}
				disabled={disabled}
				onValidity={onValidity}
				onChange={(weather) => {
					if (disabled) return;
					edit((current) =>
						solarInputs(current, { ...readSolarSetup(current), weather }),
					);
					onError(null);
				}}
			/>
			<div className="lp-energy-submit">
				<div>
					<strong>
						{prepared
							? __("Weather settings prepared in this draft", "linker-tools")
							: __("Weather settings need preparation", "linker-tools")}
					</strong>
					<p>
						{dirty || draft.pending
							? __(
									"Save project records these settings before a weather request can start.",
									"linker-tools",
								)
							: sprintf(
									__(
										"A weather request uses saved input revision %d.",
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
							prepareWeatherInputs(inputs);
							if (!edit(prepareWeatherInputs))
								throw new ApiError(409, "scenario_changed");
							onError(null);
						} catch (error) {
							onError(error);
						}
					}}
				>
					{__("Prepare weather settings", "linker-tools")}
				</button>
				<button
					type="button"
					className="lp-button"
					disabled={
						actionsDisabled ||
						!valid ||
						!prepared ||
						dirty ||
						!!draft.pending ||
						!!draft.conflict
					}
					onClick={start}
				>
					{__("Request weather for saved inputs", "linker-tools")}
				</button>
			</div>
		</>
	);
}
