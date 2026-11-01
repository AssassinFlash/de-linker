import type { Source } from "../../domain/geometry.ts";
import type { GeometryFormProps } from "./RoofForm.tsx";
import {
	GeometryExportPermission,
	GeometryForm,
	GeometryNumber,
	GeometryText,
} from "./GeometryForm.tsx";
import { __ } from "../../i18n.ts";

export function SourceForm({
	locale,
	commit,
	cancel,
	onValidity,
	source,
	referenceLocked = false,
}: GeometryFormProps & { source: Source; referenceLocked?: boolean }) {
	return (
		<GeometryForm
			title={__("Source properties", "linker-tools")}
			locale={locale}
			cancel={cancel}
			onValidity={onValidity}
			submit={(values) =>
				commit({
					type: "put_source",
					before: source,
					value: {
						...source,
						note: values.text("note"),
						rights_note: values.text("rights"),
						reference_url: values.text("url") || null,
						reference_sha256: referenceLocked
							? source.reference_sha256
							: values.text("hash") || null,
						acquired_at_utc: values.text("acquired") || null,
						spatial_precision_m: values.number("precision", {
							optional: true,
							min: 0,
						}),
						calibration_note: values.text("calibration"),
						permissions: {
							...source.permissions,
							export: values.text("export") as Source["permissions"]["export"],
						},
					},
				})
			}
		>
			<p className="lp-profile-help">
				{__(
					"Source statements are retained with the geometry. They describe the supplied evidence and permissions; they do not certify measurement accuracy or licence compliance.",
					"linker-tools",
				)}
			</p>
			<GeometryText
				name="note"
				label={__("Source reference", "linker-tools")}
				value={source.note}
				multiline
			/>
			<GeometryNumber
				name="precision"
				locale={locale}
				label={__("Declared spatial precision", "linker-tools")}
				value={source.spatial_precision_m}
				optional
				help={__(
					"0 or greater. An empty field means unknown. This is a source claim, separate from numerical calculation precision.",
					"linker-tools",
				)}
			/>
			<GeometryText
				name="calibration"
				label={__("Calibration and measurement conditions", "linker-tools")}
				value={source.calibration_note}
				multiline
			/>
			<GeometryText
				name="acquired"
				label={__("Acquired at UTC", "linker-tools")}
				value={source.acquired_at_utc ?? ""}
				optional
				help={__(
					"YYYY-MM-DDTHH:MM:SSZ; an empty field means not recorded.",
					"linker-tools",
				)}
			/>
			<GeometryText
				name="rights"
				label={__("Permission or licence basis", "linker-tools")}
				value={source.rights_note}
				multiline
			/>
			<GeometryText
				name="url"
				label={__("Reference URL", "linker-tools")}
				value={source.reference_url ?? ""}
				optional
			/>
			<GeometryText
				name="hash"
				label={__("Reference SHA-256", "linker-tools")}
				value={source.reference_sha256 ?? ""}
				readOnly={referenceLocked}
				optional
			/>
			<GeometryExportPermission value={source.permissions.export} />
		</GeometryForm>
	);
}
