import type { Draft } from "../domain/draft.ts";
import { sameJson } from "../domain/draft.ts";
import { emptyBrief, readBrief } from "../domain/brief.ts";
import type { Configuration } from "../data/config.ts";
import type { Json } from "../data/protocol.ts";
import { formatDecimal } from "../domain/decimal.ts";
import { __ } from "../i18n.ts";

/** Both columns come from the retained local document and the actual server
 * revision. This is a comparison, not an automatic merge or a new save. */
export function RevisionComparison({
	draft,
	config,
}: {
	draft: Draft;
	config: Configuration;
}) {
	if (!draft.conflict) return null;
	const open =
		draft.history.current.brief === undefined
			? emptyBrief()
			: readBrief(draft.history.current.brief);
	const saved =
		draft.conflict.inputs.brief === undefined
			? emptyBrief()
			: readBrief(draft.conflict.inputs.brief);
	const choices: Record<string, string> = {
		residential: __("Residential", "linker-tools"),
		commercial: __("Commercial", "linker-tools"),
		industrial: __("Industrial", "linker-tools"),
		new_pv_storage: __("New PV and storage", "linker-tools"),
		storage_addition: __("Storage for existing PV", "linker-tools"),
		pv_only: __("PV without storage", "linker-tools"),
		bill_total: __("Electricity bills", "linker-tools"),
		user_estimate: __("Project estimate", "linker-tools"),
	};
	const rows: readonly [
		string,
		Json,
		Json,
		Readonly<Record<string, string>>?,
	][] = [
		[
			__("Site use", "linker-tools"),
			open.project_use,
			saved.project_use,
			choices,
		],
		[
			__("Planned system", "linker-tools"),
			open.system_scope,
			saved.system_scope,
			choices,
		],
		[
			__("Country", "linker-tools"),
			open.site.country_code,
			saved.site.country_code,
			config.countries,
		],
		[
			__("Address or location reference", "linker-tools"),
			open.site.location_label,
			saved.site.location_label,
		],
		[
			__("Latitude", "linker-tools") + " (°)",
			open.site.latitude,
			saved.site.latitude,
		],
		[
			__("Longitude", "linker-tools") + " (°)",
			open.site.longitude,
			saved.site.longitude,
		],
		[
			__("Project time zone", "linker-tools"),
			open.site.timezone,
			saved.site.timezone,
		],
		[
			__("Annual consumption", "linker-tools") + " (kWh)",
			open.annual_load.kwh,
			saved.annual_load.kwh,
		],
		[
			__("Basis for the annual figure", "linker-tools"),
			open.annual_load.basis,
			saved.annual_load.basis,
			choices,
		],
		[
			__("Source and period", "linker-tools"),
			open.annual_load.source_note,
			saved.annual_load.source_note,
		],
		[
			__("Requirements and site constraints", "linker-tools"),
			open.project_note,
			saved.project_note,
		],
	];
	const differences = rows.filter(
		([, local, remote]) => !sameJson(local, remote),
	);
	const { brief: _openBrief, ...otherOpen } = draft.history.current;
	const { brief: _savedBrief, ...otherSaved } = draft.conflict.inputs;
	const otherDiffers = !sameJson(otherOpen, otherSaved);
	function text(
		value: Json,
		labels?: Readonly<Record<string, string>>,
	): string {
		if (value === null || value === "")
			return __("Not specified", "linker-tools");
		if (typeof value === "number") return formatDecimal(value, config.locale);
		return typeof value === "string"
			? (labels?.[value] ?? value)
			: JSON.stringify(value);
	}
	return (
		<details className="lp-comparison" open>
			<summary>{__("Compare project data", "linker-tools")}</summary>
			{differences.length ? (
				<div className="lp-table-scroll">
					<table>
						<thead>
							<tr>
								<th scope="col">{__("Input", "linker-tools")}</th>
								<th scope="col">{__("Open changes", "linker-tools")}</th>
								<th scope="col">{__("Saved revision", "linker-tools")}</th>
							</tr>
						</thead>
						<tbody>
							{differences.map(([label, local, remote, labels]) => (
								<tr key={label}>
									<th scope="row">{label}</th>
									<td>{text(local, labels)}</td>
									<td>{text(remote, labels)}</td>
								</tr>
							))}
						</tbody>
					</table>
				</div>
			) : (
				<p>
					{__("The project brief matches the saved revision.", "linker-tools")}
				</p>
			)}
			{otherDiffers && (
				<details>
					<summary>
						{__("Additional project data differ", "linker-tools")}
					</summary>
					<h3>{__("Open changes", "linker-tools")}</h3>
					<pre>{JSON.stringify(otherOpen, null, 2)}</pre>
					<h3>{__("Saved revision", "linker-tools")}</h3>
					<pre>{JSON.stringify(otherSaved, null, 2)}</pre>
				</details>
			)}
		</details>
	);
}
