/** FAQ progressive enhancement. Content stays readable without this script. */
(function (scope) {
	"use strict";
	/** Pure AND-token filter over existing question, answer and model text. */
	function matches(text, query) {
		var normalize = function (value) {
			return value.normalize("NFKD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase();
		};
		var haystack = normalize(text);
		return normalize(query).trim().split(/\s+/).every(function (term) { return haystack.includes(term); });
	}
	if (typeof module !== "undefined" && module.exports) module.exports = { matches: matches };
	if (!scope.document) return;
	var root = scope.document.getElementById("linker-faq-page");
	if (!root) return;
	var search = root.querySelector("[data-faq-search]");
	if (!search) return;
	var input = search.querySelector("input");
	var result = search.querySelector("[data-faq-result]");
	var questions = Array.from(root.querySelectorAll(".linker-answer, .linker-trade-question"));
	var documents = Array.from(root.querySelectorAll(".linker-document"));
	var groups = Array.from(root.querySelectorAll(".linker-answers-group, .linker-trade-category, .linker-documents-group"));
	var sections = Array.from(root.querySelectorAll(".linker-faq-section"));
	// Preserve the reader's own open groups when a search is cleared.
	var previousOpen = null;
	search.hidden = false;
	input.addEventListener("input", function () {
		var query = input.value.trim();
		if (query && previousOpen === null) previousOpen = groups.filter(function (group) { return group.open; });
		questions.concat(documents).forEach(function (item) {
			item.hidden = !matches(item.textContent, query);
		});
		groups.forEach(function (group) {
			var items = Array.from(group.querySelectorAll(".linker-answer, .linker-trade-question, .linker-document"));
			group.hidden = !items.some(function (item) { return !item.hidden; });
			if (group.tagName === "DETAILS") group.open = query ? !group.hidden : (previousOpen || []).includes(group);
		});
		// A section whose every entry is filtered out takes its heading with it.
		sections.forEach(function (section) {
			var items = Array.from(section.querySelectorAll(".linker-answer, .linker-trade-question, .linker-document"));
			section.hidden = !items.some(function (item) { return !item.hidden; });
		});
		if (!query) previousOpen = null;
		var count = questions.concat(documents).filter(function (item) { return !item.hidden; }).length;
		result.textContent = !query ? "" : count ? result.dataset.resultLabel.replace("%d", String(count)) : result.dataset.emptyLabel;
	});
})(typeof window !== "undefined" ? window : globalThis);
