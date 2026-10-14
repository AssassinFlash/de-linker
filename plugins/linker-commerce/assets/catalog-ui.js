/**
 * The product archive's filter drawer on the narrow viewports.
 *
 * The stylesheet owns the drawer's look: under 860px the rail folds into a
 * right-hand panel (`#linker-products .sidebar-filters.is-mobile-open`,
 * storefront.css) over a dimmed page — the `body.product-filter-open` state
 * (docs/specs/82-domain-language.md's rename table), whose `::before` is the
 * live page's own overlay, the viewport-wide `rgba(15, 23, 42, 0.42)` block
 * at the z-index the live stylesheet gives it.
 *
 * This script is the state, never the design: the open button reveals the
 * panel, and the close button, the "Show products" action or Escape hides it
 * again, with `aria-expanded` following. Those are the live drawer's closers
 * as well — its overlay is decoration, so a tap on the dimmed page closes
 * nothing here either. The facet links inside navigate on their own — the
 * apply button only closes.
 */
(function (window, document) {
	'use strict';

	var openButton = document.getElementById('product-filter-open');
	var closeButton = document.getElementById('product-filter-close');
	var applyButton = document.getElementById('product-filter-apply');
	var panel = document.getElementById('sidebar-filters');

	function set(open) {
		if (!panel) {
			return;
		}
		panel.classList.toggle('is-mobile-open', open);
		document.body.classList.toggle('product-filter-open', open);
		if (openButton) {
			openButton.setAttribute('aria-expanded', open ? 'true' : 'false');
		}
	}

	if (openButton && panel) {
		openButton.addEventListener('click', function () {
			set(true);
			var close = document.getElementById('product-filter-close');
			if (close) {
				close.focus();
			}
		});
	}
	if (closeButton) {
		closeButton.addEventListener('click', function () {
			set(false);
			if (openButton) {
				openButton.focus();
			}
		});
	}
	if (applyButton) {
		applyButton.addEventListener('click', function () {
			set(false);
			if (openButton) {
				openButton.focus();
			}
		});
	}
	document.addEventListener('keydown', function (event) {
		if (event.key === 'Escape' && panel && panel.classList.contains('is-mobile-open')) {
			set(false);
			if (openButton) {
				openButton.focus();
			}
		}
	});
}(window, document));
