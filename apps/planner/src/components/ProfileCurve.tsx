/** Step rendering of the current owned preview page; no interpolated power points. */
import type { ProfilePreview } from "../domain/profiles.ts";
import { __ } from "../i18n.ts";

export function ProfileCurve({
	preview,
	locale,
}: {
	preview: ProfilePreview;
	locale: string;
}) {
	const rows = preview.rows;
	if (!rows.length) return null;
	const start = Date.parse(rows[0]!.start_utc),
		end = Date.parse(rows.at(-1)!.end_utc);
	if (
		!(end > start) ||
		rows.some(
			(row, i) =>
				Date.parse(row.end_utc) <= Date.parse(row.start_utc) ||
				(i > 0 && Date.parse(row.start_utc) < Date.parse(rows[i - 1]!.end_utc)),
		)
	)
		return null;
	const peak = Math.max(0, ...rows.map((row) => row.interval_mean_kw)),
		scale = peak || 1;
	// Drawing coordinates are a display layout, not calculation time resolution.
	const x = (instant: string) =>
			44 + ((Date.parse(instant) - start) / (end - start)) * 580,
		y = (power: number) => 164 - (power / scale) * 140;
	let path = "";
	for (let i = 0; i < rows.length; i++) {
		const row = rows[i]!;
		path += `${i > 0 && row.start_utc === rows[i - 1]!.end_utc ? "L" : "M"}${x(row.start_utc)},${y(row.interval_mean_kw)} H${x(row.end_utc)} `;
	}
	const title = __("PV profile · visible intervals", "linker-tools");
	return (
		<figure className="lp-profile-review">
			<figcaption>{title}</figcaption>
			<svg
				width="100%"
				height="200"
				viewBox="0 0 640 200"
				role="img"
				aria-label={title}
			>
				<title>{title}</title>
				<path
					d="M44 16 V164 H624"
					fill="none"
					stroke="currentColor"
					strokeWidth="1"
				/>
				<path d={path} fill="none" stroke="currentColor" strokeWidth="2" />
				<text x="4" y="28" fill="currentColor">
					{new Intl.NumberFormat(locale, { maximumFractionDigits: 2 }).format(
						peak,
					)}{" "}
					kW
				</text>
				<text x="12" y="180" fill="currentColor">
					0
				</text>
			</svg>
			<p>
				<time>{rows[0]!.start_utc}</time> → <time>{rows.at(-1)!.end_utc}</time>{" "}
				· UTC
			</p>
			<p>
				{__(
					"The chart shows only the visible interval page. The source summary and the saved energy calculation use their complete declared periods. The steps represent interval mean power; no finer measurements are implied.",
					"linker-tools",
				)}
			</p>
		</figure>
	);
}
