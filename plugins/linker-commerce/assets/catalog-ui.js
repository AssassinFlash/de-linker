/** Register before the archive markup arrives so the first tap opens the filters. */
(function (document) {
	'use strict';

	function setOpen(open) {
		var opener = document.getElementById('product-filter-open');
		var panel = document.getElementById('sidebar-filters');
		var focusTarget = open ? document.getElementById('product-filter-close') : opener;

		document.body.classList.toggle('product-filter-open', open);
		opener.setAttribute('aria-expanded', open ? 'true' : 'false');
		if (panel) {
			panel.classList.toggle('is-mobile-open', open);
		}
		if (focusTarget) {
			focusTarget.focus();
		}
	}

	document.addEventListener('click', function (event) {
		var button = event.target.closest?.('button');
		if (!button) {
			return;
		}
		if (button.id === 'product-filter-open') {
			setOpen(true);
		} else if (button.id === 'product-filter-close' || button.id === 'product-filter-apply') {
			setOpen(false);
		}
	});
	document.addEventListener('keydown', function (event) {
		if (event.key === 'Escape' && document.body?.classList.contains('product-filter-open')) {
			setOpen(false);
		}
	});
	document.addEventListener('DOMContentLoaded', function () {
		var panel = document.getElementById('sidebar-filters');
		if (panel && document.body.classList.contains('product-filter-open') && !panel.classList.contains('is-mobile-open')) {
			setOpen(true);
		}
	}, { once: true });
}(document));
