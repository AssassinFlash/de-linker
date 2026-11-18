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
			node.focus({ preventScroll: true });
			node.scrollIntoView({ block: "start" });
		}
	}, [focusSection, hasSolar, hasEnergy]);
	return (
		<>
			{details}
			{solar && (
				<section
					id="sc-solar"
					ref={solarSection}
					tabIndex={-1}
					aria-label={__("Solar", "linker-tools")}
				>
					{solar}
				</section>
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
