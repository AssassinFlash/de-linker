interface Window {
	linkerTrack?: {
		(
			name: 'genie_open' | 'genie_ask',
			params: {
				surface: 'hero' | 'workspace' | 'floating';
				page_type?: string;
			}
		): boolean | void;
		(
			name: 'generate_lead',
			params: {
				lead_surface:
					'contact' | 'inquiry' | 'genie_contact' | 'genie_inquiry';
			}
		): boolean | void;
	};
}
