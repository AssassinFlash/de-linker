import { createHash } from "node:crypto";
import {
	readFileSync,
	writeFileSync,
	readdirSync,
	statSync,
	existsSync,
} from "node:fs";
import { resolve, relative } from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const root = fileURLToPath(new URL("..", import.meta.url));
const output = resolve(root, "../../plugins/linker-tools/build/planner");
const manifestName = "source-manifest.json";
const inputContractFile = "src/contracts/project-input-contracts.json";
function files(directory) {
	return readdirSync(directory)
		.sort()
		.flatMap((name) => {
			const path = resolve(directory, name);
			return statSync(path).isDirectory() ? files(path) : [path];
		});
}
const sources = [
	...files(resolve(root, "src")).filter(
		(path) => !/\.test\.[jt]sx?$/.test(path),
	),
	...files(resolve(root, "bin")),
	...[
		".npmrc",
		"package.json",
		"package-lock.json",
		"tsconfig.json",
		"vite.config.ts",
	].map((name) => resolve(root, name)),
];
function scanClasses() {
	const classes = new Set();
	for (const file of sources.filter((file) => file.endsWith(".tsx"))) {
		const source = ts.createSourceFile(
			file,
			readFileSync(file, "utf8"),
			ts.ScriptTarget.Latest,
			true,
			ts.ScriptKind.TSX,
		);
		function visit(node) {
			if (
				ts.isJsxAttribute(node) &&
				node.name.getText(source) === "className" &&
				node.initializer
			) {
				function literals(value) {
					if (ts.isStringLiteralLike(value))
						for (const token of value.text.split(/\s+/).filter(Boolean))
							classes.add(token);
					ts.forEachChild(value, literals);
				}
				literals(node.initializer);
			}
			ts.forEachChild(node, visit);
		}
		visit(source);
	}
	return [...classes].sort().join("\n") + "\n";
}
function hash(paths, directory) {
	return Object.fromEntries(
		paths
			.sort()
			.map((path) => [
				relative(directory, path).replaceAll("\\", "/"),
				createHash("sha256").update(readFileSync(path)).digest("hex"),
			]),
	);
}
function snapshot() {
	const inputContracts = JSON.parse(
		readFileSync(resolve(root, inputContractFile), "utf8"),
	);
	const pluginContracts = JSON.parse(
		readFileSync(resolve(output, "../../project-input-contracts.json"), "utf8"),
	);
	if (JSON.stringify(inputContracts) !== JSON.stringify(pluginContracts))
		throw new Error("Planner and Tools input contracts differ");
	const modules = JSON.parse(
		readFileSync(resolve(output, "vite-manifest.json"), "utf8"),
	);
	// A versioned WP entry must stay a leaf for imports from generated chunks.
	// Otherwise the browser executes it again under its unversioned identity.
	for (const [key, module] of Object.entries(modules)) {
		if (
			key !== "src/main.tsx" &&
			[...(module.imports ?? []), ...(module.dynamicImports ?? [])].includes(
				"src/main.tsx",
			)
		)
			throw new Error("Planner chunks must not import the versioned entry");
	}
	const built = files(output).filter(
		(path) => relative(output, path) !== manifestName,
	);
	if (built.some((path) => path.endsWith(".css")))
		throw new Error("Planner styles must use the site WindPress volume");
	return {
		sources: hash(sources, root),
		build: hash(built, output),
		project_input_contracts: inputContracts.project_input_contracts,
	};
}
const mode = process.argv[2];
if (mode === "write") {
	writeFileSync(resolve(output, "windpress.scan.txt"), scanClasses());
	writeFileSync(
		resolve(output, manifestName),
		JSON.stringify(snapshot(), null, 2) + "\n",
	);
} else if (mode === "check") {
	const path = resolve(output, manifestName);
	if (
		!existsSync(path) ||
		JSON.stringify(JSON.parse(readFileSync(path, "utf8"))) !==
			JSON.stringify(snapshot()) ||
		readFileSync(resolve(output, "windpress.scan.txt"), "utf8") !==
			scanClasses()
	)
		throw new Error(
			"Planner build does not match its source; rebuild apps/planner",
		);
	process.stdout.write("Planner build matches its sources.\n");
} else throw new Error("Usage: node bin/build-manifest.mjs write|check");
