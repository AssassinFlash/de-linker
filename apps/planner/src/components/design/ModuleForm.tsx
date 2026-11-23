import { useState } from "react";
import type { ModuleSpec } from "../../domain/geometry.ts";
import {
	emptyPanelFields,
	panelFields,
	panelSpecification,
} from "../../domain/panelParameters.ts";
import { PanelMeasurementFields } from "../PanelMeasurementFields.tsx";
import type { GeometryFormProps } from "./RoofForm.tsx";
import { GeometryForm } from "./GeometryForm.tsx";
import { __ } from "../../i18n.ts";

export function ModuleForm({
	locale,
	commit,
	cancel,
	onValidity,
	module,
}: GeometryFormProps & { module: ModuleSpec | null }) {
	const [values, setValues] = useState(() =>
		module ? panelFields(module) : emptyPanelFields(),
	);
	const [id] = useState(() => module?.id ?? "module_" + crypto.randomUUID());
	const spec = panelSpecification(id, values);
	return (
		<GeometryForm
			title={__("Module specification", "linker-tools")}
			locale={locale}
			cancel={cancel}
			onValidity={onValidity}
			measurementHelp={false}
			submitDisabled={!spec}
			submit={() =>
				!!spec && commit({ type: "put_module", before: module, value: spec })
			}
		>
			<PanelMeasurementFields
				locale={locale}
				fields={values}
				change={setValues}
			/>
		</GeometryForm>
	);
}
