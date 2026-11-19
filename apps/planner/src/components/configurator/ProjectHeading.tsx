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
				<h1>{title || __("Your project", "linker-tools")}</h1>
				{location && <p>{location}</p>}
			</div>
			{actions}
		</header>
	);
}

export function InquiryStages({
	reviewing = false,
	guided = false,
}: {
	reviewing?: boolean;
	guided?: boolean;
}) {
	return (
		<nav
			className="sc-nav"
			aria-label={__("Project navigation", "linker-tools")}
		>
			<ol className="sc-inquiry-stages">
				<li aria-current={!guided && !reviewing ? "step" : undefined}>
					{guided
						? __("Compare systems", "linker-tools")
						: __("Compare options", "linker-tools")}
				</li>
				{guided && (
					<li aria-current={reviewing ? undefined : "step"}>
						{__("Choose an option", "linker-tools")}
					</li>
				)}
				<li aria-current={reviewing ? "step" : undefined}>
					{__("Review and send", "linker-tools")}
				</li>
			</ol>
		</nav>
	);
}
