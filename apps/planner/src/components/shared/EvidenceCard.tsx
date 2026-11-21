import type { ReactNode } from "react";
import { __, sprintf } from "../../i18n.ts";

export function EvidenceCard({
	title,
	models = [],
	url,
	pages = [],
	unavailable,
	children,
}: {
	title: string;
	models?: readonly string[];
	url?: string | null;
	pages?: readonly number[];
	unavailable?: string;
	children?: ReactNode;
}) {
	const cited = [...new Set(pages)].sort((a, b) => a - b);
	return (
		<article className="linker-source-card">
			<div className="linker-source-card__identity">
				{models.length > 0 && <small>{models.join(" · ")}</small>}
				<strong>{title}</strong>
			</div>
			{children}
			{url && !unavailable ? (
				<div className="linker-source-card__links">
					{cited.length ? (
						cited.map((page) => (
							<a
								key={page}
								href={url.split("#")[0] + "#page=" + page}
								target="_blank"
								rel="noopener noreferrer"
							>
								{sprintf(__("Page %d", "linker-tools"), page)}
							</a>
						))
					) : (
						<a href={url} target="_blank" rel="noopener noreferrer">
							{__("Open document", "linker-tools")}
						</a>
					)}
				</div>
			) : (
				unavailable && (
					<small>
						{cited.length > 0 &&
							cited
								.map((page) => sprintf(__("Page %d", "linker-tools"), page))
								.join(" · ") + " · "}
						{unavailable}
					</small>
				)
			)}
		</article>
	);
}
