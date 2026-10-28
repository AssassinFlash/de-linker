/**
 * Basic mode withdrawal. CMP owns choice storage and Woo owns source cookies.
 * Disable an already loaded Google tag before its consent-update listener runs:
 * otherwise a denied update may send a cookieless ping (Advanced mode).
 */
(function () {
	'use strict';

	// CookieYes 3.5.7 hard-codes English aria-labels even for German banners.
	// The visible translated heading is the accessible name in both languages.
	function labelPanels() {
		[
			[
				'.cky-consent-container',
				'[data-cky-tag="title"]',
				'linker-cookieyes-title',
			],
			[
				'#ckyPreferenceCenter',
				'[data-cky-tag="detail-title"]',
				'linker-cookieyes-preferences-title',
			],
		].forEach(function (entry) {
			const panel = document.querySelector(entry[0]);
			const heading = panel && panel.querySelector(entry[1]);
			if (heading) {
				heading.id = entry[2];
				panel.setAttribute('aria-labelledby', heading.id);
			}
		});
	}
	function connectPreferences() {
		const panel = document.querySelector('#ckyPreferenceCenter');
		const modal = panel && panel.closest('.cky-modal');
		if (!modal) {
			return false;
		}
		let open = false;
		let opener = null;
		function focusPanel(event) {
			if ((!event || event.target === modal) && open && !panel.contains(panel.ownerDocument.activeElement)) {
				panel.querySelector('[data-cky-tag="detail-close"]')?.focus();
			}
		}
		function sync() {
			const next = modal.classList.contains('cky-modal-open');
			if (next === open) {
				return;
			}
			open = next;
			if (open) {
				const active = panel.ownerDocument.activeElement;
				opener = panel.contains(active) ? null : active;
				// CookieYes resets its English name whenever the panel opens.
				labelPanels();
				focusPanel();
			} else {
				if (opener && opener.isConnected) {
					opener.focus();
				}
				opener = null;
			}
		}
		new window.MutationObserver(sync).observe(modal, {
			attributes: true,
			attributeFilter: ['class'],
		});
		// The native opening transition also changes visibility. Focus can be
		// unavailable at its initial hidden frame; no delay is needed afterward.
		modal.addEventListener('transitionstart', focusPanel);
		modal.addEventListener('transitionend', focusPanel);
		labelPanels();
		sync();
		return true;
	}

	document.addEventListener('DOMContentLoaded', function () {
		queueMicrotask(function () {
			labelPanels();
			if (connectPreferences()) {
				return;
			}
			// CookieYes can insert the panel after fetching its configuration.
			const waiting = new window.MutationObserver(function () {
				if (connectPreferences()) {
					waiting.disconnect();
				}
			});
			waiting.observe(document.body, { childList: true, subtree: true });
		});
	});
	document.addEventListener('cookieyes_consent_update', labelPanels);
	document.addEventListener('keydown', function (event) {
		if (event.key !== 'Escape') {
			return;
		}
		const close = document.querySelector('.cky-modal-open #ckyPreferenceCenter [data-cky-tag="detail-close"]');
		if (close) {
			event.preventDefault();
			close.click();
		}
	});

	function measurementId() {
		if (window.linkerConsentMeasurementID) {
			return window.linkerConsentMeasurementID;
		}
		const script = document.querySelector(
			'script[src*="googletagmanager.com/gtag/js"]'
		);
		if (!script) {
			return null;
		}
		const url = new URL(script.getAttribute('src'), location.href);
		return url.searchParams.get('id');
	}

	function clearAnalyticsCookies() {
		const domains = [''];
		const parts = location.hostname.split('.');
		while (parts.length > 1) {
			domains.push(parts.join('.'), '.' + parts.join('.'));
			parts.shift();
		}
		document.cookie.split(';').forEach(function (cookie) {
			const name = cookie.trim().split('=')[0];
			if (!/^_ga(?:_|$)/.test(name)) {
				return;
			}
			domains.forEach(function (domain) {
				document.cookie =
					name +
					'=; Max-Age=0; path=/' +
					(domain ? '; domain=' + domain : '');
			});
		});
	}

	document.addEventListener(
		'wp_listen_for_consent_change',
		function (event) {
			if (
				!event.detail ||
				!Object.prototype.hasOwnProperty.call(
					event.detail,
					'statistics'
				)
			) {
				return;
			}
			const allowed = event.detail.statistics === 'allow';
			const id = measurementId();
			if (id) {
				window['ga-disable-' + id] = !allowed;
			}
			if (!allowed) {
				clearAnalyticsCookies();
				// Remove the measuring library's event handlers by reloading into the
				// CMP's denied state. A blocked placeholder has no active src.
				if (
					document.querySelector(
						'script[src*="googletagmanager.com/gtag/js"]:not([type="text/plain"]):not([type="javascript/blocked"])'
					)
				) {
					location.reload();
				}
			}
		},
		true
	);
})();
