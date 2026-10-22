import type { ReactNode } from "react";

export function Notice({
	children,
	error = false,
}: {
	children: ReactNode;
	error?: boolean;
}) {
	return (
		<div
			className="lp-notice"
			data-error={error || undefined}
			role={error ? "alert" : "status"}
		>
			{children}
		</div>
	);
}
