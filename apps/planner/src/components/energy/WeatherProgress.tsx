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
			return __("The weather request is waiting to start.", "linker-tools");
		case "fetching":
			return __(
				"Weather data is being downloaded from JRC PVGIS and checked.",
				"linker-tools",
			);
		case "captured":
			return __(
				'The original weather data has passed validation and is retained. A project source is available only when the preparation status above shows "Source ready".',
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
				<p role="status">
					{status.data.acquisitionState !== "captured" &&
					!runPending(status.data.taskState)
						? __(
								"Weather preparation has ended without a validated weather source.",
								"linker-tools",
							)
						: statusText(status.data.acquisitionState)}
				</p>
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
