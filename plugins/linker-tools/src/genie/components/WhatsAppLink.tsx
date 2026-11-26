/**
 * Opens an editable WhatsApp conversation with the Linker trade desk.
 *
 * @param props       Link options.
 * @param props.url   Localized contact URL from the WordPress mount.
 * @param props.label Visible link text.
 */
export function WhatsAppLink( {
	url,
	label = 'WhatsApp',
}: {
	url?: string;
	label?: string;
} ) {
	return url ? (
		<a
			className="linker-genie-whatsapp"
			href={ url }
			target="_blank"
			rel="noopener noreferrer"
		>
			<svg
				width="14"
				height="14"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				strokeWidth="1.6"
				strokeLinecap="round"
				strokeLinejoin="round"
				aria-hidden="true"
			>
				<path d="M20.7 11.6a8.8 8.8 0 0 1-13.1 7.7L3 20.6l1.3-4.4a8.8 8.8 0 1 1 16.4-4.6Z" />
				<path d="m8.9 7.5 1.1 2.3-.8 1.2a8.5 8.5 0 0 0 3.8 3.5l1.1-1.3 2.4 1.2c-.2 1.4-1 2.1-2.3 2-3.6-.5-7.2-4.1-7.4-7.2 0-1.1.7-1.8 2.1-1.7Z" />
			</svg>
			{ label }
		</a>
	) : null;
}
