/**
 * Storefront PDP (ticket 067): quantity, model jump, lightbox, family
 * differences, section nav, and comparison overflow hint.
 */
(function () {
    var root = document.getElementById("tv-storefront-pdp");
    if (!root) {
        return;
    }

    var qty = root.querySelector(".pdp-qty-in");
    if (qty) {
        var min = parseInt(qty.getAttribute("min"), 10);
        if (isNaN(min) || min < 1) {
            min = 1;
        }
        var maxAttr = qty.getAttribute("max");
        var max = maxAttr ? parseInt(maxAttr, 10) : NaN;
        function clamp(value) {
            if (isNaN(value) || value < min) {
                value = min;
            }
            if (!isNaN(max) && max >= min && value > max) {
                value = max;
            }
            qty.value = String(value);
            return value;
        }
        root.querySelectorAll(".pdp-qty-step").forEach(function (button) {
            button.addEventListener("click", function () {
                var step = parseInt(button.getAttribute("data-qstep"), 10) || 0;
                clamp((parseInt(qty.value, 10) || min) + step);
            });
        });
        qty.addEventListener("change", function () {
            clamp(parseInt(qty.value, 10));
        });
    }

    var model = root.querySelector("[data-product-model]");
    if (model) {
        model.addEventListener("change", function () {
            if (model.value) {
                window.location.assign(model.value);
            }
        });
    }

    var viewer = root.querySelector("#pdp-image-viewer");
    var viewerImg = viewer ? viewer.querySelector("img") : null;
    var viewerCap = viewer ? viewer.querySelector("[data-viewer-caption]") : null;
    var lastTrigger = null;
    function openViewer(src, caption, trigger) {
        if (!viewer || !viewerImg || !src) {
            return;
        }
        lastTrigger = trigger || document.activeElement;
        viewerImg.src = src;
        if (viewerCap) {
            viewerCap.textContent = caption || "";
        }
        if (typeof viewer.showModal === "function") {
            viewer.showModal();
        }
    }
    function closeViewer() {
        if (!viewer) {
            return;
        }
        if (typeof viewer.close === "function" && viewer.open) {
            viewer.close();
        }
        if (lastTrigger && typeof lastTrigger.focus === "function") {
            lastTrigger.focus();
        }
    }
    root.querySelectorAll("[data-pdp-image]").forEach(function (button) {
        button.addEventListener("click", function () {
            openViewer(
                button.getAttribute("data-src") || "",
                button.getAttribute("data-caption") || "",
                button
            );
        });
    });
    root.querySelectorAll("[data-pdp-thumb]").forEach(function (button) {
        button.addEventListener("click", function () {
            var src = button.getAttribute("data-src") || "";
            var main = root.querySelector("[data-pdp-main]");
            if (main && src) {
                if (main.tagName === "IMG") {
                    main.src = src;
                    main.removeAttribute("srcset");
                    main.removeAttribute("sizes");
                } else {
                    main.setAttribute("data-src", src);
                    main.setAttribute("data-caption", button.getAttribute("data-caption") || "");
                    var nested = main.querySelector("img");
                    if (nested) {
                        nested.src = src;
                    }
                }
            }
            root.querySelectorAll("[data-pdp-thumb]").forEach(function (other) {
                other.setAttribute("aria-pressed", other === button ? "true" : "false");
            });
        });
    });
    var closer = root.querySelector("[data-pdp-close-image]");
    if (closer) {
        closer.addEventListener("click", closeViewer);
    }
    if (viewer) {
        viewer.addEventListener("close", function () {
            if (lastTrigger && typeof lastTrigger.focus === "function") {
                lastTrigger.focus();
            }
        });
    }

    var diff = root.querySelector("[data-family-diff]");
    if (diff) {
        function syncDiff() {
            root.querySelectorAll("#compare [data-same]").forEach(function (row) {
                row.hidden = diff.checked && row.getAttribute("data-same") === "1";
            });
        }
        diff.addEventListener("change", syncDiff);
        syncDiff();
    }

    var links = [].slice.call(root.querySelectorAll(".pdp-section-link"));
    function syncNav() {
        if (!links.length) {
            return;
        }
        var hash = location.hash;
        var selected = links.filter(function (link) {
            return link.getAttribute("href") === hash;
        })[0] || links[0];
        links.forEach(function (link) {
            if (link === selected) {
                link.setAttribute("aria-current", "location");
            } else {
                link.removeAttribute("aria-current");
            }
        });
    }
    links.forEach(function (link) {
        link.addEventListener("click", function () {
            window.setTimeout(syncNav, 0);
        });
    });
    window.addEventListener("hashchange", syncNav);
    syncNav();

    var table = root.querySelector(".pdp-family-scroll");
    var hint = root.querySelector(".pdp-comparison-hint");
    function syncHint() {
        if (!table || !hint) {
            return;
        }
        hint.hidden = table.scrollWidth <= table.clientWidth + 2;
    }
    syncHint();
    window.addEventListener("resize", syncHint);
})();
