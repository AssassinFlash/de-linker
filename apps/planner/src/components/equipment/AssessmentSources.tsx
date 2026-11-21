import { useQuery } from "@tanstack/react-query";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import { currentProductQuery } from "../../data/currentProductQuery.ts";
import type { JsonObject } from "../../data/protocol.ts";
import { readEquipmentProducts } from "../../data/equipmentProducts.ts";
import { readObject } from "../../data/readProtocol.ts";
import { __ } from "../../i18n.ts";
import { EvidenceCard } from "../shared/EvidenceCard.tsx";
import { equipmentCheckLabel } from "./equipmentLabels.ts";

interface SourceGroup {
	url: string;
	productId: number | null;
	model: string;
	documentId: string;
	hash: string;
	pages: Set<number>;
	checks: Set<string>;
}

function collectSources(
	part: JsonObject,
	groups: Map<string, SourceGroup>,
	systemName = "",
) {
	const products = (part.selected_products ?? []) as JsonObject[];
	for (const check of part.checks as JsonObject[]) {
		const label = [
			systemName,
			equipmentCheckLabel(String(check.semantic_id ?? check.id)),
		]
			.filter(Boolean)
			.join(" · ");
		const facts = ((check.facts ?? []) as JsonObject[]).flatMap((f) =>
			f.source ? [readObject(f.source)] : [],
		);
		const additional = ((check.documents ?? []) as JsonObject[]).filter(
			(doc) =>
				!facts.some(
					(f) =>
						f.url === doc.url &&
						f.page === doc.page &&
						(!doc.product_id || f.product_id === doc.product_id),
				),
		);
		for (const doc of [...facts, ...additional]) {
			if (typeof doc.url !== "string") continue;
			const url = new URL(doc.url);
			url.hash = "";
			const productId =
				typeof doc.product_id === "number" ? doc.product_id : null;
			const product = products.find((p) => p.product_id === productId);
			const documentId =
				typeof doc.document_id === "string" ? doc.document_id : "";
			const hash = typeof doc.blob_sha256 === "string" ? doc.blob_sha256 : "";
			const key = JSON.stringify([productId, documentId || url.href, hash]);
			let group = groups.get(key);
			if (!group) {
				group = {
					url: url.href,
					productId,
					model: product
						? [product.brand, product.model].filter(Boolean).join(" ")
						: "",
					documentId,
					hash,
					pages: new Set(),
					checks: new Set(),
				};
				groups.set(key, group);
			}
			if (typeof doc.page === "number") group.pages.add(doc.page);
			group.checks.add(label);
		}
	}
	for (const system of (part.systems ?? []) as JsonObject[])
		collectSources(readObject(system.assessment), groups, String(system.name));
}

export function AssessmentSources({
	assessment,
	client,
	scope,
}: {
	assessment: JsonObject;
	client: PlannerClient;
	scope: string;
}) {
	const groups = new Map<string, SourceGroup>();
	collectSources(assessment, groups);
	const query = useQuery({
		...currentProductQuery(client, scope, groups.size > 0),
		select: readEquipmentProducts,
	});
	if (!groups.size)
		return (
			<p className="sc-muted">
				{__("No source documents recorded.", "linker-tools")}
			</p>
		);
	if (query.isError)
		return (
			<div role="alert" className="sc-card-state">
				{__(
					"The document sources could not be loaded. Try again.",
					"linker-tools",
				)}{" "}
				<button
					type="button"
					className="sc-button"
					onClick={() => void query.refetch()}
				>
					{__("Try again", "linker-tools")}
				</button>
			</div>
		);
	if (query.isPending)
		return <p role="status">{__("One moment…", "linker-tools")}</p>;
	return (
		<div className="linker-source-list">
			{[...groups.entries()].map(([key, doc]) => {
				const available = query.data.products
					.filter((p) => doc.productId === null || p.id === doc.productId)
					.flatMap((p) =>
						Array.isArray(p.documents)
							? p.documents.map((v) => readObject(v))
							: [],
					);
				const current = available.find((d) =>
					doc.documentId
						? doc.documentId === d.document_id
						: d.url === doc.url ||
							(Array.isArray(d.aliases) && d.aliases.includes(doc.url)),
				);
				const changed =
					!!current && !!doc.hash && current.blob_sha256 !== doc.hash;
				const file =
					new URL(doc.url).pathname.split("/").pop() ||
					__("Source document", "linker-tools");
				const title =
					!changed && typeof current?.title === "string" && current.title
						? current.title
						: file;
				let target: string | null = null;
				if (current && !changed && typeof current.url === "string") {
					const url = new URL(current.url);
					if (doc.hash)
						url.searchParams.set("linker_document_sha256", doc.hash);
					target = url.href;
				}
				return (
					<EvidenceCard
						key={key}
						title={title}
						url={target}
						models={doc.model ? [doc.model] : []}
						pages={[...doc.pages]}
						unavailable={
							changed
								? __(
										"This file differs from the version recorded with this result.",
										"linker-tools",
									)
								: !target
									? __(
											"This document is currently unavailable.",
											"linker-tools",
										)
									: ""
						}
					>
						<small>{[...doc.checks].join(" · ")}</small>
					</EvidenceCard>
				);
			})}
		</div>
	);
}
