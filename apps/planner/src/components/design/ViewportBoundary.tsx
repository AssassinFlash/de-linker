import { Component } from "react";
import type { ReactNode } from "react";
import { Notice } from "../Notice.tsx";

/** Outside the downloadable view: its failure must leave the editor usable. */
export class ViewportBoundary extends Component<
	{
		children: ReactNode;
		retry: () => void;
		failure: string;
		retryLabel: string;
	},
	{ failed: boolean }
> {
	state = { failed: false };
	static getDerivedStateFromError() {
		return { failed: true };
	}
	render() {
		return this.state.failed ? (
			<Notice error>
				<p>{this.props.failure}</p>
				<button
					type="button"
					className="lp-button lp-button-secondary"
					onClick={this.props.retry}
				>
					{this.props.retryLabel}
				</button>
			</Notice>
		) : (
			this.props.children
		);
	}
}
