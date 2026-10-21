/* Saved legal documents create navigation after the server's link localizer.
 * Resolve those entries with native Polylang URLs supplied by the server,
 * and carry a valid section hash through the existing language controls. */
(() => {
	const root = document.querySelector('.legal-root');
	if (!root) {
		return;
	}
	for (const link of root.querySelectorAll('.lga-docs-link')) {
		const route = new URL(link.href).pathname;
		if (window.LinkerLegalRoutes?.[route]) {
			link.href = window.LinkerLegalRoutes[route];
		}
	}
	document.addEventListener('click', (event) => {
		const link = event.target.closest('a[data-linker-language-choice]');
		if (
			!link ||
			!/^#section-\d+$/.test(location.hash) ||
			!document.getElementById(location.hash.slice(1))
		) {
			return;
		}
		const destination = new URL(link.href);
		destination.hash = location.hash;
		link.href = destination.href;
	});
})();
