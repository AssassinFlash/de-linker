import { useMemo } from "react";
import type { Brief } from "../domain/brief.ts";
import type { GeometryDocument } from "../domain/geometry.ts";
import { moduleSummary, panelPoses } from "../domain/panelPoses.ts";
import { formatDecimal } from "../domain/decimal.ts";
import type { Configuration } from "../data/config.ts";
import { PlanViewport } from "./design/PlanViewport.tsx";
import { Icon } from "./Icon.tsx";
import { __ } from "../i18n.ts";

/** Summary values come from the current input document. It does not invent a
 * yield, a completion percentage or an engineering-release state. */
export function ProjectOverview({
	brief,
	geometry,
	config,
	choose,
}: {
	brief: Brief;
	geometry: GeometryDocument;
	config: Configuration;
	choose: (workspace: "site" | "energy" | "design" | "calculations") => void;
}) {
	const poses = useMemo(() => panelPoses(geometry), [geometry]),
		summary = useMemo(() => moduleSummary(geometry), [geometry]),
		roof = geometry.roofs[0],
		number = (value: number) => formatDecimal(value, config.locale);
	return (
		<section
			className="lp-overview lp-focus-target"
			aria-labelledby="lp-overview-heading"
			id="lp-overview"
			tabIndex={-1}
		>
			<div className="lp-overview-intro">
				<span className="lp-eyebrow">
					{__("Project overview", "linker-tools")}
				</span>
				<h2 id="lp-overview-heading">
					{__("Your project at a glance", "linker-tools")}
				</h2>
				<p>
					{__(
						"Site information, roof layouts and energy inputs share this project. Each workspace can be completed as the design develops.",
						"linker-tools",
					)}
				</p>
			</div>
			<dl className="lp-overview-metrics">
				<div>
					<dt>{__("Country", "linker-tools")}</dt>
					<dd>
						{brief.site.country_code
							? (config.countries[brief.site.country_code] ??
								brief.site.country_code)
							: "—"}
					</dd>
					<small>{__("Project location", "linker-tools")}</small>
				</div>
				<div>
					<dt>{__("Annual consumption", "linker-tools")}</dt>
					<dd>
						{brief.annual_load.kwh === null
							? "—"
							: number(brief.annual_load.kwh)}
						{brief.annual_load.kwh !== null && <small> kWh</small>}
					</dd>
					<small>
						{brief.annual_load.basis === "bill_total"
							? __("Electricity bills", "linker-tools")
							: brief.annual_load.basis === "user_estimate"
								? __("Project estimate", "linker-tools")
								: __("Basis not specified", "linker-tools")}
					</small>
				</div>
				<div>
					<dt>{__("Included modules", "linker-tools")}</dt>
					<dd>{geometry.arrays.length ? number(summary.count) : "—"}</dd>
					<small>{__("Across the current roof layouts", "linker-tools")}</small>
				</div>
				<div>
					<dt>{__("Declared DC nameplate power", "linker-tools")}</dt>
					<dd>
						{geometry.arrays.length ? (
							<>
								{number(summary.stc_kwp)}
								<small> kWp</small>
							</>
						) : (
							"—"
						)}
					</dd>
					<small>
						{__("Module count and declared specifications", "linker-tools")}
					</small>
				</div>
			</dl>
			<div className="lp-overview-work">
				<div className="lp-overview-preview">
					{roof ? (
						<>
							<div className="lp-overview-preview-title">
								<Icon name="layers" />
								<span>{roof.name}</span>
								<span>{__("Current layout", "linker-tools")}</span>
							</div>
							<PlanViewport
								document={geometry}
								roof={roof}
								poses={poses}
								selected={null}
								select={() => {}}
								commit={() => false}
								disabled
								previewOnly
							/>
							<button
								className="lp-text-button"
								type="button"
								onClick={() => choose("design")}
							>
								{__("Open roof workspace", "linker-tools")}
								<Icon name="arrow" />
							</button>
						</>
					) : (
						<div className="lp-overview-empty">
							<Icon name="layers" />
							<h3>
								{__("A place for the roof and its layout", "linker-tools")}
							</h3>
							<p>
								{__(
									"Roof design is optional. A measured roof can be added here while the project information and energy inputs remain available in their workspaces.",
									"linker-tools",
								)}
							</p>
							<button
								className="lp-button"
								type="button"
								onClick={() => choose("design")}
							>
								{__("Open roof workspace", "linker-tools")}
								<Icon name="arrow" />
							</button>
						</div>
					)}
				</div>
				<aside
					className="lp-overview-next"
					aria-label={__("Project workspaces", "linker-tools")}
				>
					<h3>{__("Continue your project", "linker-tools")}</h3>
					<button type="button" onClick={() => choose("site")}>
						<Icon name="location" />
						<span>
							<strong>{__("Site and project", "linker-tools")}</strong>
							<small>
								{brief.site.location_label ||
									__(
										"Location, system scope and site conditions",
										"linker-tools",
									)}
							</small>
						</span>
						<Icon name="arrow" />
					</button>
					<button type="button" onClick={() => choose("design")}>
						<Icon name="layers" />
						<span>
							<strong>{__("Roof design", "linker-tools")}</strong>
							<small>
								{__("Roof faces, obstacles and module layout", "linker-tools")}
							</small>
						</span>
						<Icon name="arrow" />
					</button>
					<button type="button" onClick={() => choose("energy")}>
						<Icon name="energy" />
						<span>
							<strong>{__("Energy inputs", "linker-tools")}</strong>
							<small>
								{__("Annual consumption and interval data", "linker-tools")}
							</small>
						</span>
						<Icon name="arrow" />
					</button>
					<button type="button" onClick={() => choose("calculations")}>
						<Icon name="energy" />
						<span>
							<strong>{__("Energy calculation", "linker-tools")}</strong>
							<small>
								{__("Scenario settings and saved calculations", "linker-tools")}
							</small>
						</span>
						<Icon name="arrow" />
					</button>
					<p className="lp-overview-basis">
						{__(
							"The overview describes the current inputs. Energy yield, equipment suitability and engineering release require their respective calculations and evidence.",
							"linker-tools",
						)}
					</p>
				</aside>
			</div>
		</section>
	);
}
