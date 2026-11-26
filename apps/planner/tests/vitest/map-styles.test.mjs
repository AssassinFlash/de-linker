// @vitest-environment jsdom
import { expect, test, vi } from "vitest";
import { loadMapModule } from "../../src/data/mapModule.ts";

vi.mock("../../src/components/design/MapViewport.tsx", () => ({
	default: () => null,
}));

test("map styles load only when the viewport opens and can retry after a failed response", async () => {
	const url = "/uploads/windpress/cache/linker/planner-maplibre.css?ver=12";
	const links = () => document.head.querySelectorAll('link[rel="stylesheet"]');
	expect(links()).toHaveLength(0);
	const first = loadMapModule(null, url);
	expect(links()).toHaveLength(1);
	expect(links()[0].href).toBe(new URL(url, document.baseURI).href);
	links()[0].dispatchEvent(new Event("error"));
	await expect(first).rejects.toThrow("map_stylesheet_unavailable");
	expect(links()).toHaveLength(0);
	const retry = loadMapModule(null, url);
	const concurrent = loadMapModule(null, url);
	expect(links()).toHaveLength(1);
	links()[0].dispatchEvent(new Event("load"));
	expect((await retry).default).toBe((await concurrent).default);
});
