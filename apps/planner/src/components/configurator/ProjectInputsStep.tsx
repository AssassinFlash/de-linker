import { useEffect, useRef, type ReactNode } from "react";
import { __ } from "../../i18n.ts";

/** One editable project; old solar and demand links target sections, not steps. */
export function ProjectInputsStep({
	details,
	solar,
	energy,
	focusSection = null,
}: {
	details: ReactNode;
	solar?: ReactNode;
	energy?: ReactNode;
	focusSection?: "solar" | "energy" | null;
}) {
	const solarSection = useRef<HTMLElement>(null),
		energySection = useRef<HTMLElement>(null);
	const hasSolar = Boolean(solar),
		hasEnergy = Boolean(energy);
	useEffect(() => {
		const node =
			focusSection === "solar"
				? (solarSection.current ?? energySection.current)
				: focusSection === "energy"
					? energySection.current
					: null;
		if (
			node &&
			!node.closest("[hidden]") &&
			!node.querySelector("dialog[open]")
		) {
			const disclosure = node.closest("details");
			if (disclosure) disclosure.open = true;
			node.focus({ preventScroll: true });
			node.scrollIntoView({ block: "start" });
		}
	}, [focusSection, hasSolar, hasEnergy]);
	return (
		<>
			{details}
			{solar && (
				<details className="sc-card">
					<summary>
						{__("Solar installation and roof layout", "linker-tools")}
					</summary>
					<section
						id="sc-solar"
						ref={solarSection}
						tabIndex={-1}
						aria-label={__("Solar", "linker-tools")}
					>
						{solar}
					</section>
				</details>
			)}
			{energy && (
				<section
					id="sc-energy"
					ref={energySection}
					tabIndex={-1}
					aria-label={__("Energy use", "linker-tools")}
				>
					{energy}
				</section>
			)}
		</>
	);
}
