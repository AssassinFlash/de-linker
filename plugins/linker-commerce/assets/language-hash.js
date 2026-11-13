/* A language switch keeps the section the visitor is reading.
 *
 * The header toggle, the mobile drawer and the footer switcher all carry
 * `data-linker-language-choice`. The server builds their destinations from
 * the request, which never includes the client-side fragment, so switching
 * language on a page with `#reset-card` or `#section-4` dropped it. The rule
 * here is the one the saved legal documents already needed: carry the current
 * hash through the click, but only when this page actually has that element.
 * A hash with no element behind it is not a place on the destination either.
 */
(() => {
	const links = 'a[data-linker-language-choice]';
	document.addEventListener('click', (event) => {
		const link = event.target.closest(links);
		if (!link || link.target || link.hasAttribute('download')) {
			return;
		}
		const hash = location.hash;
		if (!hash || !document.getElementById(hash.slice(1))) {
			return;
		}
		const destination = new URL(link.href);
		destination.hash = hash;
		link.href = destination.href;
	});
})();
