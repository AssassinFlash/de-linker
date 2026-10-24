import { useState } from "react";
import type { ModuleSpec } from "../../domain/geometry.ts";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import { useModuleTemplates } from "../../data/useModuleTemplates.ts";
import type { GeometryFormProps } from "./RoofForm.tsx";
import { GeometryForm } from "./GeometryForm.tsx";
import { formatDecimal } from "../../domain/decimal.ts";
import { __, sprintf } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";

export function ModuleForm({
	locale,
	commit,
	cancel,
	onValidity,
	module,
	client,
	scope,
}: GeometryFormProps & {
	module: ModuleSpec | null;
	client: PlannerClient;
	scope: string;
}) {
	const catalog = useModuleTemplates(client, scope);
	const [selection, setSelection] = useState(
		module?.source.woo?.reference_input_id ?? "",
	);
	const template = catalog.data?.find(
		(item) => item.specification.source.woo?.reference_input_id === selection,
	);
	const specification = template?.specification;
	return (
		<GeometryForm
			title={__("Module specification", "linker-tools")}
			locale={locale}
			cancel={cancel}
			onValidity={onValidity}
			measurementHelp={false}
			submitDisabled={!specification || catalog.isFetching || !!catalog.error}
			submit={() =>
				!!specification &&
				commit({
					type: "put_module",
					before: module,
					value: {
						...specification,
						id:
							module?.id ?? "module_" + crypto.randomUUID().replaceAll("-", ""),
					},
				})
			}
		>
			<p>
				{__(
					"Dimensions, rated power at STC and the temperature coefficient come from Linker's product data.",
					"linker-tools",
				)}
			</p>
			{catalog.isFetching && (
				<p role="status">{__("Loading module data…", "linker-tools")}</p>
			)}
			{catalog.error && (
				<Notice error>
					{__("Module data could not be loaded.", "linker-tools")}
				</Notice>
			)}
			{catalog.data?.length === 0 && (
				<Notice>
					{__(
						"No module specification is currently available.",
						"linker-tools",
					)}
				</Notice>
			)}
			<label className="lp-field">
				<span>{__("Choose a module", "linker-tools")}</span>
				<select
					required
					value={selection}
					onChange={(event) => setSelection(event.currentTarget.value)}
					disabled={catalog.isFetching || !catalog.data?.length}
				>
					<option value="">{__("Choose a module", "linker-tools")}</option>
					{catalog.data?.map((item) => (
						<option
							key={item.specification.source.woo!.reference_input_id}
							value={item.specification.source.woo!.reference_input_id}
						>
							{item.specification.model}
						</option>
					))}
				</select>
			</label>
			<button
				type="button"
				className="lp-text-button"
				disabled={catalog.isFetching}
				onClick={() => void catalog.refetch()}
			>
				{__("Reload module data", "linker-tools")}
			</button>
			{specification && template && (
				<>
					<dl className="lp-design-quantities">
						{(
							[
								[
									__("Module length", "linker-tools"),
									specification.length_m,
									"m",
								],
								[
									__("Module width", "linker-tools"),
									specification.width_m,
									"m",
								],
								[
									__("Module thickness", "linker-tools"),
									specification.thickness_m,
									"m",
								],
								[
									__("Rated power at STC", "linker-tools"),
									specification.stc_power_w,
									"W",
								],
								[
									__(
										"Temperature coefficient of maximum power",
										"linker-tools",
									),
									template.parameters.gamma_pdc_per_c! * 100,
									"%/°C",
								],
							] as const
						).map(([label, value, unit]) => (
							<div key={label}>
								<dt>{label}</dt>
								<dd>
									{formatDecimal(value, locale)} <small>{unit}</small>
								</dd>
							</div>
						))}
					</dl>
					<p>
						<a
							href={specification.source.url!}
							target="_blank"
							rel="noreferrer"
						>
							{__("Source document", "linker-tools")}
						</a>{" "}
						·{" "}
						{sprintf(__("Page %d", "linker-tools"), specification.source.page!)}
					</p>
					<p>
						{__(
							"“Apply properties” updates the module values in this draft. “Save project” saves the changes.",
							"linker-tools",
						)}
					</p>
				</>
			)}
		</GeometryForm>
	);
}
