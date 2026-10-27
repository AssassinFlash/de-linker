import { useQuery } from "@tanstack/react-query";
import type { ComponentProps } from "react";
import { ApiError } from "../data/protocol.ts";
import {
	readSavedSolutionSource,
	savedSolutionHints,
	savedSolutionInputs,
} from "../domain/savedSolution.ts";
import { __ } from "../i18n.ts";
import { NewProject } from "./NewProject.tsx";
import { Notice } from "./Notice.tsx";
import { SavedSolutionReference } from "./SavedSolutionReference.tsx";

export function SavedSolutionStart({
	solutionId,
	dismiss,
	...props
}: ComponentProps<typeof NewProject> & {
	solutionId: number;
	dismiss: () => void;
}) {
	const source = useQuery({
		queryKey: [props.session.query_scope, "saved-solution-source", solutionId],
		// Pin the opening snapshot while a creation intent may be pending.
		// Drop private source data when this view closes; reopening reads afresh.
		staleTime: Infinity,
		gcTime: 0,
		refetchOnWindowFocus: false,
		refetchOnReconnect: false,
		retry: false,
		queryFn: async ({ signal }) => {
			if (solutionId <= 0)
				throw new ApiError(404, "saved_solution_unavailable");
			return readSavedSolutionSource(
				await props.client.query(
					"sources/saved-solution",
					{
						schema_version: 1,
						solution_id: solutionId,
					},
					props.session.query_scope,
					signal,
				),
				solutionId,
			);
		},
	});
	if (!source.data)
		return (
			<Notice error={source.isError}>
				<p>
					{source.isError
						? __(
								"The saved inputs could not be loaded in this session.",
								"linker-tools",
							)
						: __("Opening your workspace…", "linker-tools")}
				</p>
				{source.isError && (
					<button
						className="lp-text-button"
						onClick={() => {
							if (
								source.error instanceof ApiError &&
								[401, 403].includes(source.error.status)
							)
								props.recheck();
							else void source.refetch();
						}}
					>
						{__("Try again", "linker-tools")}
					</button>
				)}
				<button className="lp-text-button" onClick={dismiss}>
					{__("Continue without these inputs", "linker-tools")}
				</button>
			</Notice>
		);
	const hints = savedSolutionHints(source.data);
	const inputs = savedSolutionInputs(
		source.data,
		hints,
		__("Annual consumption as recorded in the saved solution.", "linker-tools"),
		__(
			"Backup supply requested; accessories may be considered.",
			"linker-tools",
		),
	);
	return (
		<div>
			<h2>{__("Start a new project from a saved solution", "linker-tools")}</h2>
			<SavedSolutionReference value={inputs.saved_solution_reference} />
			<NewProject
				{...props}
				entryHints={hints}
				initialProject={{
					title:
						source.data.title.trim().slice(0, 256) ||
						__("New project", "linker-tools"),
					inputs,
				}}
				cancelled={dismiss}
			/>
		</div>
	);
}
