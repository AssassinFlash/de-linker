import { ApiError } from "../data/protocol.ts";
import { __, sprintf } from "../i18n.ts";
import { Notice } from "./Notice.tsx";
import { issueLabel } from "./ProfileLabels.ts";

export function ProfileError({ error }: { error: unknown }) {
	if (!error) return null;
	const issue = error instanceof ApiError ? error.profileIssue : null;
	return (
		<Notice error>
			<p>
				{issue
					? issueLabel(issue.issue)
					: error instanceof ApiError && error.status === 413
						? __(
								"The file or request exceeds this service's size limit.",
								"linker-tools",
							)
						: __(
								"The data request could not be confirmed. Please retry.",
								"linker-tools",
							)}
			</p>
			{issue?.line !== null && issue?.line !== undefined && (
				<>
					<p>
						{sprintf(
							__("The CSV record starts on file line %d.", "linker-tools"),
							issue.line,
						)}
					</p>
					<p>
						{__(
							"File lines include blank lines and line breaks inside quoted cells. They are not spreadsheet row numbers.",
							"linker-tools",
						)}
					</p>
				</>
			)}
			{issue?.field && (
				<p>
					{issue.field === "timestamp"
						? __("Check the timestamp column.", "linker-tools")
						: issue.field === "end_timestamp"
							? __("Check the interval end column.", "linker-tools")
							: issue.field === "value"
								? __("Check the value column.", "linker-tools")
								: __("Check the header record.", "linker-tools")}
				</p>
			)}
		</Notice>
	);
}
