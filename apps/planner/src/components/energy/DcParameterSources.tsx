import type { JsonObject } from "../../data/protocol.ts";
import { readObject } from "../../data/readProtocol.ts";
import { __, sprintf } from "../../i18n.ts";

/** Frozen Woo facts, including their original identifiers and citations. */
export function DcParameterSources({
	parameters,
	locale,
}: {
	parameters: JsonObject;
	locale: string;
}) {
	const facts = readObject(parameters.source_facts);
	const number = (value: number) =>
		new Intl.NumberFormat(locale, { maximumSignificantDigits: 12 }).format(
			value,
		);
	return (
		<details className="lp-comparison">
			<summary>{__("Product data used", "linker-tools")}</summary>
			<dl className="lp-field-summary">
				{Object.entries(facts)
					.filter(
						([, raw]) =>
							raw !== null &&
							typeof raw === "object" &&
							!Array.isArray(raw) &&
							Object.hasOwn(raw, "value"),
					)
					.map(([id, raw]) => {
						const fact = readObject(raw),
							source = fact.source ? readObject(fact.source) : null;
						const url =
							typeof source?.url === "string" &&
							/^https?:\/\//i.test(source.url)
								? source.url
								: null;
						return (
							<div key={id}>
								<dt>{id}</dt>
								<dd>
									{typeof fact.value === "number"
										? number(fact.value)
										: JSON.stringify(fact.value)}{" "}
									{typeof fact.unit === "string" ? fact.unit : ""}
									{url && (
										<p>
											<a href={url} target="_blank" rel="noreferrer">
												{__("Source document", "linker-tools")}
											</a>
											{" · "}
											{sprintf(
												__("Page %d", "linker-tools"),
												Number(source!.page),
											)}
										</p>
									)}
									{fact.qualifier !== null && fact.qualifier !== undefined && (
										<p>{JSON.stringify(fact.qualifier)}</p>
									)}
								</dd>
							</div>
						);
					})}
			</dl>
		</details>
	);
}
