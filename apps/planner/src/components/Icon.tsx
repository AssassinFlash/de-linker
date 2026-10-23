import type { SVGProps } from "react";

const paths = {
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
