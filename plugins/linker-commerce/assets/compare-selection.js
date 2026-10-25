/**
 * The comparison selection of this browser tab.
 *
 * One rule, one place: the tab's sessionStorage holds an ordered list of
 * product IDs and nothing else, and the comparison page's own address is the
 * server-normalized source of truth — opening the page writes its list back
 * into the tab. Everything the script changes is state, never design: a
 * product's compare control gets `data-compare-selected` and `aria-pressed`,
 * the chip gets its visibility, its address and its count
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

	function chip() {
		return document.querySelector('[data-compare-chip]');
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
		var ids = read();
		var limit = max();
		var full = ids.length >= limit;
		var selected = {};
		ids.forEach(function (id) {
			selected[id] = true;
		});

		Array.prototype.forEach.call(document.querySelectorAll('[data-compare-product]'), function (control) {
			var id = control.getAttribute('data-compare-product') || '';
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
	}

	function toggle(id) {
		id = String(id || '');
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
	syncFromPage();
	paint();

	var scroll = document.querySelector('#linker-compare .linker-compare-scroll');
	var hint = document.querySelector('[data-compare-scroll-hint]');
	if (scroll && hint) {
		var measure = function () {
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
