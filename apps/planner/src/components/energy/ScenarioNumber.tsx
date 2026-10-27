import { useCallback, useEffect } from "react";
import { NumberField } from "../NumberField.tsx";

/** Stable validity callbacks preserve unfinished decimal input across rerenders. */
export function ScenarioNumber({
	field,
	label,
	value,
	unit,
	locale,
	onChange,
	report,
	max,
	min = 0,
	integer,
}: {
	field: string;
	label: string;
	value: number | null;
	unit: string;
	locale: string;
	onChange: (value: number | null) => void;
	report: (field: string, valid: boolean) => void;
	max?: number;
	min?: number | null;
	integer?: boolean;
}) {
	const validity = useCallback(
		(valid: boolean) => report(field, valid),
		[field, report],
	);
	useEffect(() => () => report(field, true), [field, report]);
	return (
		<NumberField
			label={label}
			value={value}
			unit={unit}
			locale={locale}
			{...(min === null ? {} : { min })}
			{...(max === undefined ? {} : { max })}
			{...(integer === undefined ? {} : { integer })}
			onChange={onChange}
			onValidity={validity}
		/>
	);
}
