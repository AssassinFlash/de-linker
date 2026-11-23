import { useEffect, useRef, type ReactNode } from "react";
import { __ } from "../../i18n.ts";

export function ProjectHeading({
	title,
	location,
	anchor,
	actions,
}: {
	title?: string;
	location?: string;
	anchor?: string;
	actions?: ReactNode;
}) {
	const heading = useRef<HTMLElement>(null);
	useEffect(() => {
		if (anchor) heading.current?.scrollIntoView?.({ block: "start" });
	}, [anchor]);
	return (
		<header ref={heading} id={anchor} className="sc-project-heading">
			<div>
				<p className="sc-eyebrow">
					{title
						? __("Your project", "linker-tools")
						: __("Solution Configurator", "linker-tools")}
				</p>
				<h1>
					{title ||
						__("Configure a matched PV & storage system", "linker-tools")}
				</h1>
				{location && <p>{location}</p>}
			</div>
			{actions}
		</header>
	);
}

export function InquiryStages({
	current = 1,
	open,
}: {
	current?: 1 | 2 | 3;
	open?: (step: 1 | 2 | 3) => void;
}) {
	const stages = [
		__("Project & direction", "linker-tools"),
		__("Fine-tune (optional)", "linker-tools"),
		__("Review & send", "linker-tools"),
	];
	return (
		<nav
			className="sc-nav sc-project-navigation"
			aria-label={__("Project navigation", "linker-tools")}
		>
			<ol className="sc-inquiry-stages">
				{stages.map((title, index) => {
					const step = (index + 1) as 1 | 2 | 3;
					const content = (
						<>
							<span className="sc-step-number" aria-hidden="true">
								{step}
							</span>
							{title}
						</>
					);
					return (
						<li key={step} aria-current={step === current ? "step" : undefined}>
							{open ? (
								<button type="button" onClick={() => open(step)}>
									{content}
								</button>
							) : (
								<span className="sc-step-label">{content}</span>
							)}
						</li>
					);
				})}
			</ol>
		</nav>
	);
}
