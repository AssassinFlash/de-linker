import assert from "node:assert/strict";
import test from "node:test";
import { JSDOM } from "jsdom";
import { readConfiguration } from "../src/data/config.ts";

test("only a same-site reviewed scene asset can become an executable retry URL", () => {
	const dom = new JSDOM("<section data-linker-planner></section>", {
		url: "https://fixture.invalid/workspace/",
	});
	try {
		const element = dom.window.document.querySelector("section");
		const configure = (scene) => {
			element.dataset.plannerConfig = JSON.stringify({
				base_url: "https://fixture.invalid/api/",
				nonce_url: "https://fixture.invalid/nonce/",
				locale: "en_GB",
				countries: { FR: "France" },
				scene_module_url: scene,
			});
			return readConfiguration(
				element,
				"https://fixture.invalid/wp-content/plugins/linker-tools/build/planner/assets/planner.js?ver=expected",
			);
		};
		const path =
			"/wp-content/plugins/linker-tools/build/planner/assets/SceneViewport-hash_1.js";
		assert.equal(
			configure(path).sceneModuleUrl,
			"https://fixture.invalid" + path,
		);
		assert.equal(configure(null).sceneModuleUrl, null);
		for (const bad of [
			"https://foreign.invalid" + path,
			"javascript:alert(1)",
			path + "?arbitrary=1",
			path + "#fragment",
			"/uploads/SceneViewport-other.js",
			"/uploads/build/planner/assets/SceneViewport-other.js",
			3,
		])
			assert.throws(() => configure(bad), /invalid_planner_scene_module/);
	} finally {
		dom.window.close();
	}
});
