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
	function connectNoticeReader() {
		const reader = document.querySelector('.cky-notice-des');
		if (!reader) return;

		function showRemainingText() {
			reader.toggleAttribute('data-scroll-more', reader.scrollHeight - reader.clientHeight - reader.scrollTop > 1);
		}
		function measure() {
			if (reader.scrollHeight > reader.clientHeight) {
				reader.tabIndex = 0;
			} else {
				reader.removeAttribute('tabindex');
			}
			showRemainingText();
		}
		const size = new ResizeObserver(measure);
		size.observe(reader);
		for (const paragraph of reader.children) size.observe(paragraph);
		reader.addEventListener('scroll', showRemainingText, { passive: true });
		measure();
	}
	function connectPreferences() {
		const panel = document.querySelector('#ckyPreferenceCenter');
		const modal = panel && panel.closest('.cky-modal');
		if (!modal) {
			return false;
		}
		connectNoticeReader();
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
		const revisit = document.querySelector('#tv-footer-v2 .cky-banner-element');
		if (revisit) {
			new IntersectionObserver(([entry]) => {
				revisit.toggleAttribute('data-in-view', entry.isIntersecting);
			}).observe(revisit);
		}
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
			if (!/^_ga(?:_|$)|^_cl(?:ck|sk)$/.test(name)) {
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

	const googleTag = 'script[src*="googletagmanager.com/gtag/js"]';
	const liveTag = googleTag + ':not([type="text/plain"]):not([type="javascript/blocked"])';
	const optedOut = window['ga-disable-' + measurementId()] === true;
	let statistics;
	function cookieValue(name) {
		const cookie = document.cookie.split('; ').find((entry) => entry.startsWith(name + '='));
		return cookie ? cookie.slice(name.length + 1) : '';
	}
	function cookieAllowsAnalytics() {
		return cookieValue('cookieyes-consent').split(',').includes('analytics:yes');
	}
	// Site Kit queues its config after this script. Keep private search terms,
	// password reset and receipt keys out of the first page_view as well as events.
	function searchPath(url) {
		if (url.searchParams.has('s') || /^\/(?:de\/)?search(?:\/|$)/i.test(url.pathname)) {
			return url.pathname.startsWith('/de/') ? '/de/search/' : '/search/';
		}
		return '';
	}
	function analyticsUrl(value, campaign) {
		if (!value) return '';
		const url = new URL(value);
		if (url.origin !== location.origin) return url.origin + '/';
		const safe = new URL(searchPath(url) || url.pathname, url.origin);
		if (campaign) {
			for (const key of ['utm_source', 'utm_medium', 'utm_campaign', 'utm_id', 'utm_term', 'utm_content']) {
				const tag = url.searchParams.get(key);
				if (tag && /^[a-z0-9._~-]+$/i.test(tag)) safe.searchParams.set(key, tag);
			}
		}
		return safe.href;
	}
	if (typeof window.gtag === 'function') {
		// Enhanced measurement reads the raw query independently of page_location.
		const searchKeys = ['q', 's', 'search', 'query', 'keyword'];
		window.gtag('policy', 'get_url', function (_container, _permission, data) {
			return data.component !== 'query' || !searchKeys.includes(data.queryKey);
		});
		const context = {
			page_location: analyticsUrl(location.href, true),
			page_referrer: analyticsUrl(document.referrer, false),
		};
		if (searchPath(new URL(location.href))) context.page_title = 'Search';
		window.gtag('set', context);
	}

	const eventFields = {
		generate_lead: ['lead_surface'],
		configurator_start: [],
		configurator_complete: [],
		configurator_export_pdf: ['export_type'],
		genie_ask: ['surface'],
		genie_handoff: [],
		datasheet_download: ['brand', 'doc_kind'],
		sign_up: ['business_type', 'country'],
	};
	window.linkerTrack = function (name, params = {}) {
		const allowed = cookieValue('cookieyes-consent') ? cookieAllowsAnalytics() : statistics === true;
		if (optedOut || !allowed || statistics === false || typeof window.gtag !== 'function' || !Object.hasOwn(eventFields, name)) return false;
		const payload = { page_lang: document.documentElement.lang.startsWith('de') ? 'de' : 'en' };
		for (const field of eventFields[name]) {
			if (params[field]) payload[field] = params[field];
		}
		window.gtag('event', name, payload);
		return true;
	};

	document.addEventListener('click', function (event) {
		const link = event.target.closest?.('a[data-doc-kind]');
		if (link) window.linkerTrack('datasheet_download', { brand: link.dataset.docBrand, doc_kind: link.dataset.docKind });
		const handoff = event.target.closest?.('[data-genie-handoff], .linker-genie-app a[href^="mailto:"], .linker-genie-hero__surface a[href^="mailto:"]');
		if (handoff) window.linkerTrack('genie_handoff');
	});
	function releaseTag() {
		const held = document.querySelector(googleTag + '[type="text/plain"]');
		const id = measurementId();
		if (!held || !id || window['ga-disable-' + id] === true || document.querySelector(liveTag)) return;
		window['ga-disable-' + id] = false;
		const tag = document.createElement('script');
		tag.async = true;
		tag.src = held.src;
		tag.dataset.linkerGtagReleased = '1';
		held.replaceWith(tag);
	}
	let clarityTag;
	function releaseClarity() {
		if (!window.linkerClarityProject || clarityTag) return;
		window.clarity = window.clarity || function () {
			(window.clarity.q = window.clarity.q || []).push(arguments);
		};
		window.clarity('consentv2', {analytics_Storage: 'granted', ad_Storage: 'denied'});
		clarityTag = document.createElement('script');
		clarityTag.async = true;
		clarityTag.src = 'https://www.clarity.ms/tag/' + encodeURIComponent(window.linkerClarityProject);
		document.head.append(clarityTag);
	}
	function withdrawClarity() {
		// ConsentV2 and pagehide both flush Clarity's collector before unloading.
		// Gate its two transports for the remainder of this withdrawn document.
		function isCollector(url) {
			const target = new URL(url, document.baseURI);
			return target.protocol === 'https:' && target.hostname.endsWith('.clarity.ms') && target.pathname === '/collect';
		}
		const beacon = navigator.sendBeacon?.bind(navigator);
		if (beacon) {
			navigator.sendBeacon = (url, data) => isCollector(url) || beacon(url, data);
		}
		const open = XMLHttpRequest.prototype.open;
		XMLHttpRequest.prototype.open = function (method, url, ...args) {
			if (isCollector(url)) this.send = () => this.abort();
			return open.call(this, method, url, ...args);
		};
		window.clarity('consentv2', {analytics_Storage: 'denied', ad_Storage: 'denied'});
	}
	// CookieYes changes the shared cookie but emits its event only in the active tab.
	const consentChannel = window.BroadcastChannel ? new BroadcastChannel('linker-analytics-consent') : null;
	if (consentChannel) consentChannel.onmessage = function () {
		if (!cookieAllowsAnalytics()) setStatistics(false);
	};
	function setStatistics(allowed, notifyTabs = false) {
		const id = measurementId();
		const previous = statistics;
		statistics = allowed;
		if (id) window['ga-disable-' + id] = optedOut || !allowed;
		if (allowed) {
			releaseTag();
			releaseClarity();
		} else if (previous !== false) {
			if (notifyTabs && previous === true) consentChannel?.postMessage('withdrawn');
			if (clarityTag) withdrawClarity();
			clearAnalyticsCookies();
			if (clarityTag || document.querySelector(liveTag)) location.reload();
		}
	}
	document.addEventListener('DOMContentLoaded', function () {
		if (cookieAllowsAnalytics()) setStatistics(true);
	});
	document.addEventListener('cookieyes_consent_update', function (event) {
		const accepted = event.detail?.accepted;
		setStatistics(Array.isArray(accepted) ? accepted.includes('analytics') : cookieAllowsAnalytics(), true);
	}, true);
	document.addEventListener('wp_listen_for_consent_change', function (event) {
		if (Object.hasOwn(event.detail || {}, 'statistics')) {
			setStatistics(event.detail.statistics === 'allow', true);
		}
	}, true);
})();
