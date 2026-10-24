import { useQuery } from "@tanstack/react-query";
import type { Session } from "../../data/protocol.ts";
import { ApiError } from "../../data/protocol.ts";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import {
	readWeatherStatus,
	weatherStatusPending,
} from "../../data/weatherStatus.ts";
import type { AcquisitionState } from "../../data/weatherStatus.ts";
import { runPending } from "../../data/planningProtocol.ts";
import { __ } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";

function statusText(state: AcquisitionState): string {
	switch (state) {
		case "not_started":
		case "ready_to_start":
			return __("The weather request is waiting to start.", "linker-tools");
		case "READY":
			return __("The weather request is waiting to start.", "linker-tools");
		case "RUNNING":
			return __(
				"The weather provider is processing the saved request.",
				"linker-tools",
			);
		case "TIMING-OUT":
			return __(
				"The provider is stopping the run after its time limit was reached. The stop is not yet confirmed.",
				"linker-tools",
			);
		case "ABORTING":
			return __(
				"The provider accepted the stop request. The stop is not yet confirmed.",
				"linker-tools",
			);
		case "SUCCEEDED":
			return __(
				"The provider has finished the request. A project source is ready only after the original data is validated and preparation succeeds.",
				"linker-tools",
			);
		case "captured":
			return __(
				'The original weather data has passed validation and is retained. A project source is available only when the preparation status above shows "Source ready".',
				"linker-tools",
			);
		case "ABORTED":
			return __(
				"The provider confirmed that the run was stopped.",
				"linker-tools",
			);
		case "FAILED":
		case "TIMED-OUT":
			return __(
				"The provider run ended without a usable weather source.",
				"linker-tools",
			);
		case "start_outcome_unknown":
			return __(
				"The provider may have started this request. Linker must verify the original request. The system will not start it again automatically.",
				"linker-tools",
			);
	}
}
export function WeatherProgress({
	runId,
	session,
	client,
	recheck,
	active,
}: {
	runId: string;
	session: Session;
	client: PlannerClient;
	recheck: () => void;
	active: boolean;
}) {
	const status = useQuery({
		queryKey: [session.query_scope, "weather-status", runId],
		enabled: active && client.isCurrentScope(session.query_scope),
		retry: false,
		queryFn: async ({ signal }) => {
			try {
				return readWeatherStatus(
					await client.query(
						"runs/weather/status",
						{ schema_version: 1, run_id: runId },
						session.query_scope,
						signal,
					),
					runId,
				);
			} catch (error) {
				if (
					error instanceof ApiError &&
					([401, 403].includes(error.status) ||
						error.code === "session_changed")
				)
					recheck();
				throw error;
			}
		},
		// Visible local-journal polling only; provider work remains in the queue.
		refetchInterval: (query) =>
			query.state.data && weatherStatusPending(query.state.data) ? 1000 : false,
	});
	return (
		<section
			className="lp-comparison"
			aria-label={__("Weather request status", "linker-tools")}
		>
			<h4>{__("Weather request status", "linker-tools")}</h4>
			{status.isPending && (
				<p role="status">
					{__("Loading weather request status…", "linker-tools")}
				</p>
			)}
			{status.error && (
				<Notice error>
					{__(
						"Weather status could not be refreshed. Any status shown comes from the last confirmed response.",
						"linker-tools",
					)}
				</Notice>
			)}
			{status.data && (
				<>
					<p role="status">
						{["not_started", "ready_to_start"].includes(
							status.data.acquisitionState,
						) && !runPending(status.data.taskState)
							? __(
									"Weather preparation has ended. No provider start has been recorded.",
									"linker-tools",
								)
							: statusText(status.data.acquisitionState)}
					</p>
					{status.data.cleanup !== null &&
						["queued", "running", "retry_wait"].includes(
							status.data.cleanup,
						) && (
							<p>
								{__(
									"Confirmation that the provider run has ended is still pending.",
									"linker-tools",
								)}
							</p>
						)}
					{status.data.cleanup === "failed" && (
						<Notice>
							{__(
								"The stop check failed. Any provider status shown is the last recorded observation.",
								"linker-tools",
							)}
						</Notice>
					)}
					{status.data.reconciliation !== null &&
						["queued", "running", "retry_wait"].includes(
							status.data.reconciliation,
						) && (
							<p>
								{__(
									"Verification of the recorded weather request is pending or in progress.",
									"linker-tools",
								)}
							</p>
						)}
					{status.data.acquisitionState === "start_outcome_unknown" && (
						<a href="mailto:sales@de-linker.com">
							{__("Contact Linker", "linker-tools")}
						</a>
					)}
				</>
			)}
			<button
				type="button"
				className="lp-text-button"
				disabled={
					status.isFetching ||
					!active ||
					!client.isCurrentScope(session.query_scope)
				}
				onClick={() => void status.refetch()}
			>
				{__("Refresh weather status", "linker-tools")}
			</button>
		</section>
	);
}
