/** Register before the archive markup arrives so the first tap opens the filters. */
(function (document) {
	'use strict';

	function setOpen(open) {
		var opener = document.getElementById('product-filter-open');
		var panel = document.getElementById('sidebar-filters');
		var close = document.getElementById('product-filter-close');
		if (!panel || !close) {
			return;
		}

		document.body.classList.toggle('product-filter-open', open);
		opener.setAttribute('aria-expanded', open ? 'true' : 'false');
		panel.classList.toggle('is-mobile-open', open);
		(open ? close : opener).focus();
	}

	// Use the archive itself so a search includes models on every page and honours active facets.
	var delay;
	var pending;
	document.addEventListener('input', function (event) {
		var input = event.target;
		if (input.id !== 'search-box' || !input.form) return;
		var form = input.form;
		var listing = document.querySelector('[data-catalog-listing]');
		var status = document.querySelector('[data-catalog-search-status]');
		var sidebar = document.getElementById('sidebar-filters');
		if (!listing || !sidebar) return;
		clearTimeout(delay);
		pending?.abort();
		var controller = new AbortController();
		pending = controller;
		if (status) status.textContent = '';
		listing.setAttribute('aria-busy', 'true');
		delay = setTimeout(async function () {
			var url = new URL(form.action, document.baseURI);
			url.search = new URLSearchParams(new FormData(form)).toString();
			if (!input.value.trim()) url.searchParams.delete('q');
			try {
				var response = await fetch(url, {credentials: 'same-origin', signal: controller.signal});
				if (!response.ok) throw new Error(String(response.status));
				var source = document.createElement('template');
				source.innerHTML = await response.text();
				if (controller.signal.aborted) return;
				var result = source.content.querySelector('[data-catalog-listing]');
				var filters = source.content.getElementById('sidebar-filters');
				if (!result || !filters) throw new Error('Missing catalogue results');
				listing.replaceWith(result);
				sidebar.replaceWith(filters);
				window.history.replaceState(window.history.state, '', url);
				window.linkerComparePaint?.();
			} catch (error) {
				if (!controller.signal.aborted) {
					listing.removeAttribute('aria-busy');
					if (status) status.textContent = form.dataset.searchFailed;
				}
			}
		}, 250);
	});

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
}(document));
