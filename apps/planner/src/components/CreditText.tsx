const links: Readonly<Record<string, string>> = {
	React: "https://react.dev/",
	"TanStack Query": "https://tanstack.com/query",
	Ajv: "https://ajv.js.org",
	"Three.js": "https://threejs.org/",
	"React Three Fiber": "https://r3f.docs.pmnd.rs/getting-started/introduction",
	"MapLibre GL JS": "https://maplibre.org/maplibre-gl-js/docs/",
	OpenFreeMap: "https://openfreemap.org/",
	"© OpenMapTiles": "https://www.openmaptiles.org/",
	"© OpenStreetMap contributors": "https://www.openstreetmap.org/copyright",
	"© OpenStreetMap-Mitwirkende": "https://www.openstreetmap.org/copyright",
};
const names = new RegExp(
	`(${Object.keys(links)
		.sort((a, b) => b.length - a.length)
		.map((name) => name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
		.join("|")})`,
	"g",
);

/** Link only our fixed credit names. Locale text is never interpreted as HTML. */
export function CreditText({ children }: { children: string }) {
	return children.split(names).map((part, index) =>
		links[part] ? (
			<a
				key={index}
				href={links[part]}
				target="_blank"
				rel="noopener noreferrer"
			>
				{part}
			</a>
		) : (
			part
		),
	);
}
