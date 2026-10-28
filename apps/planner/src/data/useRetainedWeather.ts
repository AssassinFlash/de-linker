/** Reuse owned source metadata without fetching provider originals in the browser. */
import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import type { PlannerClient } from "./PlannerClient.ts";
import type { Session } from "./protocol.ts";
import { ApiError } from "./protocol.ts";
import { readObject } from "./readProtocol.ts";
import { beamHash, readBeamWeatherAssets } from "./directBeamWeather.ts";

export function useRetainedWeather(
	client: PlannerClient,
	session: Session,
	projectId: string,
	assetId: string | null,
	active: boolean,
) {
	const scope = session.query_scope,
		pageSize = session.runtime.limits.max_page_size,
		owned = client.isCurrentScope(scope);
	const sources = useInfiniteQuery({
		queryKey: [scope, "retained-weather-assets", projectId],
		initialPageParam: 0,
		enabled: active && owned,
		retry: false,
		queryFn: async ({ pageParam, signal }) =>
			readBeamWeatherAssets(
				await client.query(
					"weather/assets",
					{
						schema_version: 1,
						project_id: projectId,
						offset: pageParam,
						page_size: pageSize,
					},
					scope,
					signal,
				),
				projectId,
				pageParam,
				pageSize,
			),
		getNextPageParam: (page) => page.next ?? undefined,
	});
	const assets = sources.data?.pages.flatMap((page) => page.assets) ?? [],
		selected = assets.find((asset) => asset.asset_id === assetId);
	const binding = useQuery({
		queryKey: [
			scope,
			"retained-weather-binding",
			projectId,
			assetId,
			selected?.metadata_sha256,
		],
		enabled: active && owned && assetId !== null,
		retry: false,
		queryFn: async ({ signal }) => {
			const asset = readObject(
					await client.query(
						"assets/read",
						{ schema_version: 1, project_id: projectId, asset_id: assetId },
						scope,
						signal,
					),
				),
				metadata = readObject(asset.metadata),
				weather = readObject(metadata.weather);
			if (
				asset.id !== assetId ||
				asset.project_id !== projectId ||
				asset.purpose !== "pvgis_tmy_weather_v1" ||
				asset.media_type !== "application/json" ||
				!beamHash(asset.content_sha256) ||
				!beamHash(asset.metadata_sha256) ||
				metadata.schema !== 1 ||
				metadata.retention !== "permanent" ||
				(selected &&
					(asset.content_sha256 !== selected.content_sha256 ||
						asset.metadata_sha256 !== selected.metadata_sha256)) ||
				typeof weather.latitude_deg !== "number" ||
				!Number.isFinite(weather.latitude_deg) ||
				typeof weather.longitude_deg !== "number" ||
				!Number.isFinite(weather.longitude_deg) ||
				!Number.isSafeInteger(weather.interval_count) ||
				Number(weather.interval_count) <= 0
			)
				throw new ApiError(502, "preparation_source_mismatch");
			return { asset, metadata, weather };
		},
	});
	return { sources, assets, selected, binding };
}
