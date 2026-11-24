interface Window {
	linkerTrack?: (
		name: 'genie_ask' | 'generate_lead',
		params:
			| { surface: 'hero' | 'workspace' | 'floating' }
			| { lead_surface: 'contact' | 'inquiry' }
	) => void;
}
