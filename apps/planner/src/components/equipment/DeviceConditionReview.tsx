import type { CertificateDocument } from "../../data/certificateEvidence.ts";
import type {
	ConditionObligation,
	EquipmentConditionReview,
} from "../../data/equipmentConditionReview.ts";
import type { EquipmentSelectionRef } from "../../domain/equipmentConditionInputs.ts";
import { __, sprintf } from "../../i18n.ts";

function deviceLabel(ref: EquipmentSelectionRef): string {
	if (ref.kind === "plant_controller")
		return sprintf(
			__("Coordination group %s · Shared controller", "linker-tools"),
			ref.group_id,
		);
	const role = {
		inverter: __("Inverter", "linker-tools"),
		battery: __("Battery", "linker-tools"),
		accessory: __("Accessory", "linker-tools"),
	}[ref.role];
	return ref.kind === "single"
		? role
		: `${sprintf(__("System %s", "linker-tools"), ref.unit_id)} · ${role}`;
}
function reasonLabel(reason: string): string {
	switch (reason) {
		case "model_field_unresolved":
			return __(
				"The labelled model field could not be read as an explicit list of model names.",
				"linker-tools",
			);
		case "project_model_unresolved":
			return __(
				"The project model entry could not be compared as a single literal model name.",
				"linker-tools",
			);
		case "literal_model_list_match":
			return __(
				"The compared model appears in the literal list on this file’s cover.",
				"linker-tools",
			);
		case "literal_model_not_listed":
			return __(
				"The compared model does not appear in the literal list on this file’s cover. Other files require their own review.",
				"linker-tools",
			);
		case "firmware_field_unresolved":
			return __(
				"The labelled firmware or software field could not be read as one explicit version. Lists, ranges and component-specific versions remain unresolved.",
				"linker-tools",
			);
		case "project_firmware_missing":
			return __(
				"No firmware or software version was declared for this device in the project.",
				"linker-tools",
			);
		case "project_firmware_unresolved":
			return __(
				"The project entry could not be compared as one explicit firmware or software version.",
				"linker-tools",
			);
		case "literal_firmware_equal":
			return __(
				"The project version exactly matches the version printed in this file’s cover field.",
				"linker-tools",
			);
		case "literal_firmware_different":
			return __(
				"The project version differs from the version printed in this file’s cover field. This comparison applies to this file only.",
				"linker-tools",
			);
		default:
			return __("This comparison remains unresolved.", "linker-tools");
	}
}
function obligationLabel(id: ConditionObligation): string {
	return {
		document_scope: __(
			"Scope and applicability of each document",
			"linker-tools",
		),
		other_pages_and_reports: __(
			"Other pages and referenced test reports",
			"linker-tools",
		),
		annex_conditions: __(
			"Annex identity, completeness and conditions",
			"linker-tools",
		),
		hardware_and_configuration: __(
			"Hardware version and device configuration",
			"linker-tools",
		),
		operating_mode: __("Operating mode", "linker-tools"),
		country_and_dso_settings: __(
			"Country settings and grid-operator requirements",
			"linker-tools",
		),
		standard_edition_and_transition: __(
			"Applicable standard edition and transition rules",
			"linker-tools",
		),
		issuer_current_status: __(
			"Current status with the document issuer",
			"linker-tools",
		),
		project_grid_assessment: __(
			"Grid assessment for this project",
			"linker-tools",
		),
		dso_permission: __("Grid-operator permission", "linker-tools"),
	}[id];
}

