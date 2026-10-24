/** Source notes are saved with the model, not substituted for verified evidence.
 * The 4096-character bound is Text in pv-generation.schema.json. */
export function ParameterNote({
	label,
	value,
	onChange,
}: {
	label: string;
	value: string;
	onChange: (value: string) => void;
}) {
	return (
		<label className="lp-field">
			<span>{label}</span>
			<textarea
				rows={2}
				maxLength={4096}
				value={value}
				onChange={(event) => onChange(event.currentTarget.value)}
			/>
		</label>
	);
}
