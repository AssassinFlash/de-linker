import type { SVGProps } from "react";

const paths = {
	upload: "M12 16V3m-5 5 5-5 5 5M4 16v5h16v-5",
	plus: "M12 5v14M5 12h14",
	folder: "M3 7V5h6l2 2h10v13H3V7Z",
	overview: "M3 3h7v7H3V3Zm11 0h7v7h-7V3ZM3 14h7v7H3v-7Zm11 0h7v7h-7v-7Z",
	energy: "m13 2-9 12h7l-1 8 10-13h-7l1-7Z",
	arrow: "M5 12h14m-5-5 5 5-5 5",
	undo: "M8 5 3 10l5 5M3 10h10a7 7 0 0 1 7 7",
	redo: "m16 5 5 5-5 5m5-5H11a7 7 0 0 0-7 7",
	check: "m5 12 4 4L19 6",
	location: "M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 1 1 14 0ZM12 7v6M9 10h6",
	layers: "m3 8 9-5 9 5-9 5-9-5Zm0 5 9 5 9-5M3 18l9 5 9-5",
	refresh: "M20 8a9 9 0 1 0 1 8M20 3v6h-6",
	back: "M19 12H5m5-5-5 5 5 5",
	solar: "m5 5-2 12h18L19 5H5Zm3 0L7 17m9-12 1 12M4 11h16M9 21h6m-3-4v4",
	system: "M3 4h7v7H3V4Zm11 9h7v7h-7v-7ZM7 11v6h7M14 7h7m-3-3 3 3-3 3",
	route: "M4 4h4v4H4V4Zm12 12h4v4h-4v-4ZM8 6h7a3 3 0 0 1 0 6H9a3 3 0 0 0 0 6h7",
	report: "M14 3H5v18h14V8l-5-5Zm0 0v5h5M8 12h8M8 16h5",
	sparkle: "m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3Z",
	trash: "M4 7h16M10 4h4M6 7l1 13h10l1-13M10 11v6M14 11v6",
} as const;
export function Icon({
	name,
	...props
}: SVGProps<SVGSVGElement> & { name: keyof typeof paths }) {
	return (
		<svg
			viewBox="0 0 24 24"
			width="20"
			height="20"
			fill="none"
			stroke="currentColor"
			strokeWidth="1.5"
			strokeLinecap="round"
			strokeLinejoin="round"
			aria-hidden="true"
			{...props}
		>
			<path d={paths[name]} />
		</svg>
	);
}