/** Per-device/per-original-file comparisons never collapse into product/project approval. */
export function DeviceConditionReview({
	review,
	documents,
}: {
	review: EquipmentConditionReview;
	documents: CertificateDocument[];
}) {
	return (
		<section className="lp-result-section">
			<h4>{__("Project device details", "linker-tools")}</h4>
			<p>
				{__(
					"These comparisons use the project entries and the labelled model and firmware or software fields on each original file’s first page. Each result concerns only the text read on that page. Project suitability, country requirements and installation approval remain unassessed.",
					"linker-tools",
				)}
			</p>
			{review.devices.map((device, index) => (
				<section className="lp-result-section" key={index}>
					<h5>
						{deviceLabel(device.selection_ref)} · {device.woo_model}
					</h5>
					<dl className="lp-run-records">
						<div>
							<dt>{__("Model identity", "linker-tools")}</dt>
							<dd>
								{device.model_identity.status === "unprovided"
									? __("Project model not declared", "linker-tools")
									: device.model_identity.status === "same_text"
										? __(
												"Project and product model texts match",
												"linker-tools",
											)
										: __("Model identity requires review", "linker-tools")}
							</dd>
						</div>
						<div>
							<dt>{__("Declared model", "linker-tools")}</dt>
							<dd>{device.declared_model ?? __("Unknown", "linker-tools")}</dd>
						</div>
						<div>
							<dt>{__("Selected product model", "linker-tools")}</dt>
							<dd>{device.model_identity.selected_woo_value}</dd>
						</div>
						<div>
							<dt>{__("Declared firmware or software", "linker-tools")}</dt>
							<dd>
								{device.declared_firmware ?? __("Unknown", "linker-tools")}
							</dd>
						</div>
						<div>
							<dt>{__("Source note", "linker-tools")}</dt>
							<dd>{device.source_note ?? __("Unknown", "linker-tools")}</dd>
						</div>
					</dl>
					{device.model_identity.status === "different_text" && (
						<p>
							{__(
								"The project model text differs from the selected product model. Their identity has not been established and needs reconciliation.",
								"linker-tools",
							)}
						</p>
					)}
					{device.documents.length === 0 && (
						<p>
							{__(
								"No linked certificate file was recorded for this device. Its conditions remain unresolved.",
								"linker-tools",
							)}
						</p>
					)}
					{device.documents.map((doc) => {
						const source = documents.find(
							(d) => d.document_id === doc.document_id,
						)!;
						return (
							<details className="lp-comparison" key={doc.document_id}>
								<summary>
									{source.title || __("Source document", "linker-tools")}
								</summary>
								<dl className="lp-run-records">
									<div>
										<dt>{__("Model comparison", "linker-tools")}</dt>
										<dd>
											{doc.model.status === "listed"
												? __("Model listed on this page", "linker-tools")
												: doc.model.status === "not_listed"
													? __("Model not listed on this page", "linker-tools")
													: __("Model comparison unresolved", "linker-tools")}
										</dd>
									</div>
									<div>
										<dt>
											{doc.model.comparison_basis === "project_declared"
												? __("Compared project model", "linker-tools")
												: __(
														"Compared product model reference",
														"linker-tools",
													)}
										</dt>
										<dd>
											{doc.model.compared_value ??
												__("Unknown", "linker-tools")}
										</dd>
									</div>
									<div>
										<dt>{__("Models printed on this page", "linker-tools")}</dt>
										<dd>
											{doc.model.declared_values?.join(" · ") ??
												__("Unresolved", "linker-tools")}
										</dd>
									</div>
									<div>
										<dt>
											{__("Firmware or software comparison", "linker-tools")}
										</dt>
										<dd>
											{doc.firmware.status === "exact_match"
												? __("Exact version match in this file", "linker-tools")
												: doc.firmware.status === "conflict"
													? __("Version differs from this file", "linker-tools")
													: __("Version comparison unresolved", "linker-tools")}
										</dd>
									</div>
									<div>
										<dt>
											{__("Version printed on this page", "linker-tools")}
										</dt>
										<dd>
											{doc.firmware.declared_value ??
												__("Unresolved", "linker-tools")}
										</dd>
									</div>
								</dl>
								{doc.model.comparison_basis === "selected_woo_model" && (
									<p className="lp-profile-help">
										{__(
											"The product model is a selection reference. No model was declared as planned or observed for this device.",
											"linker-tools",
										)}
									</p>
								)}
								<p>{reasonLabel(doc.model.reason)}</p>
								<p>{reasonLabel(doc.firmware.reason)}</p>
								{(doc.model.page === 1 || doc.firmware.page === 1) && (
									<p className="lp-profile-help">
										{sprintf(__("Page %d", "linker-tools"), 1)}
									</p>
								)}
								<p>
									{__(
										"Annex conditions remain unresolved. The identity and completeness of any annex have not been verified.",
										"linker-tools",
									)}
								</p>
								{typeof doc.annex.source?.quote === "string" && (
									<blockquote>{doc.annex.source.quote}</blockquote>
								)}
								<details className="lp-comparison">
									<summary>
										{__("Recorded source details", "linker-tools")}
									</summary>
									<dl className="lp-run-records">
										<div>
											<dt>{__("Recorded product revision", "linker-tools")}</dt>
											<dd>
												<code>{device.product_revision}</code>
											</dd>
										</div>
										<div>
											<dt>
												{__("Recorded document revision", "linker-tools")}
											</dt>
											<dd>
												<code>{doc.document_revision}</code>
											</dd>
										</div>
										<div>
											<dt>SHA-256</dt>
											<dd>
												<code>{doc.blob_sha256}</code>
											</dd>
										</div>
									</dl>
								</details>
							</details>
						);
					})}
				</section>
			))}
			<details className="lp-comparison">
				<summary>
					{__("Still requires separate review", "linker-tools")}
				</summary>
				<ul>
					{review.remaining_obligations.map((id) => (
						<li key={id}>{obligationLabel(id)}</li>
					))}
				</ul>
			</details>
		</section>
	);
}
