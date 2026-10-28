/**
 * The comparison selection of this browser tab.
 *
 * One rule, one place: the tab's sessionStorage holds an ordered list of
 * product IDs and nothing else, and the comparison page's own address is the
 * server-normalized source of truth — opening the page writes its list back
 * into the tab. Everything the script changes is state, never design: a
 * product's compare control gets `data-compare-selected` and `aria-pressed`,
 * the chip gets its visibility, its address, its count and its position below
 * the current header
 * (docs/specs/19-tool-pages.md). The words and the look of both belong to the
 * markup and the stylesheet, so nothing here needs translating.
 *
 * The markup contract, for whatever renders a compare control:
 *
 *   <button type="button" data-compare-product="ID" aria-pressed="false">
 *     <span data-compare-label>…</span>
 *   </button>
 *   <a data-compare-chip data-compare-page="/compare-products/" data-compare-max="4" hidden>…</a>
 */
(function (window, document) {
	'use strict';

	var storageKey = 'linkerCompareIds';
	var aliases = {};
	var compactChip = window.matchMedia ? window.matchMedia('(max-width: 1279px)') : null;
	var alignmentFrame = null;
	var alignmentTracking = false;
	var headerObserver = null;

	function identities() {
		var map = {};
		Array.prototype.forEach.call(document.querySelectorAll('[data-compare-identities]'), function (node) {
			try {
				var rows = JSON.parse(node.getAttribute('data-compare-identities') || '{}');
				if (!rows || typeof rows !== 'object' || Array.isArray(rows)) {
					return;
				}
				Object.keys(rows).forEach(function (id) {
					var source = String(rows[id]);
					if (/^[1-9][0-9]*$/.test(id) && /^[1-9][0-9]*$/.test(source)) {
						map[id] = source;
					}
				});
			} catch (error) {
				// Malformed page data must not destroy the visitor's selection.
			}
		});
		return map;
	}

	function chip() {
		return document.querySelector('[data-compare-chip]');
	}

	function alignChip() {
		var el = chip();
		var header = document.getElementById('lc-header');
		if (!el || el.hidden || !header || (compactChip && !compactChip.matches)) {
			return;
		}
		// The phone admin bar scrolls away with the header. Its actual bottom
		// includes every intermediate position; header height alone cannot.
		el.style.setProperty('--compare-chip-top', Math.max(0, header.getBoundingClientRect().bottom) + 'px');
	}

	function scheduleChipAlignment() {
		var el = chip();
		if (!el || el.hidden || alignmentFrame !== null || (compactChip && !compactChip.matches)) {
			return;
		}
		alignmentFrame = window.requestAnimationFrame(function () {
			alignmentFrame = null;
			alignChip();
		});
	}

	function trackChip(visible) {
		var header = document.getElementById('lc-header');
		if (visible && header) {
			if (!alignmentTracking) {
				window.addEventListener('scroll', scheduleChipAlignment, { passive: true });
				window.addEventListener('resize', scheduleChipAlignment, { passive: true });
				if (window.ResizeObserver) {
					headerObserver = new window.ResizeObserver(scheduleChipAlignment);
					headerObserver.observe(header);
				}
				alignmentTracking = true;
			}
			alignChip();
			return;
		}
		if (!alignmentTracking) {
			return;
		}
		window.removeEventListener('scroll', scheduleChipAlignment);
		window.removeEventListener('resize', scheduleChipAlignment);
		if (headerObserver) {
			headerObserver.disconnect();
			headerObserver = null;
		}
		if (alignmentFrame !== null) {
			window.cancelAnimationFrame(alignmentFrame);
			alignmentFrame = null;
		}
		alignmentTracking = false;
	}

	function max() {
		var el = chip();
		var value = el ? parseInt(el.getAttribute('data-compare-max'), 10) : 0;
		return isNaN(value) || value < 1 ? 4 : value;
	}

	function pageUrl() {
		var el = chip();
		var value = el ? el.getAttribute('data-compare-page') : '';
		return value || '/compare-products/';
	}

	function clean(rows) {
		if (!Array.isArray(rows)) {
			return [];
		}
		var out = [];
		var seen = {};
		rows.forEach(function (id) {
			id = String(id);
			id = aliases[id] || id;
			if (!/^[1-9][0-9]*$/.test(id) || seen[id]) {
				return;
			}
			seen[id] = true;
			out.push(id);
		});
		return out.slice(0, max());
	}

	function read() {
		try {
			return clean(JSON.parse(window.sessionStorage.getItem(storageKey) || '[]'));
		} catch (error) {
			return [];
		}
	}

	function write(ids) {
		try {
			window.sessionStorage.setItem(storageKey, JSON.stringify(clean(ids)));
		} catch (error) {
			// A tab that refuses storage keeps no selection; the page still works.
		}
	}

	function address(ids) {
		var base = String(pageUrl());
		if (!ids.length) {
			return base;
		}
		return base + (base.indexOf('?') === -1 ? '?' : '&') + 'ids=' + ids.join(',');
	}

	function paint() {
		aliases = identities();
		var ids = read();
		write(ids);
		var limit = max();
		var full = ids.length >= limit;
		var selected = {};
		ids.forEach(function (id) {
			selected[id] = true;
		});

		Array.prototype.forEach.call(document.querySelectorAll('[data-compare-product]'), function (control) {
			var raw = control.getAttribute('data-compare-product') || '';
			var id = aliases[raw] || raw;
			var on = !!selected[id];
			control.setAttribute('aria-pressed', on ? 'true' : 'false');
			control.setAttribute('data-compare-selected', on ? 'true' : 'false');
			control.disabled = full && !on;
			if (full && !on) {
				control.setAttribute('data-compare-limit', 'reached');
			} else {
				control.removeAttribute('data-compare-limit');
			}
		});

		var el = chip();
		if (!el) {
			trackChip(false);
			return;
		}
		el.hidden = ids.length === 0;
		el.setAttribute('data-compare-count-value', String(ids.length));
		if (ids.length) {
			el.setAttribute('href', address(ids));
		}
		var count = el.querySelector('[data-compare-count]');
		if (count) {
			count.textContent = ids.length + '/' + limit;
		}
		trackChip(!el.hidden);
	}

	function toggle(id) {
		id = String(id || '');
		id = aliases[id] || id;
		if (!/^[1-9][0-9]*$/.test(id)) {
			return;
		}
		var ids = read();
		var at = ids.indexOf(id);
		if (at >= 0) {
			ids.splice(at, 1);
		} else if (ids.length >= max()) {
			return;
		} else {
			ids.push(id);
		}
		write(ids);
		paint();
	}

	/**
	 * The comparison page writes its own selection back: the address is the
	 * normalized list, so a refresh, a bookmark or a shared link leaves the
	 * tab agreeing with the page it is looking at.
	 */
	function syncFromPage() {
		var page = document.getElementById('linker-compare');
		if (!page) {
			return;
		}
		var raw = page.getAttribute('data-compare-ids') || '';
		var ids = raw === '' ? [] : raw.split(',');
		write(ids);
	}

	document.addEventListener('click', function (event) {
		var control = event.target && event.target.closest ? event.target.closest('[data-compare-product]') : null;
		if (!control) {
			return;
		}
		if (event.preventDefault) {
			event.preventDefault();
		}
		toggle(control.getAttribute('data-compare-product'));
	});

	window.addEventListener('pageshow', function (event) {
		if (event.persisted) {
			syncFromPage();
			paint();
		}
	});

	window.linkerComparePaint = paint;
	aliases = identities();
	syncFromPage();
	paint();

	var scroll = document.querySelector('#linker-compare .linker-compare-scroll');
	var hint = document.querySelector('[data-compare-scroll-hint]');
	if (scroll && hint) {
		var measure = function () {
			// Allow one CSS pixel at the layout boundary; a rounding remainder alone needs no scrolling cue.
			hint.hidden = scroll.scrollWidth <= scroll.clientWidth + 1;
		};
		measure();
		window.addEventListener('resize', measure);
		if (window.ResizeObserver) {
			var observer = new window.ResizeObserver(measure);
			observer.observe(scroll);
			observer.observe(scroll.querySelector('table'));
		}
	}
}(window, document));
