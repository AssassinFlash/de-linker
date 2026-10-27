import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
	plugins: [react()],
	// Every entry and lazy chunk resolves relative to the deployed plugin asset.
	base: "./",
	build: {
		target: "es2022",
		outDir: "../../plugins/linker-tools/build/planner",
		emptyOutDir: true,
		manifest: "vite-manifest.json",
		rolldownOptions: {
			input: "src/main.tsx",
			output: {
				entryFileNames: "assets/planner.js",
				// WP versions the entry URL. A lazy chunk must never import that
				// entry without its query and execute a second React/root identity.
				// Shared modules have one content-addressed URL for every consumer.
				codeSplitting: {
					groups: [
						{
							name: "planner-core",
							tags: ["$initial"],
							test: (id) => !id.endsWith("/src/main.tsx"),
						},
					],
				},
			},
		},
		sourcemap: false,
	},
});
