import { __ } from "../i18n.ts";
import { CreditText } from "./CreditText.tsx";

/** Application-level identity shared by the project list and every workspace. */
export function ToolIdentity() {
	return (
		<footer className="lp-tool-identity">
			<div className="lp-tool-product">
				<strong>{__("Solution Configurator", "linker-tools")}</strong>
				<span>{__("by Linker", "linker-tools")}</span>
				<p>
					{__(
						"Linker brings your inputs into an editable project for solar and storage planning.",
						"linker-tools",
					)}
				</p>
			</div>
			<details className="lp-tool-about">
				<summary>{__("About this tool", "linker-tools")}</summary>
				<div>
					<p>
						{__(
							"Linker provides the project workflow and editing tools. Your inputs and design stay together in the same project, with controls for saving changes and restoring available drafts.",
							"linker-tools",
						)}
					</p>
					<p className="lp-tool-boundary">
						{__(
							"All design views use the same project geometry. Source records retain the declared accuracy and permissions; a displayed model provides no engineering approval.",
							"linker-tools",
						)}
					</p>
					<h2>{__("Software and data credits", "linker-tools")}</h2>
					<p>
						<CreditText>
							{__(
								"Interface and project data: React, TanStack Query and Ajv. 3D views: Three.js and React Three Fiber. Map display: MapLibre GL JS.",
								"linker-tools",
							)}
						</CreditText>
					</p>
					<p>
						<CreditText>
							{__(
								"Street map: OpenFreeMap. © OpenMapTiles; © OpenStreetMap contributors.",
								"linker-tools",
							)}
						</CreditText>
					</p>
					<a
						href="https://openfreemap.org/privacy/"
						target="_blank"
						rel="noopener noreferrer"
					>
						{__("OpenFreeMap privacy policy", "linker-tools")}
					</a>
				</div>
			</details>
		</footer>
	);
}
