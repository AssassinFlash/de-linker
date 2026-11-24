interface Window {
	linkerTrack?: (
		name:
			| "configurator_start"
			| "configurator_complete"
			| "configurator_export_pdf",
		params?: { export_type: "pdf" | "csv" },
	) => boolean;
}
