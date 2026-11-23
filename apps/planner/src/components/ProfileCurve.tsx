/** Step rendering of the current owned preview page; no interpolated power points. */
import type { ProfilePreview } from "../domain/profiles.ts";
import { __ } from "../i18n.ts";

export function profileDateFormat(locale: string) {
	return new Intl.DateTimeFormat(locale, {
		dateStyle: "medium",
		timeStyle: "medium",
		hourCycle: "h23",
		timeZone: "UTC",
	});
}

export function ProfileCurve({
	preview,
	locale,
	title = __("PV profile · visible intervals", "linker-tools"),
}: {
	preview: ProfilePreview;
	locale: string;
	title?: string;
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
	const peakLabel =
		new Intl.NumberFormat(locale, { maximumFractionDigits: 2 }).format(peak) +
		" kW";
	const axisX = 18 + peakLabel.length * 14;
	const time = new Intl.DateTimeFormat(locale, {
		hour: "2-digit",
		minute: "2-digit",
		hourCycle: "h23",
		timeZone: "UTC",
	});
	const basis =
		preview.source.basis === "published_load_profile" &&
		typeof preview.source.profile === "string"
			? `BDEW/VDEW · ${preview.source.profile}`
			: null;
	// Drawing coordinates are a display layout, not calculation time resolution.
	const x = (instant: string) =>
			axisX + ((Date.parse(instant) - start) / (end - start)) * (624 - axisX),
		y = (power: number) => 164 - (power / scale) * 140;
	let path = "";
	for (let i = 0; i < rows.length; i++) {
		const row = rows[i]!;
		path += `${i > 0 && row.start_utc === rows[i - 1]!.end_utc ? "L" : "M"}${x(row.start_utc)},${y(row.interval_mean_kw)} H${x(row.end_utc)} `;
	}
	return (
		<figure className="sc-profile-review">
			<figcaption>
				{title}
				{basis && <small>{basis}</small>}
			</figcaption>
			<svg
				width="100%"
				height="200"
				viewBox="0 0 640 200"
				role="img"
				aria-label={title}
			>
				<title>{title}</title>
				<path
					className="sc-curve-grid"
					d={`M${axisX} 24 H624 M${axisX} 94 H624`}
				/>
				<text x={axisX} y="190" textAnchor="start">
					{time.format(start)}
				</text>
				<text x="624" y="190" textAnchor="end">
					{time.format(end)} UTC
				</text>
				<path
					d={`M${axisX} 16 V164 H624`}
					fill="none"
					stroke="currentColor"
					strokeWidth="1"
				/>
				<path
					className="sc-curve-series"
					d={path}
					fill="none"
					stroke="currentColor"
					strokeWidth="2"
				/>
				<text x={axisX - 8} textAnchor="end" y="28" fill="currentColor">
					{peakLabel}
				</text>
				<text x={axisX - 8} textAnchor="end" y="164" fill="currentColor">
					0
				</text>
			</svg>
			<p>{profileDateFormat(locale).formatRange(start, end)} UTC</p>
			<p>
				{__(
					"The chart shows only the visible interval page. The source summary and the saved energy calculation use their complete declared periods. The steps represent interval mean power; no finer measurements are implied.",
					"linker-tools",
				)}
			</p>
		</figure>
	);
}
