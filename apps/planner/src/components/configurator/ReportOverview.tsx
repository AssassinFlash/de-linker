import type { PlanningReport } from "../../data/planningReport.ts";

export function ReportOverview({ report }: { report: PlanningReport }) {
	const cards = report.summary_cards,
		chart = report.monthly_chart,
		de = report.locale === "de";
	const number = new Intl.NumberFormat(de ? "de-DE" : "en-GB", {
		maximumFractionDigits: 1,
	});
	return (
		<>
			{!!cards?.length && (
				<dl className="sc-field-summary">
					{cards.map((card) => (
						<div key={card.label}>
							<dt>{card.label}</dt>
							<dd>
								{card.value}
								{card.note && (
									<small className="block sc-muted">{card.note}</small>
								)}
							</dd>
						</div>
					))}
				</dl>
			)}
			{chart && (
				<details className="sc-disclosure">
					<summary>{chart.title}</summary>
					<p>{chart.source_note}</p>
					<div className="sc-table-scroll">
						<table>
							<thead>
								<tr>
									<th>{de ? "Monat" : "Month"}</th>
									<th>
										{de ? "PV-Erzeugung" : "PV generation"} ({chart.unit})
									</th>
									{chart.load_kwh && (
										<th>
											{de ? "Stromverbrauch" : "Electricity use"} ({chart.unit})
										</th>
									)}
								</tr>
							</thead>
							<tbody>
								{chart.months.map((month, i) => (
									<tr key={month}>
										<th scope="row">{month}</th>
										<td>{number.format(chart.pv_kwh[i]!)}</td>
										{chart.load_kwh && (
											<td>{number.format(chart.load_kwh[i]!)}</td>
										)}
									</tr>
								))}
							</tbody>
						</table>
					</div>
				</details>
			)}
		</>
	);
}
export function appendixTitle(locale: "en" | "de") {
	return locale === "de"
		? "Technischer & rechtlicher Anhang"
		: "Technical & Compliance Appendix";
}
