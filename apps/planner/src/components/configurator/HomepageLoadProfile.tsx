import { useCallback } from "react";
import type { HomepageProfileFile } from "../../data/homepageProfile.ts";
import { __ } from "../../i18n.ts";
import {
	emptyMapping,
	mappedProfile,
	ProfileMapping,
} from "../ProfileMapping.tsx";
import type { MappingFields } from "../ProfileMapping.tsx";

export interface HomepageProfileForm {
	readonly file: File | null;
	readonly delimiter: string;
	readonly mapping: MappingFields;
	readonly mappingValid: boolean;
	readonly source: string;
	readonly rights: string;
}

export function emptyHomepageProfile(): HomepageProfileForm {
	return {
		file: null,
		delimiter: "",
		mapping: {
			...emptyMapping(null),
			measurement: "gross_load",
			origin: "measured",
		},
		mappingValid: true,
		source: "",
		rights: "",
	};
}

export function homepageProfileFile(
	form: HomepageProfileForm,
): HomepageProfileFile | null {
	const mapping = form.delimiter && mappedProfile(form.mapping, form.delimiter);
	if (
		!form.file ||
		!mapping ||
		!form.mappingValid ||
		!form.source.trim() ||
		!form.rights.trim()
	)
		return null;
	return { file: form.file, mapping, source: form.source, rights: form.rights };
}

export function HomepageLoadProfile({
	form,
	locale,
	disabled,
	change,
}: {
	form: HomepageProfileForm;
	locale: string;
	disabled: boolean;
	change: (patch: Partial<HomepageProfileForm>) => void;
}) {
	const checkMapping = useCallback(
		(mappingValid: boolean) => change({ mappingValid }),
		[change],
	);
	return (
		<fieldset className="sc-card" disabled={disabled}>
			<label className="sc-field">
				<span>{__("Measured site load (CSV, optional)", "linker-tools")}</span>
				<input
					name="load_profile"
					type="file"
					accept=".csv,text/csv,text/plain"
					onChange={(event) => {
						const file = event.currentTarget.files?.[0] ?? null;
						change({ file, source: file?.name ?? "" });
					}}
				/>
			</label>
			{form.file && (
				<>
					<p>
						{__(
							"Use a file that records total electricity use before on-site solar or battery effects. Enter the column headings exactly as they appear in the file.",
							"linker-tools",
						)}
					</p>
					<div className="sc-fields">
						<label className="sc-field">
							<span>{__("Column delimiter", "linker-tools")}</span>
							<select
								name="load_profile_delimiter"
								required
								value={form.delimiter}
								onChange={(event) =>
									change({ delimiter: event.currentTarget.value })
								}
							>
								<option value="">
									{__("Choose an option", "linker-tools")}
								</option>
								<option value=";">{__("Semicolon", "linker-tools")}</option>
								<option value=",">{__("Comma", "linker-tools")}</option>
								<option value={"\t"}>{__("Tab", "linker-tools")}</option>
							</select>
						</label>
						<label className="sc-field">
							<span>{__("Source name", "linker-tools")}</span>
							<input
								name="load_profile_source"
								required
								value={form.source}
								maxLength={256}
								onChange={(event) =>
									change({ source: event.currentTarget.value })
								}
							/>
						</label>
						<label className="sc-field sc-field-wide">
							<span>
								{__("Source and permission to store privately", "linker-tools")}
							</span>
							<textarea
								name="load_profile_rights"
								required
								value={form.rights}
								maxLength={4096}
								onChange={(event) =>
									change({ rights: event.currentTarget.value })
								}
							/>
						</label>
					</div>
					<ProfileMapping
						columns={null}
						fields={form.mapping}
						locale={locale}
						grossLoadOnly
						onChange={(mapping) => change({ mapping })}
						onValidity={checkMapping}
					/>
				</>
			)}
		</fieldset>
	);
}
