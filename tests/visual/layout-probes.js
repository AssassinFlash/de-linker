/**
 * In-page layout defect probes. Evaluated by layout-selfcheck.mjs with
 * `page.evaluate(source, cfg)`; this file is a single function expression and
 * never runs under Node.
 *
 * Every rule is a geometric fact read from getComputedStyle and
 * getBoundingClientRect, so a hit is reproducible without looking at pixels.
 * Overlay/decoration exceptions are explicit in `cfg` and in the report.
 */

(cfg = {}) => {
	const issues = [];
	const CSS = (element) => getComputedStyle(element);
	const r1 = (value) => Math.round(value * 10) / 10;
	const RECT = (rect) => ({
		x: r1(rect.x),
		y: r1(rect.y),
		w: r1(rect.width),
		h: r1(rect.height),
	});

	const OVERLAY_SELECTORS = cfg.overlaySelectors ?? [];
	const SKIP_SR_SELECTOR =
		'[class*="screen-reader"], [class*="sr-only"], [class*="visually-hidden"], [class*="skip-link"], [class*="a11y"]';
	const TAP_TARGET = cfg.tapTarget ?? 24;

	/** Short, unique-enough selector for a human to find the node again. */
	const path = (element) => {
		const parts = [];
		let node = element;
		for (let depth = 0; node && node.nodeType === 1 && depth < 6; depth++) {
			if (node.id) {
				parts.unshift(`#${node.id}`);
				break;
			}
			const tag = node.tagName.toLowerCase();
			const classes = [...node.classList]
				.filter((name) => name.length < 40 && /^[A-Za-z][\w-]*$/.test(name))
				.slice(0, 2);
			const sameType = node.parentElement
				? [...node.parentElement.children].filter(
						(child) => child.tagName === node.tagName,
					)
				: [node];
			const index = sameType.length > 1 ? `:nth-of-type(${sameType.indexOf(node) + 1})` : "";
			parts.unshift(`${tag}${classes.map((name) => `.${name}`).join("")}${index}`);
			node = node.parentElement;
		}
		return parts.join(" > ");
	};

	const label = (element) =>
		(element.getAttribute("aria-label") ||
			element.textContent ||
			element.getAttribute("alt") ||
			"")
			.replace(/\s+/g, " ")
			.trim()
			.slice(0, 70);

	const report = (type, element, metrics, extra = {}) => {
		const rect = element.getBoundingClientRect();
		issues.push({
			type,
			severity: extra.severity ?? "defect",
			selector: path(element),
			text: label(element),
			rect: { ...RECT(rect), pageY: r1(rect.top + scrollY) },
			metrics,
			...extra,
		});
	};

	const isRendered = (element) => {
		const style = CSS(element);
		if (style.display === "none" || style.visibility === "hidden") return false;
		if (Number(style.opacity) === 0) return false;
		const rect = element.getBoundingClientRect();
		return rect.width > 0 && rect.height > 0;
	};

	const isOverlay = (element) =>
		OVERLAY_SELECTORS.some((selector) => {
			try {
				return element.matches(selector) || element.closest(selector) !== null;
			} catch {
				return false;
			}
		});

	const isOutsideDocument = (element) => {
		const rect = element.getBoundingClientRect();
		const pageTop = rect.top + scrollY;
		return pageTop < -50 || rect.left < -50;
	};

	/**
	 * A laid-out row wider than the frame that clips it is a carousel track, not
	 * a spill: the confirmation page's failure has no such ancestor. Returns the
	 * track's selector, or null.
	 */
	const overflowingTrack = (element) => {
		let node = element.parentElement;
		for (let depth = 0; node && node !== document.documentElement && depth < 8; depth++) {
			const style = CSS(node);
			if (style.overflowX !== "visible") return null;
			if (
				node.scrollWidth - node.clientWidth > 1 &&
				[...node.children].length > 1 &&
				[...node.children].some((child) => {
					const childStyle = CSS(child);
					return childStyle.position !== "absolute" && childStyle.position !== "fixed";
				})
			)
				return path(node);
			node = node.parentElement;
		}
		return null;
	};

	const elements = [...document.body.querySelectorAll("*")];

	// 1. Horizontal content overflow an element does not clip. Innermost only:
	// an ancestor whose overflow comes from a descendant is reported once, at
	// the descendant that actually spills. Severity depends on the consequence:
	// the page scrolling sideways or an ancestor cutting the content off is a
	// defect; content that simply sits outside a smaller box but stays fully
	// visible is a review item.
	for (const element of elements) {
		const style = CSS(element);
		if (style.display === "inline" || style.display === "contents") continue;
		if (style.overflowX !== "visible") continue;
		const overflow = element.scrollWidth - element.clientWidth;
		if (overflow <= 1) continue;
		if (element.clientWidth === 0) continue;
		const childOverflow = [...element.children].some((child) => {
			const childStyle = CSS(child);
			if (childStyle.overflowX !== "visible") return false;
			return child.scrollWidth - child.clientWidth >= overflow - 1;
		});
		if (childOverflow) continue;
		const track = overflowingTrack(element);
		report(
			"overflow-x-visible",
			element,
			{
				scrollWidth: element.scrollWidth,
				clientWidth: element.clientWidth,
				overflowPx: overflow,
				overflowX: style.overflowX,
			},
			track
				? {
						severity: "review",
						note: `inside a laid-out track wider than its clipping frame (${track}); treated as a carousel, not a spill`,
						carousel: track,
					}
				: { note: "content wider than the box, nothing in its own overflow clips it" },
		);
	}

	// 2. Element painted outside a clipping (overflow: hidden|clip) ancestor's
	// visible box. Scrollable ancestors are skipped on purpose: content beyond
	// an auto/scroll container is reachable, not lost.
	const clippingBox = (element) => {
		let node = element.parentElement;
		while (node && node !== document.documentElement) {
			if (isOverlay(node)) return null;
			const style = CSS(node);
			const clipsX = style.overflowX === "hidden" || style.overflowX === "clip";
			const clipsY = style.overflowY === "hidden" || style.overflowY === "clip";
			if (clipsX || clipsY) {
				const rect = node.getBoundingClientRect();
				return {
					node,
					clipsX,
					clipsY,
					left: rect.left + node.clientLeft,
					top: rect.top + node.clientTop,
					width: node.clientWidth,
					height: node.clientHeight,
				};
			}
			node = node.parentElement;
		}
		return null;
	};
	for (const element of elements) {
		const style = CSS(element);
		if (style.position === "fixed") continue;
		if (style.display === "inline" || style.display === "contents") continue;
		if (!isRendered(element)) continue;
		if (isOverlay(element)) continue;
		if (element.ownerSVGElement) continue;
		const box = clippingBox(element);
		if (!box) continue;
		const rect = element.getBoundingClientRect();
		const overflowRight = rect.right - (box.left + box.width);
		const overflowBottom = rect.bottom - (box.top + box.height);
		const outsideX = box.clipsX && overflowRight > 1 ? overflowRight : 0;
		const outsideY = box.clipsY && overflowBottom > 1 ? overflowBottom : 0;
		if (!outsideX && !outsideY) continue;
		const track = overflowingTrack(element);
		report(
			"clipped-by-ancestor",
			element,
			{
				overflowRightPx: r1(Math.max(0, overflowRight)),
				overflowBottomPx: r1(Math.max(0, overflowBottom)),
				clipper: path(box.node),
				clipperOverflow: `${CSS(box.node).overflowX}/${CSS(box.node).overflowY}`,
				clipperBox: {
					x: r1(box.left),
					y: r1(box.top),
					w: r1(box.width),
					h: r1(box.height),
				},
				...(track ? { carousel: track } : {}),
			},
			track
				? {
						severity: "review",
						note: `sits in a track wider than its frame (${track}); a carousel slide, not lost content`,
					}
				: { note: "painted outside a hidden/clip ancestor; the part is unreachable" },
		);
	}

	// 3. The confirmation-page signature: a centring grid container whose child
	// opts out of it with justify-self/align-self. Geometric confirmation is
	// required (child hugs the container's start edge and is smaller than it),
	// so a grid item that simply has `justify-self: start` and fills the row is
	// not reported.
	for (const container of elements) {
		const style = CSS(container);
		if (!/grid/.test(style.display)) continue;
		const justify = style.justifyItems;
		const align = style.alignItems;
		if (justify !== "center" && align !== "center") continue;
		if (isOverlay(container)) continue;
		const box = container.getBoundingClientRect();
		const contentLeft = box.left + container.clientLeft;
		const contentTop = box.top + container.clientTop;
		const contentWidth = container.clientWidth;
		const contentHeight = container.clientHeight;
		if (contentWidth < 2 || contentHeight < 2) continue;
		const items = [...container.children].filter((child) => isRendered(child));
		if (items.length < 2) continue;
		for (const item of items) {
			const itemStyle = CSS(item);
			const rect = item.getBoundingClientRect();
			if (justify === "center") {
				const starts =
					itemStyle.justifySelf === "start" || itemStyle.justifySelf === "left";
				const ends =
					itemStyle.justifySelf === "end" || itemStyle.justifySelf === "right";
				const hug = starts
					? Math.abs(rect.left - contentLeft)
					: Math.abs(contentLeft + contentWidth - rect.right);
				const narrower = contentWidth - rect.width;
				if ((starts || ends) && hug <= 1 && narrower > 8) {
					report(
						"opt-out-of-centering",
						item,
						{
							container: path(container),
							containerJustifyItems: justify,
							containerAlignItems: align,
							itemJustifySelf: itemStyle.justifySelf,
							edgeGapPx: r1(hug),
							widthGapPx: r1(narrower),
						},
						{
							note: `container centres its items; this one hugs the ${
								starts ? "left" : "right"
							} edge`,
						},
					);
				}
			}
			if (
				align === "center" &&
				(itemStyle.alignSelf === "start" || itemStyle.alignSelf === "flex-start")
			) {
				const hugTop = Math.abs(rect.top - contentTop);
				const shorter = contentHeight - rect.height;
				if (hugTop <= 1 && shorter > 8) {
					report(
						"opt-out-of-centering-vertical",
						item,
						{
							container: path(container),
							containerAlignItems: align,
							itemAlignSelf: itemStyle.alignSelf,
							topGapPx: r1(hugTop),
							heightGapPx: r1(shorter),
						},
						{
							severity: "review",
							note: "grid centres items vertically; this one starts at the top edge",
						},
					);
				}
			}
		}
	}

	// 4. Single-line text clipped vertically (its own box is shorter than the
	// line it holds). Screen-reader labels are 1px boxes by design and are
	// excluded, as is anything the sr-only class convention marks.
	for (const element of elements) {
		const style = CSS(element);
		if (element.children.length > 0) continue;
		const text = (element.textContent || "").trim();
		if (text.length < 2) continue;
		if (style.display === "none" || style.visibility === "hidden") continue;
		if (element.matches(SKIP_SR_SELECTOR)) continue;
		if (element.clientWidth <= 1 || element.clientHeight <= 1) continue;
		const clipY = style.overflowY === "hidden" || style.overflowY === "clip";
		const clamp = style.webkitLineClamp;
		const singleLine = style.whiteSpace === "nowrap" || (clamp !== "none" && clamp !== "");
		const verticalCut = element.scrollHeight - element.clientHeight;
		if (singleLine && clipY && verticalCut > 1) {
			report(
				"text-clipped",
				element,
				{
					scrollHeight: element.scrollHeight,
					clientHeight: element.clientHeight,
					cutPx: verticalCut,
					whiteSpace: style.whiteSpace,
					lineClamp: clamp,
					overflowY: style.overflowY,
				},
				{ note: "single-line text box shorter than its line; glyphs are cut" },
			);
		}
	}

	// 5. Interactive elements that are too small for a pointer, or that sit in
	// the tab order while invisible. WCAG 2.2 exceptions are applied: a link
	// that is part of a text flow is skipped, and the standard screen-reader
	// pattern (clip + :focus reveal) is excluded by class convention.
	//
	// `visibility: hidden` is NOT a defect: a hidden element is not focusable
	// and is skipped by the tab order (CSS Display). Only a truly focusable
	// element that renders nothing counts, and only when an ancestor is not
	// merely waiting to be revealed.
	const interactiveSelector =
		'a[href], button, [role="button"], input:not([type="hidden"]), select, textarea, summary, [tabindex]';
	for (const element of document.body.querySelectorAll(interactiveSelector)) {
		if (element.closest("[inert]")) continue;
		if (element.disabled) continue;
		const style = CSS(element);
		if (style.display === "none") continue;
		if (isOverlay(element)) continue;
		if (element.closest("[aria-hidden='true']")) continue;
		const focusable =
			element.tabIndex >= 0 &&
			!element.hasAttribute("disabled") &&
			!element.matches(SKIP_SR_SELECTOR);
		const rect = element.getBoundingClientRect();
		const hiddenAncestor = (() => {
			let node = element;
			while (node && node !== document.body) {
				const nodeStyle = CSS(node);
				if (nodeStyle.visibility === "hidden" || nodeStyle.display === "none")
					return true;
				node = node.parentElement;
			}
			return false;
		})();
		// A collapsed accordion/panel is a legitimate hidden state; the probe
		// cannot tell it apart from a broken tab stop, so it is a review item.
		const collapsedAncestor = (() => {
			let node = element.parentElement;
			while (node && node !== document.body) {
				if (
					node.hasAttribute("hidden") ||
					node.getAttribute("aria-expanded") === "false" ||
					node.getAttribute("aria-hidden") === "true"
				)
					return true;
				node = node.parentElement;
			}
			return false;
		})();
		const invisible =
			Number(style.opacity) === 0 ||
			(rect.width <= 1 && rect.height <= 1) ||
			style.clipPath === "inset(50%)";
		if (focusable && invisible && !hiddenAncestor) {
			report(
				"focusable-invisible",
				element,
				{
					visibility: style.visibility,
					opacity: style.opacity,
					clipPath: style.clipPath,
					tabIndex: element.tabIndex,
					w: r1(rect.width),
					h: r1(rect.height),
					insideCollapsedPanel: collapsedAncestor,
				},
				collapsedAncestor
					? {
							severity: "review",
							note: "focusable but renders nothing inside a collapsed panel",
						}
					: { note: "in the tab order while rendering nothing" },
			);
			continue;
		}
		if (!isRendered(element)) continue;
		if (isOutsideDocument(element)) continue;
		if (element.matches(SKIP_SR_SELECTOR)) continue;
		if (rect.width >= TAP_TARGET && rect.height >= TAP_TARGET) continue;
		// Elements inside a clipping ancestor may be deliberately inset: the
		// painted box is what a pointer can reach, but a parent button with a
		// larger hit area already owns the click.
		const owner = element.parentElement?.closest(interactiveSelector.split(",").join(","));
		if (owner && owner !== element) continue;
		const inlineInText =
			style.display === "inline" &&
			(function parentText() {
				const parent = element.parentElement;
				if (!parent) return false;
				const own = (element.textContent || "").trim().length;
				return (parent.textContent || "").trim().length - own > 20;
			})();
		if (inlineInText) continue;
		report(
			"small-target",
			element,
			{
				w: r1(rect.width),
				h: r1(rect.height),
				min: TAP_TARGET,
				display: style.display,
				position: style.position,
			},
			{ severity: "review", note: "hit area below the 24px pointer target" },
		);
	}

	// 6. Broken media: images that finished loading with no intrinsic size, and
	// font faces the browser marked as errored.
	for (const image of document.images) {
		if (!image.complete) continue;
		if (image.naturalWidth > 0) continue;
		if (!(image.currentSrc || image.getAttribute("src"))) continue;
		const rect = image.getBoundingClientRect();
		if (rect.width === 0 && rect.height === 0) continue;
		report(
			"image-broken",
			image,
			{
				naturalWidth: image.naturalWidth,
				naturalHeight: image.naturalHeight,
				currentSrc: (image.currentSrc || image.src || "").slice(-120),
				w: r1(rect.width),
				h: r1(rect.height),
			},
			{ note: "complete image with no intrinsic width" },
		);
	}
	for (const face of Array.from(document.fonts ?? [])) {
		if (face.status !== "error") continue;
		issues.push({
			type: "font-error",
			severity: "defect",
			selector: `@font-face ${face.family}`,
			text: `${face.weight} ${face.style}`.trim(),
			rect: null,
			metrics: { family: face.family, weight: face.weight, style: face.style },
			note: "document.fonts reports status=error",
		});
	}

	// 7. The document scrolls sideways.
	const docWidth = document.documentElement.scrollWidth;
	const viewWidth = document.documentElement.clientWidth;
	if (docWidth - viewWidth > 1) {
		const offenders = elements
			.filter((element) => {
				const style = CSS(element);
				if (style.position === "fixed" || style.display === "inline") return false;
				if (!isRendered(element) || isOverlay(element)) return false;
				return element.getBoundingClientRect().right - viewWidth > 1;
			})
			.slice(0, 8)
			.map((element) => ({
				selector: path(element),
				rightPx: r1(element.getBoundingClientRect().right),
			}));
		issues.push({
			type: "horizontal-scroll",
			severity: "defect",
			selector: "html",
			text: document.title.slice(0, 70),
			rect: null,
			metrics: { scrollWidth: docWidth, clientWidth: viewWidth, deltaPx: docWidth - viewWidth },
			offenders,
			note: "document wider than the viewport; the page scrolls sideways",
		});
	}

	// 8. Two in-flow sibling blocks painted on top of each other. Layered UI
	// (fixed/absolute/sticky) is excluded: overlap is its purpose. SVG children
	// are excluded too — icon paths intentionally cover their own shapes.
	for (const parent of elements) {
		if (isOverlay(parent)) continue;
		if (parent.ownerSVGElement || parent instanceof SVGElement) continue;
		const children = [...parent.children];
		if (children.length < 2 || children.length > 60) continue;
		const blocks = children.filter((child) => {
			if (child.ownerSVGElement || child instanceof SVGElement) return false;
			const style = CSS(child);
			if (style.display === "none" || style.visibility === "hidden") return false;
			if (style.position !== "static" && style.position !== "relative") return false;
			if (Number(style.opacity) === 0) return false;
			if (isOverlay(child)) return false;
			const rect = child.getBoundingClientRect();
			return rect.width > 4 && rect.height > 4;
		});
		for (let a = 0; a < blocks.length; a++) {
			for (let b = a + 1; b < blocks.length; b++) {
				const one = blocks[a].getBoundingClientRect();
				const two = blocks[b].getBoundingClientRect();
				const overlapX =
					Math.min(one.right, two.right) - Math.max(one.left, two.left);
				const overlapY =
					Math.min(one.bottom, two.bottom) - Math.max(one.top, two.top);
				if (overlapX <= 0 || overlapY <= 0) continue;
				const area = overlapX * overlapY;
				const smaller = Math.min(one.width * one.height, two.width * two.height);
				if (smaller === 0) continue;
				const ratio = area / smaller;
				if (ratio <= 0.4) continue;
				report(
					"overlap",
					blocks[a],
					{
						other: path(blocks[b]),
						overlapRatio: Math.round(ratio * 100) / 100,
						overlapPx: { w: r1(overlapX), h: r1(overlapY) },
					},
					{ note: `overlaps ${path(blocks[b])}` },
				);
			}
		}
	}

	// Keep the report readable: one entry per (type, selector), highest first.
	const seen = new Set();
	const unique = issues.filter((issue) => {
		const key = `${issue.type}|${issue.selector}`;
		if (seen.has(key)) return false;
		seen.add(key);
		return true;
	});

	return {
		url: location.href,
		title: document.title,
		lang: document.documentElement.lang,
		viewport: {
			width: window.innerWidth,
			height: window.innerHeight,
			devicePixelRatio: window.devicePixelRatio,
		},
		document: {
			scrollWidth: docWidth,
			clientWidth: viewWidth,
			scrollHeight: document.documentElement.scrollHeight,
		},
		counts: unique.reduce((total, issue) => {
			total[issue.type] = (total[issue.type] ?? 0) + 1;
			return total;
		}, {}),
		issues: unique,
	};
};
