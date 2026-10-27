import { Component } from "react";
import type { ReactNode } from "react";
import { Notice } from "../Notice.tsx";
import { __ } from "../../i18n.ts";

export class ChartBoundary extends Component<
	{ children: ReactNode },
	{ failed: boolean }
> {
	state = { failed: false };
	static getDerivedStateFromError() {
		return { failed: true };
	}
	render() {
		return this.state.failed ? (
			<Notice>
				{__(
					"The chart could not be displayed. The interval table and CSV remain available.",
					"linker-tools",
				)}
			</Notice>
		) : (
			this.props.children
		);
	}
}
