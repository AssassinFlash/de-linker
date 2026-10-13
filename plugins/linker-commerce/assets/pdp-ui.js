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
	var mainTrigger = root.querySelector("[data-pdp-main]");
	var thumbs = Array.from(root.querySelectorAll("[data-pdp-thumb]"));
	var suppressClickUntil = 0;
	// Measure the actual bar, including localized wrapping, text zoom and safe area.
	var actionBar = root.querySelector(".pdp-mobile-action");
	if (actionBar && typeof ResizeObserver !== "undefined") {
		new ResizeObserver(function () {
			var height = actionBar.getBoundingClientRect().height;
			if (height) document.body.style.setProperty("--pdp-action-height", height + "px");
		}).observe(actionBar);
	}
	if (main && mainTrigger) {
		var selected = 0;
		function selectImage(index) {
			if (!thumbs.length) return;
			selected = (index + thumbs.length) % thumbs.length;
			thumbs.forEach(function (thumb, position) {
				thumb.setAttribute("aria-pressed", position === selected ? "true" : "false");
			});
			var source = thumbs[selected].getAttribute("data-src");
			if (source) {
				main.removeAttribute("srcset");
				main.removeAttribute("sizes");
				main.src = source;
				mainTrigger.setAttribute("aria-label", thumbs[selected].getAttribute("aria-label") || main.alt);
				// Viewer always opens the image currently selected, including desktop.
				mainTrigger.setAttribute("data-src", source);
			}
		}
		thumbs.forEach(function (thumb, index) {
			thumb.addEventListener("click", function () { selectImage(index); });
		});
		var touch = null;
		mainTrigger.addEventListener("touchstart", function (event) {
			if (!window.matchMedia("(max-width: 860px)").matches || event.touches.length !== 1) return;
			touch = { x: event.touches[0].clientX, y: event.touches[0].clientY };
			suppressClickUntil = 0;
		}, { passive: true });
		mainTrigger.addEventListener("touchend", function (event) {
			if (!touch || !event.changedTouches.length) return;
			var dx = event.changedTouches[0].clientX - touch.x;
			var dy = event.changedTouches[0].clientY - touch.y;
			touch = null;
			// 40px separates a deliberate horizontal swipe from a tap/vertical scroll.
			if (Math.abs(dx) >= 40 && Math.abs(dx) > Math.abs(dy) && thumbs.length > 1) {
				selectImage(selected + (dx < 0 ? 1 : -1));
				// Suppress only the immediate synthetic click, never a later tap.
				suppressClickUntil = Date.now() + 350;
			}
		}, { passive: true });
		mainTrigger.addEventListener("touchcancel", function () { touch = null; });
		mainTrigger.addEventListener("keydown", function (event) {
			if (event.key === "ArrowRight" || event.key === "ArrowLeft") {
				event.preventDefault();
				selectImage(selected + (event.key === "ArrowRight" ? 1 : -1));
			}
		});
	}
	var viewer = root.querySelector("#pdp-image-viewer");
	var viewerImage = viewer ? viewer.querySelector("img") : null;
	root.querySelectorAll("[data-pdp-image]").forEach(function (trigger) {
		trigger.addEventListener("click", function () {
			if (trigger === mainTrigger && Date.now() < suppressClickUntil) { suppressClickUntil = 0; return; }
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
		var close = viewer.querySelector("[data-pdp-close-image]");
		if (close) {
			close.addEventListener("click", function () {
				viewer.close();
			});
		}
	}

	/* Specification deck: the tabs select which group's panel is visible. */
	var tabs = Array.prototype.slice.call(root.querySelectorAll('.pdp-info-tabs [role="tab"]'));
	var panels = Array.prototype.slice.call(root.querySelectorAll(".pdp-info-panel"));
	tabs.forEach(function (tab, position) {
		tab.addEventListener("click", function () {
			var index = (tab.id || "").replace("pdp-spec-tab-", "");
			tabs.forEach(function (other) {
				var active = other === tab;
				other.setAttribute("aria-selected", active ? "true" : "false");
				other.setAttribute("tabindex", active ? "0" : "-1");
			});
			panels.forEach(function (panel, panelPosition) {
				var show = (panel.id || "").replace("pdp-spec-panel-", "") === index || panelPosition === position;
				panel.hidden = !show;
			});
		});
	});

	/* The assistant entries: the tool row's ask button and the project
	   choices hand their message to the assistant. */
	function ask(message, trigger) {
		/* The Genie dock listens for linker-genie-ask (App.tsx); the old
		   assistant's lia:ask name died with its plugin. */
		window.dispatchEvent(
			new CustomEvent("linker-genie-ask", { detail: { message: message, trigger: trigger } })
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
