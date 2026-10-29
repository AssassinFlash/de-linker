import { readFileSync } from "node:fs";
import { arch, platform } from "node:os";

type PreparationFixture = typeof import("./preparation-flow-darwin-arm64.json");

const machine = arch() === "x64" ? "x86_64" : arch();
const fixture: PreparationFixture = JSON.parse(
	readFileSync(
		new URL(
			`./preparation-flow-${platform()}-${machine}.json`,
			import.meta.url,
		),
		"utf8",
	),
);

export default fixture;
