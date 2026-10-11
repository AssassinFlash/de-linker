/**
 * Storefront product page: the gallery viewer and thumbnails, the
 * specification tab deck, the assistant entries. One block per behaviour,
 * everything read from the markup the template and the data shortcodes
 * wrote - no markup is invented here.
 */
(function () {
	"use strict";
	var root = document.getElementById("tv-storefront-pdp");
	if (!root) {
		return;
	}

	/* Gallery: a thumbnail selects the main image; the main and secondary
	   images open the viewer dialog. */
	var main = root.querySelector(".pdp-gallery-main");
	if (main) {
		root.querySelectorAll("[data-pdp-thumb]").forEach(function (thumb) {
			thumb.addEventListener("click", function () {
				var previous = root.querySelector('.pdp-thumb[aria-pressed="true"]');
				if (previous) {
					previous.setAttribute("aria-pressed", "false");
				}
				thumb.setAttribute("aria-pressed", "true");
				var source = thumb.getAttribute("data-src");
				if (source) {
					main.removeAttribute("srcset");
					main.removeAttribute("sizes");
					main.src = source;
				}
			});
		});
	}
	var viewer = root.querySelector("#pdp-image-viewer");
	var viewerImage = viewer ? viewer.querySelector("img") : null;
	root.querySelectorAll("[data-pdp-image]").forEach(function (trigger) {
		trigger.addEventListener("click", function () {
			if (!viewer || !viewerImage) {
				return;
			}
			viewerImage.src = trigger.getAttribute("data-src") || "";
			if (typeof viewer.showModal === "function") {
				viewer.showModal();
			}
		});
	});
	if (viewer) {
		var close = viewer.querySelector("[data-pdp-viewer-close]");
		if (close) {
			close.addEventListener("click", function () {
				viewer.close();
			});
		}
	}

	/* Specification deck: one disclosure is visible, the tabs select which. */
	var tabs = Array.prototype.slice.call(root.querySelectorAll('.pdp-info-tabs [role="tab"]'));
	var panels = Array.prototype.slice.call(root.querySelectorAll(".pdp-info-panel details[data-pdp-tab]"));
	var panelBox = root.querySelector(".pdp-info-panel");
	tabs.forEach(function (tab) {
		tab.addEventListener("click", function () {
			var index = (tab.id || "").replace("pdp-spec-tab-", "");
			tabs.forEach(function (other) {
				var active = other === tab;
				other.setAttribute("aria-selected", active ? "true" : "false");
				other.setAttribute("tabindex", active ? "0" : "-1");
			});
			panels.forEach(function (panel) {
				var show = panel.getAttribute("data-pdp-tab") === index;
				panel.open = show;
				panel.hidden = !show;
			});
			if (panelBox) {
				panelBox.id = "pdp-spec-panel-" + index;
				panelBox.setAttribute("aria-labelledby", "pdp-spec-tab-" + index);
			}
		});
	});

	/* The assistant entries: the tool row's ask button and the project
	   choices hand their message to the assistant. */
	function ask(message, trigger) {
		window.dispatchEvent(
			new CustomEvent("lia:ask", { detail: { message: message, trigger: trigger } })
		);
	}
	var askButton = root.querySelector("[data-pdp-ask]");
	if (askButton) {
		askButton.addEventListener("click", function () {
			ask(askButton.getAttribute("data-ask-message") || "", askButton);
		});
	}
	root.querySelectorAll("[data-project-message]").forEach(function (choice) {
		choice.addEventListener("click", function () {
			ask(choice.getAttribute("data-project-message") || "", choice);
		});
	});
	root.querySelectorAll("[data-linker-assistant-open]").forEach(function (entry) {
		entry.addEventListener("click", function () {
			window.dispatchEvent(
				new CustomEvent("lia:open", { detail: { view: entry.getAttribute("data-linker-assistant-open") } })
			);
		});
	});
})();
