/**
 * The Genie workspace's icons, at the prototype's drawing (20×20, 1.65 stroke,
 * round caps and joins): the rail's pen and sidebar marks, the composer's
 * arrow. Each is decorative — the control that carries it names itself in text
 * (docs/specs/13-genie.md).
 */

interface IconProps {
	size?: number;
}

/**
 * The rail's "New conversation" row.
 * @param root0
 * @param root0.size
 */
export function NewConversationIcon( { size = 20 }: IconProps ) {
	return (
		<svg
			viewBox="0 0 24 24"
			width={ size }
			height={ size }
			fill="none"
			stroke="currentColor"
			strokeWidth="1.65"
			strokeLinecap="round"
			strokeLinejoin="round"
			aria-hidden="true"
		>
			<path d="m16 3 5 5-11 11-6 1 1-6Z" />
			<path d="m14 5 5 5" />
		</svg>
	);
}

/**
 * The sidebar disclosure mark, in the rail's brand row and in the bar.
 * @param root0
 * @param root0.size
 */
export function PanelIcon( { size = 20 }: IconProps ) {
	return (
		<svg
			viewBox="0 0 24 24"
			width={ size }
			height={ size }
			fill="none"
			stroke="currentColor"
			strokeWidth="1.65"
			strokeLinecap="round"
			strokeLinejoin="round"
			aria-hidden="true"
		>
			<rect x="3" y="4" width="18" height="16" rx="2" />
			<path d="M9 4v16" />
		</svg>
	);
}

/**
 * The composer's submit mark.
 * @param root0
 * @param root0.size
 */
export function SendIcon( { size = 20 }: IconProps ) {
	return (
		<svg
			viewBox="0 0 24 24"
			width={ size }
			height={ size }
			fill="none"
			stroke="currentColor"
			strokeWidth="1.65"
			strokeLinecap="round"
			strokeLinejoin="round"
			aria-hidden="true"
		>
			<path d="M12 19V5m-6 6 6-6 6 6" />
		</svg>
	);
}
