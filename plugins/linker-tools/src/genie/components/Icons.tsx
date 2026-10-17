/**
 * The Genie icons, at the prototype's drawing (20×20, 1.65 stroke, round caps
 * and joins): the rail's pen and sidebar marks, the composer's arrow, and the
 * dock header's four marks (a new conversation, the conversation history, the
 * full page, closing the dock) plus the composer's attach mark. Each is
 * decorative — the control that carries it names itself in text
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
 * The dock header's "new conversation" mark: a plus.
 * @param root0
 * @param root0.size
 */
export function PlusIcon( { size = 20 }: IconProps ) {
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
			<path d="M12 5v14M5 12h14" />
		</svg>
	);
}

/**
 * The dock header's history mark: a clock.
 * @param root0
 * @param root0.size
 */
export function HistoryIcon( { size = 20 }: IconProps ) {
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
			<circle cx="12" cy="12" r="8" />
			<path d="M12 8v4l2.5 2.5" />
		</svg>
	);
}

/**
 * The dock header's "back to the conversation" mark: a chevron.
 * @param root0
 * @param root0.size
 */
export function BackIcon( { size = 20 }: IconProps ) {
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
			<path d="m15 6-6 6 6 6" />
		</svg>
	);
}

/**
 * The dock header's "open the full page" mark: an arrow leaving its box.
 * @param root0
 * @param root0.size
 */
export function ExpandIcon( { size = 20 }: IconProps ) {
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
			<path d="M14 5h5v5M19 5l-7 7M10 19H5v-5M5 19l7-7" />
		</svg>
	);
}

/**
 * The dock header's "hide the dock" mark: a cross.
 * @param root0
 * @param root0.size
 */
export function CloseIcon( { size = 20 }: IconProps ) {
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
			<path d="M6 6l12 12M18 6 6 18" />
		</svg>
	);
}

/**
 * The composer's attach mark: a paperclip.
 * @param root0
 * @param root0.size
 */
export function AttachIcon( { size = 20 }: IconProps ) {
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
			<path d="m15 7-6.5 6.5a2.1 2.1 0 0 0 3 3L18 10a4.2 4.2 0 0 0-6-6L5.5 10.5a6.4 6.4 0 0 0 9 9L20 14" />
		</svg>
	);
}

/**
 * The composer's dictation mark: a microphone.
 * @param root0
 * @param root0.size
 */
export function MicIcon( { size = 20 }: IconProps ) {
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
			<rect x="9" y="3" width="6" height="11" rx="3" />
			<path d="M6 11a6 6 0 0 0 12 0M12 17v4" />
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

/**
 * A history row's delete mark (ticket #235).
 * @param root0
 * @param root0.size
 */
export function TrashIcon( { size = 20 }: IconProps ) {
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
			<path d="M4 7h16" />
			<path d="M10 11v6M14 11v6" />
			<path d="M6 7l1 13h10l1-13" />
			<path d="M9 7V4h6v3" />
		</svg>
	);
}

/**
 * The "email this conversation" mark (ticket #235).
 * @param root0
 * @param root0.size
 */
export function MailIcon( { size = 20 }: IconProps ) {
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
			<rect x="3" y="5" width="18" height="14" rx="2" />
			<path d="m4 7 8 6 8-6" />
		</svg>
	);
}
