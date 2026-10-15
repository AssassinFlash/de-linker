/**
 * Storefront product page: the gallery viewer and thumbnails, the
 * specification cards, the assistant entries, the sticky navigation and the
 * rail's own cues. One block per behaviour, everything read from the markup
 * the template and the data shortcodes wrote - no markup is invented here.
 *
 * The page's sticky offsets are assets, not guesses: the header and the
 * section nav are measured into the CSS variables their rules read
 * (--lk-header-h, --pdp-snav-h). The scrollspy's reach below the chrome is the
 * prototype's own threshold - 34% of the viewport, whichever is larger
 * (docs/design/2026-10-15-pdp-prototype/index.html, spy()).
 */
(function () {
	"use strict";
	var root = document.getElementById("tv-storefront-pdp");
	if (!root) {
		return;
	}

	var page = document.documentElement;
	var header = document.querySelector("header#lc-header");
	var sectionNav = root.querySelector(".pdp-section-nav");
	var sectionLinks = Array.prototype.slice.call(root.querySelectorAll(".pdp-section-link"));
	var rail = root.querySelector(".pdp-buy-inner");

	/* Measured chrome: the sticky top offsets and the anchors' scroll margins
	   follow the heights the page really renders. */
	function measure() {
		if (header) {
			page.style.setProperty("--lk-header-h", header.offsetHeight + "px");
		}
		if (sectionNav) {
			page.style.setProperty("--pdp-snav-h", sectionNav.offsetHeight + "px");
		}
	}
	if (typeof ResizeObserver !== "undefined") {
		if (header) {
			new ResizeObserver(measure).observe(header);
		}
		if (sectionNav) {
			new ResizeObserver(measure).observe(sectionNav);
		}
	}
	window.addEventListener("resize", measure);

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
	var viewerCaption = viewer ? viewer.querySelector("[data-viewer-caption]") : null;
	var viewerTrigger = null;
	root.querySelectorAll("[data-pdp-image]").forEach(function (trigger) {
		trigger.addEventListener("click", function () {
			if (trigger === mainTrigger && Date.now() < suppressClickUntil) { suppressClickUntil = 0; return; }
			if (!viewer || !viewerImage) {
				return;
			}
			viewerTrigger = trigger;
			viewerImage.src = trigger.getAttribute("data-src") || "";
			if (viewerCaption) {
				var picture = trigger.querySelector("img");
				viewerCaption.textContent = trigger.getAttribute("aria-label") || (picture ? picture.alt : "");
			}
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
		// The backdrop is the dialog element itself: a click outside the
		// picture closes, as the viewer dialog does on the live page.
		viewer.addEventListener("click", function (event) {
			if (event.target === viewer) {
				viewer.close();
			}
		});
		// Focus returns to the picture the viewer was opened from.
		viewer.addEventListener("close", function () {
			if (viewerTrigger && typeof viewerTrigger.focus === "function") {
				viewerTrigger.focus();
			}
		});
	}

	/* The assistant entries: the tool row's ask button and the project
	   choices hand their message to the assistant. */
	function ask(message, trigger) {
		/* The Genie dock listens for linker-genie-ask
		   (plugins/linker-tools/includes/Genie/Entries.php); the old
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

	/* The rail's own cues: while the rail scrolls inside its sticky box, the
	   fades mark the copy that is out of view. */
	function railCue() {
		if (!rail) {
			return;
		}
		var overflow = rail.scrollHeight > rail.clientHeight + 1;
		rail.classList.toggle("show-top-fade", overflow && rail.scrollTop > 1);
		rail.classList.toggle(
			"show-bottom-fade",
			overflow && rail.scrollTop + rail.clientHeight < rail.scrollHeight - 1
		);
	}
	if (rail) {
		rail.addEventListener("scroll", railCue, { passive: true });
		if (typeof ResizeObserver !== "undefined") {
			new ResizeObserver(railCue).observe(rail);
		}
	}
	var projectCheck = root.querySelector(".pdp-project-check");
	if (projectCheck) {
		projectCheck.addEventListener("toggle", railCue);
	}

	/* Section navigation: the link of the section in view is the current one,
	   and the strip keeps it inside its own scroll box. */
	function spy() {
		if (!sectionLinks.length) {
			return;
		}
		// The chrome below the header, or 34% of the viewport - the
		// prototype's own reach (docs/design/2026-10-15-pdp-prototype,
		// index.html spy()).
		var reach = Math.max(
			(header ? header.offsetHeight : 0) + (sectionNav ? sectionNav.offsetHeight : 0) + 16,
			Math.round(window.innerHeight * 0.34)
		);
		var current = sectionLinks[0];
		var atBottom =
			window.scrollY > 40 && window.innerHeight + window.scrollY >= page.scrollHeight - 2;
		if (atBottom) {
			current = sectionLinks[sectionLinks.length - 1];
		} else {
			sectionLinks.forEach(function (link) {
				var id = (link.getAttribute("href") || "").slice(1);
				var section = id ? document.getElementById(id) : null;
				if (section && section.getBoundingClientRect().top <= reach) {
					current = link;
				}
			});
		}
		sectionLinks.forEach(function (link) {
			link.setAttribute("aria-current", link === current ? "true" : "false");
		});
		if (!sectionNav) {
			return;
		}
		var strip = sectionNav.querySelector(".sf-container");
		if (!strip || strip.scrollWidth <= strip.clientWidth + 1) {
			return;
		}
		var stripBox = strip.getBoundingClientRect();
		var chip = current.getBoundingClientRect();
		if (chip.right > stripBox.right - 8) {
			strip.scrollLeft += chip.right - (stripBox.right - 8);
		} else if (chip.left < stripBox.left + 8) {
			strip.scrollLeft -= stripBox.left + 8 - chip.left;
		}
	}
	var spyScheduled = false;
	window.addEventListener("scroll", function () {
		if (spyScheduled) {
			return;
		}
		spyScheduled = true;
		requestAnimationFrame(function () {
			spyScheduled = false;
			spy();
		});
	}, { passive: true });
	sectionLinks.forEach(function (link) {
		link.addEventListener("click", function () {
			sectionLinks.forEach(function (other) {
				other.setAttribute("aria-current", other === link ? "true" : "false");
			});
		});
	});

	function settle() {
		measure();
		railCue();
		spy();
	}
	if (document.fonts && document.fonts.ready) {
		document.fonts.ready.then(settle);
	}
	window.addEventListener("load", settle);
	settle();
})();
