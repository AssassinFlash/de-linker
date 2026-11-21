import { useEffect, useState } from "react";
import { __ } from "../../i18n.ts";
import type { Brief } from "../../domain/brief.ts";
import { NumberField } from "../NumberField.tsx";

export function SiteCoordinates({
	site,
	locale,
	change,
	onValidity,
}: {
	site: Brief["site"];
	locale: string;
	change: (field: "latitude" | "longitude", value: number | null) => void;
	onValidity: (valid: boolean) => void;
}) {
	const [latitudeValid, setLatitudeValid] = useState(true);
	const [longitudeValid, setLongitudeValid] = useState(true);
	useEffect(() => {
		onValidity(latitudeValid && longitudeValid);
	}, [latitudeValid, longitudeValid, onValidity]);
	useEffect(() => () => onValidity(true), [onValidity]);
	return (
		<>
			<NumberField
				label={__("Latitude", "linker-tools")}
				name="latitude"
				unit="°"
				locale={locale}
				min={-90}
				max={90}
				value={site.latitude}
				notation="point-or-comma"
				onChange={(value) => change("latitude", value)}
				onValidity={setLatitudeValid}
			/>
			<NumberField
				label={__("Longitude", "linker-tools")}
				name="longitude"
				unit="°"
				locale={locale}
				min={-180}
				max={180}
				value={site.longitude}
				notation="point-or-comma"
				onChange={(value) => change("longitude", value)}
				onValidity={setLongitudeValid}
			/>
		</>
	);
}
