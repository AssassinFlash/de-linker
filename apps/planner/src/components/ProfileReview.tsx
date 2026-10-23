import type { Ref } from "react";
import type { ProfileAsset, ProfilePreview } from "../domain/profiles.ts";
import { __ } from "../i18n.ts";
import { measurementLabel, originLabel } from "./ProfileLabels.ts";
import { Notice } from "./Notice.tsx";
import { readObject } from "../data/readProtocol.ts";

export function ProfileReview({
	asset,
	preview,
	locale,
	loadMore,
	busy,
	headingRef,
}: {
	asset: ProfileAsset;
	preview: ProfilePreview;
	locale: string;
	loadMore: () => void;
	busy: boolean;
	headingRef?: Ref<HTMLHeadingElement>;
}) {
	const n = (value: number) =>
		new Intl.NumberFormat(locale, { maximumSignificantDigits: 15 }).format(
			value,
		);
	const s = preview.summary;
	const mapping =
		asset.purpose === "csv_profile_v1"
			? readObject(asset.metadata.csv_mapping)
			: null;
	const provenance = readObject(asset.metadata.provenance ?? {});
	const facts: [string, string][] = [
		[
			__("Source label", "linker-tools"),
			String(provenance.label ?? __("Not specified", "linker-tools")),
		],
		[
			__("Measurement point", "linker-tools"),
			measurementLabel(preview.measurement),
		],
		[
			__("Source type", "linker-tools"),
			originLabel(String(preview.source.origin)),
		],
		...(mapping
			? ([
					[
						__("Original value meaning", "linker-tools"),
						mapping.value_kind === "interval_average_kw"
							? __("Average power over each interval · kW", "linker-tools")
							: __("Energy within each interval · kWh", "linker-tools"),
					],
					[__("Source time zone", "linker-tools"), String(mapping.timezone)],
					[
						__("The timestamp identifies…", "linker-tools"),
						mapping.timestamp_role === "start"
							? __("The start of the interval", "linker-tools")
							: __("The end of the interval", "linker-tools"),
					],
				] as [string, string][])
			: []),
		[
			__("Energy in covered intervals", "linker-tools"),
			n(s.energy_kwh) + " kWh",
		],
		[__("Data records", "linker-tools"), n(s.interval_count)],
		[
			__("Covered duration", "linker-tools"),
			n(s.covered_seconds / 3600) + " h",
		],
		[
			__("Gap duration within the source period", "linker-tools"),
			n(s.gap_seconds / 3600) + " h",
		],
		[__("Gaps", "linker-tools"), n(s.gap_count)],
		[
			__("Longest original interval", "linker-tools"),
			n(s.native_max_interval_seconds / 60) + " min",
		],
		[
			__("Effective resolution limit", "linker-tools"),
			n(s.effective_max_interval_seconds / 60) + " min",
		],
		[
			__("Minimum interval mean", "linker-tools"),
			n(s.min_interval_mean_kw) + " kW",
		],
		[
			__("Maximum interval mean", "linker-tools"),
			n(s.max_interval_mean_kw) + " kW",
		],
	];
	return (
		<div className="lp-profile-review">
			<h3
				ref={headingRef}
				tabIndex={headingRef ? -1 : undefined}
				className="lp-focus-target"
			>
				{__("Data interpretation", "linker-tools")}
			</h3>
			<p className="lp-profile-range">
				<time dateTime={s.start_utc}>{s.start_utc}</time> →{" "}
				<time dateTime={s.end_utc}>{s.end_utc}</time> · UTC
			</p>
			<dl className="lp-profile-facts">
				{facts.map(([label, value]) => (
					<div key={label}>
						<dt>{label}</dt>
						<dd>{value}</dd>
					</div>
				))}
			</dl>
			<Notice>
				{__(
					"The summary covers the full source period shown above. Maximum power is an interval average. This review does not determine instantaneous peaks, battery size or suitability for a calculation.",
					"linker-tools",
				)}
			</Notice>
			{s.gap_count > 0 && (
				<Notice error>
					{__(
						"The source contains gaps. Missing intervals have not been filled with zeros or estimated values.",
						"linker-tools",
					)}
				</Notice>
			)}
			{preview.measurement === "net_import" && (
				<Notice>
					<p>
						{__(
							"For net grid import, energy is imports minus exports over the covered intervals.",
							"linker-tools",
						)}
					</p>
					<p>
						{__(
							"Net grid import can be affected by on-site generation and storage. Total site consumption cannot be derived from net import alone.",
							"linker-tools",
						)}
					</p>
				</Notice>
			)}
			{s.reconstructed_means && (
				<Notice>
					{__(
						"Some interval means were reconstructed. Finer output intervals do not create finer original observations.",
						"linker-tools",
					)}
				</Notice>
			)}
			<div
				className="lp-table-scroll"
				role="region"
				aria-label={__("Interpreted intervals", "linker-tools")}
				tabIndex={0}
			>
				<table className="lp-data-table">
					<caption>
						{__("Interpreted intervals · UTC · average kW", "linker-tools")}
					</caption>
					<thead>
						<tr>
							<th scope="col">{__("Start", "linker-tools")}</th>
							<th scope="col">{__("End", "linker-tools")}</th>
							<th scope="col">kW</th>
						</tr>
					</thead>
					<tbody>
						{preview.rows.map((row) => (
							<tr key={row.interval_index}>
								<td>{row.start_utc}</td>
								<td>{row.end_utc}</td>
								<td>{n(row.interval_mean_kw)}</td>
							</tr>
						))}
					</tbody>
				</table>
			</div>
			{preview.next_offset !== null && (
				<button
					type="button"
					className="lp-text-button"
					disabled={busy}
					onClick={loadMore}
				>
					{__("Next intervals", "linker-tools")}
				</button>
			)}
			{preview.first_gaps.length > 0 && (
				<details className="lp-comparison">
					<summary>{__("Gap locations · UTC", "linker-tools")}</summary>
					<ul>
						{preview.first_gaps.map((gap) => (
							<li key={gap.start_utc}>
								{gap.start_utc} → {gap.end_utc}
							</li>
						))}
					</ul>
					{preview.gaps_truncated && (
						<p>
							{__(
								"Only the first gap locations are shown. Totals cover the complete profile.",
								"linker-tools",
							)}
						</p>
					)}
				</details>
			)}
			<details className="lp-comparison">
				<summary>
					{__("Original source and interpretation record", "linker-tools")}
				</summary>
				<dl className="lp-source-hashes">
					<dt>{__("Original file SHA-256", "linker-tools")}</dt>
					<dd>{asset.content_sha256}</dd>
					<dt>{__("Import metadata SHA-256", "linker-tools")}</dt>
					<dd>{asset.metadata_sha256}</dd>
				</dl>
				<pre>
					{JSON.stringify(
						{
							metadata: asset.metadata,
							source: preview.source,
							transformations: preview.transformations,
						},
						null,
						2,
					)}
				</pre>
			</details>
		</div>
	);
}
