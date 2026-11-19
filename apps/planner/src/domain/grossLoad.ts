import type { JsonObject } from "../data/protocol.ts";
import { readScenarioDraft } from "./energyScenario.ts";
import { readSelections } from "./profiles.ts";
import type { ProfilePreview } from "./profiles.ts";
import { KNOWN_PV_MODEL, referenceDraft } from "./pvgisReference.ts";

export function attachGrossLoad(
	inputs: JsonObject,
	profile: ProfilePreview,
): JsonObject {
	const scenario =
		inputs.energy_scenario === undefined
			? null
			: readScenarioDraft(inputs.energy_scenario);
	const followsKnownPvProfile =
		scenario?.schedule.length === 1 &&
		scenario.schedule[0]?.mode === "connected" &&
		referenceDraft(inputs).model === KNOWN_PV_MODEL;
	return {
		...inputs,
		...(scenario
			? {
					energy_scenario: {
						...scenario,
						schedule: scenario.schedule.map((period) =>
							followsKnownPvProfile ||
							(period.start_utc === "" && period.end_utc === "")
								? {
										...period,
										start_utc: profile.summary.start_utc,
										end_utc: profile.summary.end_utc,
									}
								: period,
						),
					},
				}
			: {}),
		profile_selections: {
			schema_version: 1,
			selected: {
				...readSelections(inputs.profile_selections).selected,
				gross_load: profile.asset_id,
			},
		},
	};
}
