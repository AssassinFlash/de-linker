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
		rollupOptions: {
			input: "src/main.tsx",
			output: { entryFileNames: "assets/planner.js" },
		},
		sourcemap: false,
	},
});
