import { useEffect, useRef } from "react";
import * as echarts from "echarts/core";
import { LineChart } from "echarts/charts";
import {
	GridComponent,
	TooltipComponent,
	LegendComponent,
	DataZoomComponent,
} from "echarts/components";
import { SVGRenderer } from "echarts/renderers";
import { TRACE_FIELDS } from "../../data/traceWindow.ts";
import type { TraceWindow } from "../../data/traceWindow.ts";

echarts.use([
	LineChart,
	GridComponent,
	TooltipComponent,
	LegendComponent,
	DataZoomComponent,
	SVGRenderer,
]);

export default function EnergyFlowChart({
	page,
	labels,
	locale,
}: {
	page: TraceWindow;
	labels: readonly string[];
	locale: string;
}) {
	const element = useRef<HTMLDivElement>(null);
	useEffect(() => {
		if (!element.current || !page.rows.length) return;
		const chart = echarts.init(element.current, undefined, { renderer: "svg" }),
			style = getComputedStyle(element.current),
			text = style.color,
			font = style.fontFamily,
			last = page.rows.at(-1)!;
		chart.setOption({
			animation: false,
			textStyle: { fontFamily: font, color: text },
			color: [
				"--proto-neutral-700",
				"--proto-sem-warn",
				"--proto-teal-400",
				"--proto-teal-700",
				"--proto-sem-danger",
				"--proto-neutral-500",
				"--proto-teal-900",
			].map((name) => style.getPropertyValue(name).trim() || text),
			grid: { left: 55, right: 55, top: 76, bottom: 64 },
			legend: {
				type: "scroll",
				top: 0,
				textStyle: { color: text, fontFamily: font },
			},
			tooltip: {
				trigger: "axis",
				valueFormatter: (value: unknown) =>
					typeof value === "number"
						? new Intl.NumberFormat(locale, {
								maximumFractionDigits: 3,
							}).format(value)
						: String(value),
			},
			xAxis: {
				type: "time",
				axisLabel: {
					formatter: (value: number) =>
						new Intl.DateTimeFormat(locale, {
							timeZone: "UTC",
							month: "2-digit",
							day: "2-digit",
							hour: "2-digit",
							minute: "2-digit",
						}).format(value),
				},
			},
			yAxis: [
				{ type: "value", name: "kW", min: 0 },
				{ type: "value", name: "kWh", min: 0 },
			],
			dataZoom: [
				{ type: "inside", filterMode: "none" },
				{ type: "slider", bottom: 8, filterMode: "none" },
			],
			series: TRACE_FIELDS.map((field, index) => ({
				name: labels[index],
				type: "line",
				yAxisIndex: field === "stored_kwh" ? 1 : 0,
				showSymbol: false,
				step: field === "stored_kwh" ? false : "end",
				connectNulls: false,
				data:
					field === "stored_kwh"
						? page.rows.map((row) => [Date.parse(row.end_utc), row[field]])
						: [
								...page.rows.map((row) => [
									Date.parse(row.start_utc),
									row[field],
								]),
								[Date.parse(last.end_utc), last[field]],
							],
			})),
		});
		const resize = new ResizeObserver(() => chart.resize());
		resize.observe(element.current);
		return () => {
			resize.disconnect();
			chart.dispose();
		};
	}, [page, labels, locale]);
	return <div className="lp-energy-chart" ref={element} aria-hidden="true" />;
}
