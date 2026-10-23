import { useCallback, useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { PlannerClient } from "../data/PlannerClient.ts";
import type { Session } from "../data/protocol.ts";
import { ApiError } from "../data/protocol.ts";
import type {
	Measurement,
	ProfileAsset,
	ProfilePreview,
} from "../domain/profiles.ts";
import { readAsset, readPreview } from "../domain/profiles.ts";
import { __ } from "../i18n.ts";
import { ProfileError } from "./ProfileError.tsx";
import { ProfileReview } from "./ProfileReview.tsx";
import { revealActionResult } from "./revealActionResult.ts";

export function OwnedProfile({
	projectId,
	assetId,
	session,
	client,
	locale,
	expectedRole,
	onSelect,
	recheck,
}: {
	projectId: string;
	assetId: string;
	session: Session;
	client: PlannerClient;
	locale: string;
	expectedRole?: Measurement;
	onSelect?: (asset: ProfileAsset, preview: ProfilePreview) => void;
	recheck: () => void;
}) {
	const [offset, setOffset] = useState(0);
	const recoveringSession = useRef(false);
	const reviewHeading = useRef<HTMLHeadingElement>(null);
	const revealedAsset = useRef<string | null>(null);
	const interactive = onSelect !== undefined;
	const admitted = client.isCurrentScope(session.query_scope);
	const canReveal = useCallback(
		() => client.isCurrentScope(session.query_scope),
		[client, session.query_scope],
	);
	const page = useQuery({
		queryKey: [
			session.query_scope,
			"profile",
			projectId,
			assetId,
			expectedRole ?? "unassigned",
			offset,
		],
		queryFn: async ({ signal }) => {
			try {
				const asset = readAsset(
					await client.query(
						"assets/read",
						{ schema_version: 1, project_id: projectId, asset_id: assetId },
						session.query_scope,
						signal,
					),
					projectId,
				);
				const preview = readPreview(
					await client.query(
						"profiles/preview",
						{
							schema_version: 1,
							project_id: projectId,
							asset_id: assetId,
							offset,
							page_size: Math.min(20, session.runtime.limits.max_page_size),
						},
						session.query_scope,
						signal,
					),
					asset,
				);
				if (expectedRole && preview.measurement !== expectedRole)
					throw new ApiError(502, "profile_role_mismatch");
				recoveringSession.current = false;
				return { asset, preview };
			} catch (error) {
				if (
					error instanceof ApiError &&
					([401, 403].includes(error.status) ||
						error.code === "session_changed")
				)
					if (!recoveringSession.current) {
						recoveringSession.current = true;
						recheck();
					}
				throw error;
			}
		},
		retry: false,
		enabled: admitted,
	});
	useEffect(() => {
		if (
			!interactive ||
			!admitted ||
			!page.data ||
			!reviewHeading.current ||
			revealedAsset.current === assetId
		)
			return;
		if (revealActionResult(reviewHeading.current, canReveal))
			revealedAsset.current = assetId;
	}, [interactive, admitted, page.data, assetId, canReveal]);
	if (page.error)
		return (
			<>
				<ProfileError
					error={page.error}
					focus={interactive && admitted}
					canReveal={canReveal}
				/>
				<button
					className="lp-text-button"
					type="button"
					onClick={() => {
						if (
							page.error instanceof ApiError &&
							([401, 403].includes(page.error.status) ||
								page.error.code === "session_changed")
						) {
							recoveringSession.current = false;
							recheck();
						} else void page.refetch();
					}}
				>
					{page.error instanceof ApiError &&
					([401, 403].includes(page.error.status) ||
						page.error.code === "session_changed")
						? __("Check session", "linker-tools")
						: __("Retry data preview", "linker-tools")}
				</button>
			</>
		);
	if (!page.data)
		return (
			<p role="status">{__("Reading the saved source…", "linker-tools")}</p>
		);
	return (
		<>
			<ProfileReview
				asset={page.data.asset}
				preview={page.data.preview}
				locale={locale}
				busy={page.isFetching}
				headingRef={interactive ? reviewHeading : null}
				loadMore={() => setOffset(page.data.preview.next_offset ?? 0)}
			/>
			{offset > 0 && (
				<button
					className="lp-text-button"
					type="button"
					onClick={() => setOffset(0)}
				>
					{__("First intervals", "linker-tools")}
				</button>
			)}
			{onSelect && (
				<button
					className="lp-button"
					type="button"
					onClick={() => onSelect(page.data.asset, page.data.preview)}
				>
					{__("Use this profile in the open draft", "linker-tools")}
				</button>
			)}
		</>
	);
}
