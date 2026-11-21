import type { ReactNode, Ref } from "react";

export function Notice({
	children,
	error = false,
	focusTarget,
}: {
	children: ReactNode;
	error?: boolean;
	focusTarget?: Ref<HTMLDivElement> | undefined;
}) {
	return (
		<div
			ref={focusTarget}
			tabIndex={focusTarget ? -1 : undefined}
			className="sc-notice"
			data-error={error || undefined}
			role={error ? "alert" : "status"}
		>
			{children}
		</div>
	);
}
