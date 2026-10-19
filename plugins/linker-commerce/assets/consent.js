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
	document.addEventListener('DOMContentLoaded', function () {
		queueMicrotask(labelPanels);
	});
	document.addEventListener('cookieyes_consent_update', labelPanels);

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
