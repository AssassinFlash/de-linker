/**
 * The FAQ + document library's interaction layer (/faq-download/).
 *
 * Progressive enhancement, never content: the page the server prints carries
 * every question, every document row and its own words, and this script only
 * narrows what is shown — the two tabs, the type chips, the search and the
 * pagination all hide or clone rows that are already in the HTML. With the
 * script absent the page is the full register, one tab after the other, and
 * every heading, row and download link still reads.
 *
 * The words the script itself renders — the counters, the search's empty
 * state, the pager's labels, the hint that marks a match found in a question's
 * answer body — come from the JSON config the page's own fragment prints
 * (`[linker_library_config]`, translated server-side), so no customer-visible
 * string is baked into this file.
 *
 * The prototype this page was accepted from is
 * docs/design/2026-10-15-faq-download-prototype (variant 5); the mapping from
 * its runtime-rendered states to this markup-first implementation is in
 * docs/specs/176-faq-download.md §2.
 */
(function (scope) {
	"use strict";

	var slice = Array.prototype.slice;
	var PAGE_SIZE = 20;

	/* ---------- pure helpers, exported to node --test ---------- */

	/** Case- and accent-insensitive form of a string. */
	function normalize(value) {
		return String(value == null ? "" : value)
			.normalize("NFD")
			.replace(/[\u0300-\u036f]/g, "")
			.toLowerCase();
	}

	/** The query's words, folded; empty ones dropped. */
	function terms(query) {
		return normalize(query).trim().split(/\s+/).filter(Boolean);
	}

	/** Every word of the query appears in the text (the register's AND match). */
	function matches(text, query) {
		var words = terms(query);
		if (!words.length) {
			return true;
		}
		var haystack = normalize(text);
		return words.every(function (word) {
			return haystack.indexOf(word) !== -1;
		});
	}

	/**
	 * A hit's rank: a match in the title counts for more than one in the body,
	 * and a whole-title match wins outright.
	 */
	function score(title, body, query) {
		var needle = normalize(query).trim();
		if (!needle) {
			return 0;
		}
		var head = normalize(title);
		var tail = normalize(body || "");
		var total = 0;
		if (head === needle) {
			total += 100;
		}
		if (head.indexOf(needle) === 0) {
			total += 40;
		} else if (head.indexOf(needle) !== -1) {
			total += 24;
		}
		if (tail.indexOf(needle) !== -1) {
			total += 8;
		}
		terms(needle).forEach(function (word) {
			if (head.indexOf(word) !== -1) {
				total += 6;
			} else if (tail.indexOf(word) !== -1) {
				total += 2;
			}
		});
		return total;
	}

	/**
	 * The ranges of a text the query matches, merged and in order. The
	 * haystack is folded, and folding keeps offsets for precomposed text, so a
	 * range marks the same characters of the original.
	 */
	function highlightRanges(text, query) {
		var source = String(text == null ? "" : text);
		var folded = normalize(source);
		var found = [];
		terms(query).forEach(function (word) {
			var at = folded.indexOf(word);
			while (at !== -1) {
				found.push([at, at + word.length]);
				at = folded.indexOf(word, at + word.length);
			}
		});
		found.sort(function (a, b) {
			return a[0] - b[0] || a[1] - b[1];
		});
		var merged = [];
		found.forEach(function (range) {
			var last = merged[merged.length - 1];
			if (last && range[0] <= last[1]) {
				last[1] = Math.max(last[1], range[1]);
			} else {
				merged.push(range.slice());
			}
		});
		return merged;
	}

	/** One result window: the first page, the last, the current and its neighbours. */
	function pageWindow(page, pages) {
		var seen = {};
		[1, pages, page - 1, page, page + 1].forEach(function (number) {
			if (number >= 1 && number <= pages) {
				seen[number] = true;
			}
		});
		return Object.keys(seen)
			.map(Number)
			.sort(function (a, b) {
				return a - b;
			});
	}

	/** A list's page: the page's rows and the page count they clamp into. */
	function paginate(items, page, size) {
		var total = size || PAGE_SIZE;
		var pages = Math.max(1, Math.ceil(items.length / total));
		var current = Math.min(Math.max(page || 1, 1), pages);
		var start = (current - 1) * total;
		return { page: current, pages: pages, items: items.slice(start, start + total) };
	}

	/** The tab a URL states; anything but `tab=documents` is the FAQ tab. */
	function tabFromSearch(search) {
		return /(^|[?&])tab=documents(&|$)/.test(String(search || "")) ? "documents" : "faq";
	}

	/** The URL for a tab: the documents tab is named, the default is not. */
	function tabUrl(pathname, search, hash, tab) {
		var rest = String(search || "").replace(/[?&]?tab=[^&]*/g, "").replace(/^[?&]+/, "").replace(/[?&]+$/, "");
		var base = rest ? "?" + rest : "";
		var named = tab === "documents" ? (base ? "&" : "?") + "tab=documents" : "";
		return String(pathname || "") + base + named + (hash || "");
	}

	if (typeof module !== "undefined" && module.exports) {
		module.exports = {
			normalize: normalize,
			terms: terms,
			matches: matches,
			score: score,
			highlightRanges: highlightRanges,
			pageWindow: pageWindow,
			paginate: paginate,
			tabFromSearch: tabFromSearch,
			tabUrl: tabUrl,
			PAGE_SIZE: PAGE_SIZE,
		};
	}

	if (!scope.document) {
		return;
	}

	/* ---------- the page ---------- */

	var root = scope.document.getElementById("linker-faq-page");
	if (!root) {
		return;
	}

	var config = readConfig();
	var i18n = (config && config.i18n) || {};
	var pageSize = (config && config.pageSize) || PAGE_SIZE;
	var genieUrl = (config && config.genieUrl) || "/genie/";

	var tabs = slice.call(root.querySelectorAll("[data-library-tab]"));
	var panels = slice.call(root.querySelectorAll("[data-library-panel]"));
	var search = root.querySelector(".linker-library-search");
	var input = root.querySelector(".linker-library-q");
	var clearButton = root.querySelector("[data-library-clear]");
	var resultCount = root.querySelector("#linker-library-result-count");
	var suggestBox = root.querySelector("#linker-library-suggest");
	var filters = root.querySelector("[data-library-filters]");
	var main = root.querySelector(".linker-library-main");
	var preparedThumbnails = new WeakSet();

	var state = {
		tab: tabFromSearch(scope.location.search),
		q: "",
		type: "all",
		pages: {},
		searchPage: 1,
		open: {},
		suggest: [],
		suggestIndex: -1,
		suggestOpen: false,
		rendering: false,
		spyLock: 0,
	};

	/** The cards: their rows, their count, their pager and their soft empty. */
	var cards = slice.call(root.querySelectorAll("[data-library-card]")).map(function (element) {
		var title = element.querySelector(".linker-library-card-title");
		return {
			el: element,
			kind: element.getAttribute("data-library-kind") || "",
			id: element.id,
			title: title ? title.textContent : "",
			rowsWrap: element.querySelector(".linker-library-rows"),
			count: element.querySelector("[data-library-card-count]"),
			rows: slice.call(element.querySelectorAll("[data-library-item]")),
			pager: null,
			empty: null,
		};
	});

	/** Every row of the page: what the search reads, and where the row lives. */
	var index = [];
	cards.forEach(function (card) {
		card.rows.forEach(function (row, position) {
			var title = row.querySelector(".linker-library-qa-q, .linker-library-doc-title");
			row.setAttribute("data-library-position", String(position));
			row.setAttribute("data-library-order", String(index.length));
			index.push({
				el: row,
				card: card,
				order: index.length,
				kind: card.kind,
				type: row.getAttribute("data-library-type") || "",
				group: row.getAttribute("data-library-group") || card.title,
				product: (row.querySelector(".linker-library-qa-product") || {}).textContent || "",
				title: title ? title.textContent : row.textContent,
				text: row.textContent,
			});
		});
	});
	var questions = index.filter(function (hit) {
		return hit.kind !== "document";
	});
	var documents = index.filter(function (hit) {
		return hit.kind === "document";
	});
	var totals = {
		faq: questions.length,
		documents: documents.length,
		all: questions.length + documents.length,
	};

	/* ---------- small helpers ---------- */

	/** A translated label of the page's config, with the count substituted. */
	function label(key, value) {
		var text = String(i18n[key] == null ? "" : i18n[key]);
		if (value == null) {
			return text;
		}
		return text.indexOf("%d") === -1 ? text + " " + value : text.replace("%d", String(value));
	}

	function plural(keyOne, keyOther, value) {
		return label(value === 1 ? keyOne : keyOther, value);
	}

	function countOf(node, value) {
		if (node) {
			node.textContent = String(value);
		}
	}

	/** Rows a card currently shows (the type filter already applied). */
	function visibleRows(card) {
		return card.rows.filter(function (row) {
			return !row.hasAttribute("data-library-filtered");
		});
	}

	/** A row's clone with the query marked, for the flat result list. */
	function cloneRow(hit, query) {
		var clone = hit.el.cloneNode(true);
		clone.removeAttribute("hidden");
		if (clone.tagName === "DETAILS") {
			clone.open = !!state.open[hit.order];
			var question = clone.querySelector(".linker-library-qa-q");
			var where = clone.querySelector(".linker-library-qa-where");
			if (where) {
				where.hidden = !query || !!(question && matches(question.textContent, query));
			}
		}
		mark(clone, query);
		prepareThumbnails(clone);
		return clone;
	}

	/** Wraps the query's matches of a subtree in <mark>. */
	function mark(node, query) {
		if (!node || !query || !terms(query).length) {
			return node;
		}
		var walker = scope.document.createTreeWalker(node, 4);
		var texts = [];
		while (walker.nextNode()) {
			texts.push(walker.currentNode);
		}
		texts.forEach(function (text) {
			var ranges = highlightRanges(text.nodeValue, query);
			if (!ranges.length) {
				return;
			}
			var fragment = scope.document.createDocumentFragment();
			var cursor = 0;
			ranges.forEach(function (range) {
				fragment.appendChild(scope.document.createTextNode(text.nodeValue.slice(cursor, range[0])));
				var element = scope.document.createElement("mark");
				element.textContent = text.nodeValue.slice(range[0], range[1]);
				fragment.appendChild(element);
				cursor = range[1];
			});
			fragment.appendChild(scope.document.createTextNode(text.nodeValue.slice(cursor)));
			text.parentNode.replaceChild(fragment, text);
		});
		return node;
	}

	function clear(node) {
		while (node && node.firstChild) {
			node.removeChild(node.firstChild);
		}
	}

	function readConfig() {
		var node = scope.document.getElementById("linker-library-config");
		if (!node) {
			return null;
		}
		try {
			return JSON.parse(node.textContent || "{}");
		} catch (error) {
			return null;
		}
	}

	function prefersReduced() {
		return typeof scope.matchMedia === "function" && scope.matchMedia("(prefers-reduced-motion: reduce)").matches;
	}

	/* ---------- the tabs ---------- */

	function tabCount(tab) {
		return root.querySelector("#linker-library-tab-" + tab + " .linker-library-n");
	}

	function setTab(tab, options) {
		var next = tab === "documents" ? "documents" : "faq";
		var moved = next !== state.tab;
		state.tab = next;
		tabs.forEach(function (element) {
			var on = element.getAttribute("data-library-tab") === next;
			element.setAttribute("aria-selected", on ? "true" : "false");
			element.tabIndex = on ? 0 : -1;
		});
		panels.forEach(function (panel) {
			panel.hidden = panel.getAttribute("data-library-panel") !== next || !!state.q.trim();
		});
		slice.call(root.querySelectorAll("[data-library-nav]")).forEach(function (group) {
			group.hidden = group.getAttribute("data-library-nav") !== next;
		});
		if (options && options.url) {
			scope.history.replaceState(
				null,
				"",
				tabUrl(scope.location.pathname, scope.location.search, options.keepHash ? scope.location.hash : "", next)
			);
		}
		if (state.q.trim()) {
			// Searching: the tab picks the half of the match set the flat list
			// shows, from its first page.
			state.searchPage = 1;
			renderSearch();
			return;
		}
		if (moved) {
			// The list starts where the tab bar does: a reader who switched tabs
			// from further down the page sees the first card, not the middle of
			// the other one.
			var bar = root.querySelector(".linker-library-tabbar");
			measureSticky();
			var offset = parseFloat(readVar("--ll-header-h")) || 0;
			var top = bar ? bar.getBoundingClientRect().top + scope.scrollY - offset : 0;
			if (bar && scope.scrollY > top + 8) {
				scope.scrollTo(0, Math.max(0, top));
			}
		}
	}

	/* ---------- cards: pagination and the soft empty ---------- */

	function pagerFor(card) {
		if (!card.pager) {
			card.pager = scope.document.createElement("nav");
			card.pager.className = "linker-library-pager";
			card.rowsWrap.appendChild(card.pager);
		}
		return card.pager;
	}

	function renderPager(card, page, pages) {
		var pager = pagerFor(card);
		clear(pager);
		if (pages <= 1) {
			return;
		}
		pager.setAttribute("aria-label", label("pages"));
		function button(text, value, current) {
			var node = scope.document.createElement("button");
			node.type = "button";
			node.setAttribute("data-library-page", String(value));
			node.setAttribute("data-library-list", card.id);
			if (current) {
				node.setAttribute("aria-current", "page");
			}
			if (value === "prev") {
				node.disabled = page <= 1;
			}
			if (value === "next") {
				node.disabled = page >= pages;
			}
			node.textContent = text;
			return node;
		}
		pager.appendChild(button(label("previous"), "prev", false));
		var previous = 0;
		pageWindow(page, pages).forEach(function (number) {
			if (previous && number - previous > 1) {
				var gap = scope.document.createElement("span");
				gap.className = "linker-library-gap";
				gap.setAttribute("aria-hidden", "true");
				gap.textContent = "…";
				pager.appendChild(gap);
			}
			previous = number;
			pager.appendChild(button(String(number), number, number === page));
		});
		pager.appendChild(button(label("next"), "next", false));
	}

	function renderCard(card) {
		var rows = visibleRows(card);
		var window_ = paginate(rows, state.pages[card.id] || 1, pageSize);
		state.pages[card.id] = window_.page;
		var shown = {};
		window_.items.forEach(function (row) {
			shown[row.getAttribute("data-library-position")] = true;
		});
		card.rows.forEach(function (row) {
			var visible = !row.hasAttribute("data-library-filtered") && shown[row.getAttribute("data-library-position")];
			if (visible) {
				row.removeAttribute("hidden");
			} else {
				row.setAttribute("hidden", "");
			}
		});
		countOf(card.count, rows.length);
		renderPager(card, window_.page, window_.pages);
		if (card.empty) {
			card.empty.hidden = rows.length > 0 || card.kind !== "document";
		}
	}

	function renderCards() {
		cards.forEach(renderCard);
	}

	/* ---------- the type chips ---------- */

	function setType(type) {
		state.type = type || "all";
		// The rows carry `data-library-type` too (it is what they are filtered
		// by); aria-pressed is the chips' alone, so the selector is scoped to
		// the container the fragments print them in.
		slice.call(root.querySelectorAll("[data-library-filters] [data-library-type]")).forEach(function (chip) {
			chip.setAttribute("aria-pressed", chip.getAttribute("data-library-type") === state.type ? "true" : "false");
		});
		cards.forEach(function (card) {
			if (card.kind !== "document") {
				return;
			}
			card.rows.forEach(function (row) {
				var on = state.type === "all" || row.getAttribute("data-library-type") === state.type;
				if (on) {
					row.removeAttribute("data-library-filtered");
				} else {
					row.setAttribute("data-library-filtered", "");
				}
			});
			state.pages[card.id] = 1;
			// The rail and the chip row count what the filter leaves, the way
			// the prototype's own rail did.
			var visible = visibleRows(card).length;
			slice.call(root.querySelectorAll('[data-library-spy-link][href="#' + card.id + '"]')).forEach(function (link) {
				countOf(link.querySelector(".linker-library-n"), visible);
				link.classList.toggle("is-dim", visible === 0);
			});
		});
		renderCards();
	}

	/* ---------- the search ---------- */

	function resultsHost() {
		var host = root.querySelector("[data-library-results]");
		if (!host) {
			host = scope.document.createElement("div");
			host.className = "linker-library-results";
			host.setAttribute("data-library-results", "");
			host.hidden = true;
			main.insertBefore(host, main.firstChild);
		}
		return host;
	}

	/** The hits of a query: every matching row, best match first. */
	function searchHits(query) {
		var hits = index.filter(function (hit) {
			return matches(hit.text, query);
		});
		hits.sort(function (a, b) {
			return score(b.title, b.text, query) - score(a.title, a.text, query) || a.order - b.order;
		});
		return hits;
	}

	/** Whether a hit is the tab's: documents belong to the documents tab. */
	function inTab(hit, tab) {
		return tab === "documents" ? hit.kind === "document" : hit.kind !== "document";
	}

	/** A tab's share of a query's hits, best match first. */
	function hitsOfTab(query, tab) {
		return searchHits(query).filter(function (hit) {
			return inTab(hit, tab);
		});
	}

	function topHits(pool, query) {
		var hits = pool.filter(function (hit) {
			return matches(hit.text, query);
		});
		hits.sort(function (a, b) {
			return score(b.title, b.text, query) - score(a.title, a.text, query) || a.order - b.order;
		});
		return hits.slice(0, 6);
	}

	function hitKind(hit) {
		return hit.kind === "document" ? label("document") : hit.kind === "trade" ? label("trade") : label("answer");
	}

	function emptyResult() {
		var ledger = scope.document.createElement("div");
		ledger.className = "linker-library-ledger";
		var empty = scope.document.createElement("div");
		empty.className = "linker-library-empty";
		var text = scope.document.createElement("p");
		text.textContent = label("empty");
		var link = scope.document.createElement("a");
		link.className = "linker-library-genie";
		link.href = genieUrl;
		link.textContent = label("askGenie");
		empty.appendChild(text);
		empty.appendChild(link);
		ledger.appendChild(empty);
		return ledger;
	}

	function renderSearch() {
		var query = state.q.trim();
		// The list is the active tab's half of the hits (the tab's own count is
		// that half's size), and the field's counter is the whole match set.
		var hits = hitsOfTab(query, state.tab);
		var host = resultsHost();
		var window_ = paginate(hits, state.searchPage, pageSize);
		state.searchPage = window_.page;
		clear(host);
		if (!hits.length) {
			host.appendChild(emptyResult());
		} else {
			var ledger = scope.document.createElement("div");
			ledger.className = "linker-library-ledger";
			window_.items.forEach(function (hit) {
				var row = scope.document.createElement("div");
				row.className = "linker-library-hit";
				var eye = scope.document.createElement("p");
				eye.className = "linker-library-hit-eye";
				eye.textContent = hit.group + " · " + hitKind(hit);
				row.appendChild(eye);
				row.appendChild(cloneRow(hit, query));
				ledger.appendChild(row);
			});
			host.appendChild(ledger);
			if (window_.pages > 1) {
				renderPager({ rowsWrap: host, id: "search", pager: null }, window_.page, window_.pages);
			}
		}
		host.hidden = false;
		countOf(resultCount, plural("resultsOne", "resultsOther", searchHits(query).length));
		countOf(tabCount("faq"), hitsOfTab(query, "faq").length);
		countOf(tabCount("documents"), hitsOfTab(query, "documents").length);
	}

	function resetCounts() {
		countOf(resultCount, label("onFile", totals.all));
		countOf(tabCount("faq"), totals.faq);
		countOf(tabCount("documents"), totals.documents);
	}

	/**
	 * Enter or leave the flat result list. Called from the input's own events
	 * and from a suggestion's activation — never from renderSuggestions(),
	 * which is why a cleared or abandoned query cannot reopen the dropdown.
	 */
	function applySearch() {
		var query = state.q.trim();
		state.rendering = true;
		if (query) {
			root.classList.add("is-searching");
			panels.forEach(function (panel) {
				panel.hidden = true;
			});
			slice.call(root.querySelectorAll("[data-library-nav]")).forEach(function (group) {
				group.hidden = true;
			});
			renderSearch();
		} else {
			root.classList.remove("is-searching");
			var host = root.querySelector("[data-library-results]");
			if (host) {
				host.hidden = true;
				clear(host);
			}
			resetCounts();
			renderCards();
			setTab(state.tab, { url: false });
		}
		state.rendering = false;
		if (clearButton) {
			clearButton.hidden = !query;
		}
		renderSuggestions();
		markActive();
	}

	/* ---------- the suggestions ---------- */

	/**
	 * Renders the dropdown for the state it is in. It opens only when
	 * `state.suggestOpen` says so: a render that follows a click inside the
	 * input's own box, or a positional change, never reopens what the reader
	 * closed (the prototype's own rule).
	 */
	function renderSuggestions() {
		if (!suggestBox || !input) {
			return;
		}
		var query = state.q.trim();
		if (!state.suggestOpen || !query) {
			state.suggest = [];
			state.suggestIndex = -1;
			clear(suggestBox);
			suggestBox.hidden = true;
			input.setAttribute("aria-expanded", "false");
			input.removeAttribute("aria-activedescendant");
			return;
		}
		var groups = [
			{ hits: topHits(questions, query), name: label("questions") },
			{ hits: topHits(documents, query), name: label("documents") },
		];
		state.suggest = [];
		clear(suggestBox);
		groups.forEach(function (group) {
			if (!group.hits.length) {
				return;
			}
			var heading = scope.document.createElement("p");
			heading.className = "linker-library-sug-label";
			heading.textContent = group.name;
			suggestBox.appendChild(heading);
			group.hits.forEach(function (hit) {
				var item = scope.document.createElement("button");
				item.type = "button";
				item.className = "linker-library-sug";
				item.setAttribute("role", "option");
				item.setAttribute("data-library-suggest", String(state.suggest.length));
				item.id = "linker-library-sug-" + state.suggest.length;
				var text = scope.document.createElement("span");
				text.className = "linker-library-sug-text";
				text.textContent = hit.title;
				var meta = scope.document.createElement("span");
				meta.className = "linker-library-sug-meta";
				meta.textContent = hit.group + (hit.product ? " · " + hit.product : "") + " · " + hitKind(hit);
				item.appendChild(mark(text, query));
				item.appendChild(meta);
				if (state.suggest.length === state.suggestIndex) {
					item.classList.add("is-active");
					item.setAttribute("aria-selected", "true");
				} else {
					item.setAttribute("aria-selected", "false");
				}
				suggestBox.appendChild(item);
				state.suggest.push(hit);
			});
		});
		if (!state.suggest.length) {
			state.suggestOpen = false;
			suggestBox.hidden = true;
			input.setAttribute("aria-expanded", "false");
			input.removeAttribute("aria-activedescendant");
			return;
		}
		suggestBox.hidden = false;
		input.setAttribute("aria-expanded", "true");
		if (state.suggestIndex >= 0 && state.suggest[state.suggestIndex]) {
			input.setAttribute("aria-activedescendant", "linker-library-sug-" + state.suggestIndex);
		} else {
			input.removeAttribute("aria-activedescendant");
		}
	}

	function closeSuggestions() {
		state.suggestOpen = false;
		state.suggestIndex = -1;
		renderSuggestions();
	}

	/** A suggestion's own move: a document opens, a question is shown in place. */
	function activateSuggestion(position) {
		var hit = state.suggest[position];
		if (!hit) {
			return;
		}
		closeSuggestions();
		if (hit.kind === "document") {
			var link = hit.el.querySelector(".linker-library-dl");
			if (link && /^https?:/i.test(link.href)) {
				scope.open(link.href, "_blank", "noopener");
			}
			return;
		}
		// The question: the search gives way to the tab that holds it.
		var position_ = Math.max(visibleRows(hit.card).indexOf(hit.el), 0);
		state.q = "";
		if (input) {
			input.value = "";
		}
		applySearch();
		setTab("faq", { url: true });
		state.pages[hit.card.id] = Math.floor(position_ / pageSize) + 1;
		renderCard(hit.card);
		state.open[hit.order] = true;
		hit.el.open = true;
		scope.requestAnimationFrame(function () {
			var summary = hit.el.querySelector("summary");
			if (summary) {
				summary.focus({ preventScroll: true });
			}
			scrollToElement(hit.el);
		});
	}

	/* ---------- anchors, the sticky stack and the spy ---------- */

	function readVar(name) {
		return scope.getComputedStyle(root).getPropertyValue(name);
	}

	/** The sticky stack's height, read off the page: header, tab bar, chip row. */
	function measureSticky() {
		var header = scope.document.getElementById("lc-header");
		var headerHeight = header ? Math.ceil(header.getBoundingClientRect().bottom) : 0;
		if (!headerHeight) {
			headerHeight = parseFloat(readVar("--ll-header-h")) || 0;
		}
		var bar = root.querySelector(".linker-library-tabbar");
		var barHeight = bar ? Math.ceil(bar.getBoundingClientRect().height) : 0;
		var chips = root.querySelector(".linker-library-chips");
		var chipsHeight =
			chips && !chips.hidden && scope.getComputedStyle(chips).display !== "none"
				? Math.ceil(chips.getBoundingClientRect().height)
				: 0;
		// Written only when the value moved: this runs from the scroll handler,
		// and an unconditional write would dirty the layout on every frame.
		var next = { header: headerHeight + "px", sticky: (barHeight || 48) + chipsHeight + "px" };
		if (next.header !== state.headerVar) {
			state.headerVar = next.header;
			root.style.setProperty("--ll-header-h", next.header);
		}
		if (next.sticky !== state.stickyVar) {
			state.stickyVar = next.sticky;
			root.style.setProperty("--ll-sticky", next.sticky);
		}
	}

	function stickyOffset() {
		measureSticky();
		return (parseFloat(readVar("--ll-header-h")) || 0) + (parseFloat(readVar("--ll-sticky")) || 0) + 12;
	}

	function scrollToElement(element) {
		if (!element) {
			return;
		}
		var top = element.getBoundingClientRect().top + scope.scrollY - stickyOffset();
		scope.scrollTo({ top: Math.max(0, top), behavior: prefersReduced() ? "auto" : "smooth" });
	}

	/** Marks the rail and chip link of the card the reader is in. */
	function markActive() {
		if (state.rendering || Date.now() < state.spyLock) {
			return;
		}
		var nodes = slice.call(root.querySelectorAll("[data-library-spy]"));
		if (!nodes.length) {
			return;
		}
		var line = stickyOffset() + 24;
		var current = nodes[0];
		nodes.forEach(function (node) {
			if (node.getBoundingClientRect().top <= line) {
				current = node;
			}
		});
		var id = current.id;
		var zone = current.getAttribute("data-library-zone") || "";
		slice.call(root.querySelectorAll("[data-library-spy-link]")).forEach(function (link) {
			var href = (link.getAttribute("href") || "").slice(1);
			var linkZone = link.getAttribute("data-library-zone") || "";
			var on = href === id || (linkZone !== "" && linkZone === zone);
			link.classList.toggle("is-active", on);
			if (on && href === id) {
				link.setAttribute("aria-current", "location");
			} else {
				link.removeAttribute("aria-current");
			}
		});
	}

	/* ---------- wiring ---------- */

	/** Every source and search clone owns its own image readiness listeners. */
	function prepareThumbnails(container) {
		slice.call(container.querySelectorAll(".linker-library-thumb img")).forEach(function (image) {
			if (preparedThumbnails.has(image)) {
				return;
			}
			preparedThumbnails.add(image);
			var tile = image.parentNode;
			var shown = function () {
				image.hidden = false;
				tile.classList.remove("is-type");
				tile.classList.add("has-src", "has-img");
			};
			var failed = function () {
				image.hidden = true;
				tile.classList.remove("has-img", "has-src");
				tile.classList.add("is-type");
			};
			image.addEventListener("load", shown, { once: true });
			image.addEventListener("error", failed, { once: true });
			if (image.complete) {
				if (image.naturalWidth) {
					shown();
				} else {
					failed();
				}
			}
		});
	}

	function prepare() {
		cards.forEach(function (card) {
			if (card.kind !== "document") {
				return;
			}
			card.empty = scope.document.createElement("p");
			card.empty.className = "linker-library-empty-soft";
			card.empty.textContent = label("emptySoft");
			card.empty.hidden = true;
			card.rowsWrap.appendChild(card.empty);
		});
		prepareThumbnails(root);
	}

	function movedPage(list, raw) {
		var current = list === "search" ? state.searchPage : state.pages[list] || 1;
		return raw === "prev" ? current - 1 : raw === "next" ? current + 1 : Number(raw);
	}

	function bind() {
		if (input) {
			input.addEventListener("input", function () {
				var value = input.value;
				if (value !== state.q) {
					state.searchPage = 1;
					state.suggestIndex = -1;
				}
				state.q = value;
				state.suggestOpen = !!value.trim();
				applySearch();
			});
			input.addEventListener("focusin", function () {
				if (state.q.trim() && !state.suggestOpen) {
					state.suggestOpen = true;
					renderSuggestions();
				}
			});
			input.addEventListener("keydown", function (event) {
				if (event.key === "ArrowDown" || event.key === "ArrowUp") {
					if (!state.q.trim()) {
						return;
					}
					event.preventDefault();
					if (!state.suggestOpen) {
						state.suggestOpen = true;
						renderSuggestions();
					}
					var total = state.suggest.length;
					if (!total) {
						return;
					}
					var step = event.key === "ArrowDown" ? 1 : -1;
					state.suggestIndex =
						state.suggestIndex < 0
							? step > 0
								? 0
								: total - 1
							: (state.suggestIndex + step + total) % total;
					renderSuggestions();
					var row = scope.document.getElementById("linker-library-sug-" + state.suggestIndex);
					if (row && row.scrollIntoView) {
						row.scrollIntoView({ block: "nearest" });
					}
					return;
				}
				if (event.key === "Enter" && state.suggestIndex >= 0) {
					event.preventDefault();
					activateSuggestion(state.suggestIndex);
					return;
				}
				if (event.key === "Escape" && state.suggestOpen) {
					// The dropdown closes; the query stays (the prototype's own
					// rule — Escape dismisses the overlay, not the search).
					event.preventDefault();
					closeSuggestions();
				}
			});
		}
		root.addEventListener("click", function (event) {
			var target = event.target;
			if (!target || !target.closest) {
				return;
			}
			var cleared = target.closest("[data-library-clear]");
			if (cleared) {
				event.preventDefault();
				state.q = "";
				state.searchPage = 1;
				if (input) {
					input.value = "";
					input.focus();
				}
				closeSuggestions();
				applySearch();
				return;
			}
			var suggestion = target.closest("[data-library-suggest]");
			if (suggestion) {
				event.preventDefault();
				activateSuggestion(Number(suggestion.getAttribute("data-library-suggest")));
				return;
			}
			var tab = target.closest("[data-library-tab]");
			if (tab) {
				event.preventDefault();
				setTab(tab.getAttribute("data-library-tab"), { url: true });
				return;
			}
			var chip = target.closest("[data-library-type]");
			if (chip && chip.tagName === "BUTTON") {
				event.preventDefault();
				setType(chip.getAttribute("data-library-type"));
				return;
			}
			var page = target.closest("[data-library-page]");
			if (page && !page.disabled) {
				event.preventDefault();
				var list = page.getAttribute("data-library-list");
				var next = movedPage(list, page.getAttribute("data-library-page"));
				if (list === "search") {
					state.searchPage = next;
					renderSearch();
				} else {
					state.pages[list] = next;
					var card = cards.filter(function (candidate) {
						return candidate.id === list;
					})[0];
					if (card) {
						renderCard(card);
					}
				}
				var anchor = list === "search" ? root.querySelector("[data-library-results]") : scope.document.getElementById(list);
				var first = anchor && anchor.querySelector("[data-library-item]:not([hidden])");
				var action = first && first.querySelector("summary, .linker-library-dl");
				if (action) {
					action.focus({ preventScroll: true });
				}
				var bar = root.querySelector(".linker-library-tabbar");
				if (anchor && bar && anchor.getBoundingClientRect().top < bar.getBoundingClientRect().bottom) {
					scrollToElement(anchor);
				}
				return;
			}
			var link = target.closest("a[data-library-spy-link]");
			if (link) {
				var id = (link.getAttribute("href") || "").slice(1);
				var element = scope.document.getElementById(id);
				if (!element) {
					return;
				}
				event.preventDefault();
				scope.history.replaceState(null, "", scope.location.pathname + scope.location.search + "#" + id);
				state.spyLock = Date.now() + 900;
				markActive();
				scrollToElement(element);
			}
		});
		root.addEventListener("keydown", function (event) {
			if ((event.key !== "ArrowRight" && event.key !== "ArrowLeft") || !event.target.closest) {
				return;
			}
			var tab = event.target.closest("[data-library-tab]");
			if (!tab) {
				return;
			}
			event.preventDefault();
			var position = tabs.indexOf(tab);
			var next = tabs[position + (event.key === "ArrowRight" ? 1 : -1)];
			if (next) {
				next.focus();
				setTab(next.getAttribute("data-library-tab"), { url: true });
			}
		});
		root.addEventListener(
			"toggle",
			function (event) {
				if (state.rendering) {
					// The render's own open/close, not the reader's.
					return;
				}
				var node = event.target;
				if (!node.classList || !node.classList.contains("linker-library-qa") || !node.hasAttribute("data-library-order")) {
					return;
				}
				var hit = index[Number(node.getAttribute("data-library-order"))];
				if (hit) {
					state.open[hit.order] = !!node.open;
				}
			},
			true
		);
		scope.document.addEventListener(
			"pointerdown",
			function (event) {
				if (!state.suggestOpen || !event.target.closest) {
					return;
				}
				if (event.target.closest(".linker-library-searchbox")) {
					return;
				}
				closeSuggestions();
			},
			true
		);
		scope.addEventListener(
			"scroll",
			function () {
				markActive();
			},
			{ passive: true }
		);
		scope.addEventListener("resize", function () {
			measureSticky();
		});
	}

	function start() {
		root.classList.add("is-enhanced");
		if (search) {
			search.hidden = false;
		}
		if (filters) {
			filters.hidden = false;
		}
		prepare();
		bind();
		measureSticky();
		setTab(state.tab, { url: false });
		resetCounts();
		setType("all");
		var hash = scope.location.hash.slice(1);
		if (hash) {
			var element = scope.document.getElementById(hash);
			if (element) {
				scrollToElement(element);
			}
		}
		markActive();
	}

	start();
})(typeof window !== "undefined" ? window : globalThis);
