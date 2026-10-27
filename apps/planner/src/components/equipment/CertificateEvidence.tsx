import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import type { PlanningRun } from "../../data/planningProtocol.ts";
import { readCertificateEvidence } from "../../data/certificateEvidence.ts";
import { __, sprintf } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";
import { DeviceConditionReview } from "./DeviceConditionReview.tsx";

type CandidateReference = { id: string; assessment_sha256: string };
function Sources({
	client,
	scope,
	run,
	candidate,
}: {
	client: PlannerClient;
	scope: string;
	run: PlanningRun;
	candidate: CandidateReference | null;
}) {
	const query = useQuery({
		queryKey: ["certificate-evidence", scope, run.id, candidate?.id],
		enabled: client.isCurrentScope(scope),
		retry: false,
		staleTime: 0,
		refetchOnMount: "always",
		refetchOnWindowFocus: false,
		queryFn: async ({ signal }) =>
			readCertificateEvidence(
				await client.query(
					"equipment/certificates/read",
					{
						schema_version: 1,
						run_id: run.id,
						candidate_id: candidate?.id ?? null,
					},
					scope,
					signal,
				),
				run,
				candidate,
				client.origin,
			),
	});
	if (query.isPending || query.isFetching)
		return <p role="status">{__("One moment…", "linker-tools")}</p>;
	if (query.isError || !query.data)
		return (
			<Notice error>
				<p>
					{__(
						"The document sources could not be loaded. Try again.",
						"linker-tools",
					)}
				</p>
				<button
					type="button"
					className="lp-text-button"
					onClick={() => void query.refetch()}
				>
					{__("Try again", "linker-tools")}
				</button>
			</Notice>
		);
	const products = new Map(
		query.data.products.map((product) => [
			product.product_id,
			`${product.brand} ${product.model}`.trim(),
		]),
	);
	return (
		<>
			<p>
				{__(
					"These documents were linked to the selected products when this result was recorded. Their applicability to this project’s models, firmware, configuration, standard editions and annexes has not been assessed here. Compliance with country-specific requirements, installation approval and grid-operator acceptance require separate evidence.",
					"linker-tools",
				)}
			</p>
			<p className="lp-profile-help">
				{sprintf(__("Input revision %d", "linker-tools"), run.revision)}
			</p>
			{query.data.condition_review && (
				<DeviceConditionReview
					review={query.data.condition_review}
					documents={query.data.documents}
				/>
			)}
			{query.data.documents.length === 0 ? (
				<p>
					{__(
						"No certificates or related product documents were recorded for the selected products.",
						"linker-tools",
					)}
				</p>
			) : (
				query.data.documents.map((doc) => (
					<section className="lp-result-section" key={doc.document_id}>
						<h5>{doc.title || __("Source document", "linker-tools")}</h5>
						<p>{doc.product_ids.map((id) => products.get(id)).join(" · ")}</p>
						{doc.access.status === "available" && doc.access.url ? (
							<a href={doc.access.url} target="_blank" rel="noreferrer">
								{__("Open document", "linker-tools")}
							</a>
						) : (
							<p>
								{doc.access.status === "source_changed"
									? __(
											"This file differs from the version recorded with this result.",
											"linker-tools",
										)
									: __(
											"This document is currently unavailable.",
											"linker-tools",
										)}
							</p>
						)}
						<details className="lp-comparison">
							<summary>{__("Recorded source details", "linker-tools")}</summary>
							<dl className="lp-run-records">
								<div>
									<dt>SHA-256</dt>
									<dd>
										<code>{doc.blob_sha256}</code>
									</dd>
								</div>
								<div>
									<dt>{__("Recorded document revision", "linker-tools")}</dt>
									<dd>
										<code>{doc.document_revision}</code>
									</dd>
								</div>
							</dl>
						</details>
					</section>
				))
			)}
		</>
	);
}

/** Opening reads metadata and current access; no job, recalculation or new source. */
export function CertificateEvidence(props: {
	client: PlannerClient;
	scope: string;
	run: PlanningRun;
	candidate?: CandidateReference | null;
}) {
	const [open, setOpen] = useState(false);
	return (
		<details
			className="lp-comparison"
			onToggle={(event) => setOpen(event.currentTarget.open)}
		>
			<summary>
				{__("Certificates and related product documents", "linker-tools")}
			</summary>
			{open && <Sources {...props} candidate={props.candidate ?? null} />}
		</details>
	);
}
