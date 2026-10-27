import type { WeatherValidationFailure } from "../../data/weatherStatus.ts";
import { __, sprintf } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";

export function WeatherFailureNotice({
	failure,
	locale,
}: {
	failure: WeatherValidationFailure;
	locale: string;
}) {
	const message =
		failure.code === "weather_response_invalid"
			? __(
					"The official weather response did not pass validation and cannot be used for PV calculation.",
					"linker-tools",
				)
			: failure.reason === "negative_wind"
				? __(
						"The official weather source contains a negative wind-speed value and cannot be used for PV calculation.",
						"linker-tools",
					)
				: __(
						"The official weather source contains a negative irradiance value and cannot be used for PV calculation.",
						"linker-tools",
					);
	return (
		<Notice error>
			<p>{message}</p>
			<p>
				{__(
					"No usable weather dataset was created from this response.",
					"linker-tools",
				)}
			</p>
			{failure.code === "weather_source_quality_invalid" && (
				<p>
					{__("Source value", "linker-tools")}:{" "}
					{new Intl.NumberFormat(locale, {
						notation:
							Math.abs(failure.value) < 0.000001 ||
							Math.abs(failure.value) >= 1000000
								? "scientific"
								: "standard",
						maximumFractionDigits: 6,
					}).format(failure.value)}{" "}
					{failure.reason === "negative_wind" ? "m/s" : "W/m²"}
				</p>
			)}
			{failure.code === "weather_source_quality_invalid" && (
				<p>
					{sprintf(
						__("Source timestamp (UTC): %s", "linker-tools"),
						new Intl.DateTimeFormat(locale, {
							dateStyle: "medium",
							timeStyle: "short",
							timeZone: "UTC",
							hourCycle: "h23",
						}).format(new Date(failure.sourceTimestampUtc)),
					)}
				</p>
			)}
		</Notice>
	);
}
