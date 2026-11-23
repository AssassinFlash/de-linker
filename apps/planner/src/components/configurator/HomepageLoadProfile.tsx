import { FileDropzone } from "../FileDropzone.tsx";
import { useCallback } from "react";
import type {
	HomepageProfileFile,
	HomepageProfileUpload,
} from "../../data/homepageProfile.ts";
import { __ } from "../../i18n.ts";
import {
	emptyMapping,
	mappedProfile,
	ProfileMapping,
} from "../ProfileMapping.tsx";
import type { MappingFields } from "../ProfileMapping.tsx";

export interface HomepageProfileForm {
	readonly file: File | null;
	readonly recoveredFile: boolean;
	readonly delimiter: string;
	readonly mapping: MappingFields;
	readonly mappingValid: boolean;
	readonly source: string;
	readonly rights: string;
}

export function emptyHomepageProfile(): HomepageProfileForm {
	return {
		file: null,
		recoveredFile: false,
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

export function restoreHomepageProfile(
	upload: HomepageProfileUpload,
): HomepageProfileForm {
	const { mapping, content_base64, source_label, rights_note } = upload.request;
	const bytes = Uint8Array.from(atob(content_base64), (char) =>
		char.charCodeAt(0),
	);
	return {
		file: new File([bytes], source_label, { type: "text/csv" }),
		recoveredFile: true,
		delimiter: mapping.delimiter,
		mapping: {
			timestamp: mapping.timestamp_column,
			value: mapping.value_column,
			measurement: mapping.measurement,
			unit: mapping.value_kind,
			timeRole: mapping.timestamp_role,
			timezone: mapping.timezone,
			origin: mapping.origin,
			durationMode: mapping.end_timestamp_column ? "ends" : "fixed",
			minutes:
				mapping.interval_seconds === null
					? null
					: mapping.interval_seconds / 60,
			end: mapping.end_timestamp_column ?? "",
			fold: mapping.fold_column ?? "",
			endFold: mapping.end_fold_column ?? "",
			decimal: mapping.decimal,
		},
		mappingValid: true,
		source: source_label,
		rights: rights_note,
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
	discard,
}: {
	form: HomepageProfileForm;
	locale: string;
	disabled: boolean;
	change: (patch: Partial<HomepageProfileForm>) => void;
	discard?: () => void;
}) {
	const checkMapping = useCallback(
		(mappingValid: boolean) => change({ mappingValid }),
		[change],
	);
	return (
		<fieldset className="sc-card" disabled={disabled}>
			<FileDropzone
				label={__("Measured site load (CSV, optional)", "linker-tools")}
				action={__("Choose CSV file", "linker-tools")}
				name="load_profile"
				accept=".csv,text/csv,text/plain"
				filename={
					form.recoveredFile
						? __("Recovered source file", "linker-tools")
						: form.file?.name
				}
				disabled={disabled}
				onFile={(file) =>
					change({ file, recoveredFile: false, source: file.name })
				}
			/>
			{form.recoveredFile && (
				<p>
					{__(
						"Your saved CSV is ready. Choose another file to replace it.",
						"linker-tools",
					)}
				</p>
			)}
			{discard && (
				<div className="sc-actions">
					<button className="sc-button" type="button" onClick={discard}>
						{__("Compare without this load profile", "linker-tools")}
					</button>
				</div>
			)}
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
