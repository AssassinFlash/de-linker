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
			const index =
				sameType.length > 1
					? `:nth-of-type(${sameType.indexOf(node) + 1})`
					: "";
			parts.unshift(
				`${tag}${classes.map((name) => `.${name}`).join("")}${index}`,
			);
			node = node.parentElement;
		}
		return parts.join(" > ");
	};

	const label = (element) =>
		(
			element.getAttribute("aria-label") ||
			element.textContent ||
			element.getAttribute("alt") ||
			""
		)
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
	 * Chrome's closed <details> keeps its children laid out below the summary,
	 * clipped by the disclosure's own overflow (measured live on a product
	 * page: 49px closed with a 310px body, 359px once opened). That is a
	 * hidden state the user opens, not lost content, so painted-geometry
	 * rules skip everything inside a closed disclosure.
	 */
	const inClosedDetails = (element) =>
		element.closest("details:not([open])") !== null;

	/**
	 * The frame that would contain a horizontal track: an ancestor clipping
	 * the X axis. A Y-only clipper does not turn an X spill into a carousel.
	 * Depth bound 8 matches the probe's other ancestor walks: a track and its
	 * frame live within one component.
	 */
	const xClippingFrame = (node) => {
		let parent = node.parentElement;
		for (
			let depth = 0;
			parent && parent !== document.documentElement && depth < 8;
			depth++
		) {
			const style = CSS(parent);
			if (style.overflowX === "hidden" || style.overflowX === "clip")
				return parent;
			parent = parent.parentElement;
		}
		return null;
	};

	/**
	 * The horizontal overflow comes from a row of laid-out items running past
	 * the frame's right edge: two non-inline in-flow siblings side by side,
	 * at least one beyond the frame. Measured shapes: the home gallery's
	 * photo buttons and the stories' cards qualify; the product feature
	 * band's stacked copy column (one over-wide headline) does not. The 300
	 * descendant cap bounds the walk to one component's subtree (the largest
	 * measured track, the home stories, holds ~160 nodes).
	 */
	const rowRunsPastFrame = (node, frame) => {
		const frameRight = frame.getBoundingClientRect().right;
		const descendants = node.querySelectorAll("*");
		const cap = Math.min(descendants.length, 300);
		for (let i = 0; i < cap; i++) {
			const el = descendants[i];
			const prev = el.previousElementSibling;
			if (!prev) continue;
			const se = CSS(el);
			const sp = CSS(prev);
			if (se.display === "none" || sp.display === "none") continue;
			if (se.display === "inline" || sp.display === "inline") continue;
			if (
				se.position === "absolute" ||
				se.position === "fixed" ||
				sp.position === "absolute" ||
				sp.position === "fixed"
			)
				continue;
			const re = el.getBoundingClientRect();
			const rp = prev.getBoundingClientRect();
			const vOverlap =
				Math.min(re.bottom, rp.bottom) - Math.max(re.top, rp.top);
			const hOverlap =
				Math.min(re.right, rp.right) - Math.max(re.left, rp.left);
			if (hOverlap > 0) continue;
			if (vOverlap <= Math.min(re.height, rp.height) / 2) continue;
			if (Math.max(re.right, rp.right) > frameRight + 1) return true;
		}
		return false;
	};

	/**
	 * A laid-out row wider than the frame that clips it is a carousel track,
	 * not a spill: the confirmation page's failure has no such frame. The
	 * track only counts when an X-clipping ancestor frames it and a row of
	 * items runs past that frame; otherwise the spill stays a defect.
	 * Returns the track's selector, or null.
	 */
	const isLaidOutTrack = (node) => {
		const style = CSS(node);
		if (style.overflowX !== "visible") return false;
		if (node.scrollWidth - node.clientWidth <= 1) return false;
		if ([...node.children].length <= 1) return false;
		const frame = xClippingFrame(node);
		if (!frame) return false;
		return rowRunsPastFrame(node, frame);
	};

	const overflowingTrack = (element) => {
		if (isLaidOutTrack(element)) return path(element);
		let node = element.parentElement;
		for (
			let depth = 0;
			node && node !== document.documentElement && depth < 8;
			depth++
		) {
			if (isLaidOutTrack(node)) return path(node);
			if (CSS(node).overflowX !== "visible") return null;
			node = node.parentElement;
		}
		return null;
	};

	const elements = [...document.body.querySelectorAll("*")];

	// 1. Horizontal content overflow an element does not clip itself. Innermost
	// only: an ancestor whose overflow comes from a descendant is reported
	// once, at the descendant that actually spills. Severity follows the
	// consequence, measured on the pages that shaped the rule: a spill no
	// clipper contains stays visible and is a defect (the product feature
	// band's headline jutting over the panel); a spill an ancestor actually
	// cuts is truncation — a review item when the cutting box is a slide in a
	// horizontal row or the content is a row of slides (the home gallery's
	// caption boxes, the stories' cards), a defect when plain content is cut
	// (the confirmation page's lost CTA).
	const contentRight = (element) =>
		element.getBoundingClientRect().left + element.scrollWidth;
	const cuttingClipper = (element) => {
		const right = contentRight(element);
		let node = element.parentElement;
		while (node && node !== document.documentElement) {
			if (isOverlay(node)) return null;
			const style = CSS(node);
			if (style.overflowX === "auto" || style.overflowX === "scroll")
				return { node, reachable: true };
			if (style.overflowX === "hidden" || style.overflowX === "clip") {
				const rect = node.getBoundingClientRect();
				if (
					style.position === "absolute" &&
					rect.width <= 1 &&
					rect.height <= 1
				)
					return null;
				if (rect.right < right - 1) return { node, reachable: false };
				return null;
			}
			node = node.parentElement;
		}
		return null;
	};
	const sideBySide = (a, b) => {
		const ra = a.getBoundingClientRect();
		const rb = b.getBoundingClientRect();
		const vOverlap = Math.min(ra.bottom, rb.bottom) - Math.max(ra.top, rb.top);
		const hOverlap = Math.min(ra.right, rb.right) - Math.max(ra.left, rb.left);
		return hOverlap <= 0 && vOverlap > Math.min(ra.height, rb.height) / 2;
	};
	const inRowWithSiblings = (node) => {
		if (!node.parentElement) return false;
		return [...node.parentElement.children].some(
			(sibling) => sibling !== node && sideBySide(sibling, node),
		);
	};
	/** Nearest ancestor that is itself a slide: in a horizontal row with its
	 * siblings. Everything inside it is slider content, cut or not (the home
	 * gallery's English captions are cut by their 59px slide, the German ones
	 * only spill inside it — same design, same verdict). Depth 8 matches the
	 * probe's other ancestor walks. */
	const rowAncestor = (element) => {
		let node = element.parentElement;
		for (let depth = 0; node && depth < 8; depth++) {
			if (inRowWithSiblings(node)) return node;
			node = node.parentElement;
		}
		return null;
	};
	for (const element of elements) {
		const style = CSS(element);
		if (style.display === "inline" || style.display === "contents") continue;
		if (style.overflowX !== "visible") continue;
		if (inClosedDetails(element)) continue;
		const overflow = element.scrollWidth - element.clientWidth;
		if (overflow <= 1) continue;
		if (element.clientWidth === 0) continue;
		const childOverflow = [...element.children].some((child) => {
			const childStyle = CSS(child);
			if (childStyle.overflowX !== "visible") return false;
			return child.scrollWidth - child.clientWidth >= overflow - 1;
		});
		if (childOverflow) continue;
		const cut = cuttingClipper(element);
		if (cut?.reachable) continue;
		const slide = rowAncestor(element);
		if (slide || (cut && rowRunsPastFrame(element, cut.node))) {
			report(
				"overflow-x-visible",
				element,
				{
					scrollWidth: element.scrollWidth,
					clientWidth: element.clientWidth,
					overflowPx: overflow,
					overflowX: style.overflowX,
					...(cut ? { clipper: path(cut.node) } : {}),
					...(slide ? { slide: path(slide) } : {}),
				},
				{
					severity: "review",
					note: `slider content (${slide ? `inside slide ${path(slide)}` : `a row of items past ${path(cut.node)}`}); verdict follows the design`,
				},
			);
			continue;
		}
		report(
			"overflow-x-visible",
			element,
			{
				scrollWidth: element.scrollWidth,
				clientWidth: element.clientWidth,
				overflowPx: overflow,
				overflowX: style.overflowX,
				...(cut ? { clipper: path(cut.node) } : {}),
			},
			cut
				? {
						note: `cut by a clipping ancestor (${path(cut.node)}); the content is lost`,
					}
				: {
						note: "content wider than the box and no clip contains it; the spill is visible",
					},
		);
	}

	// 2. Element painted outside a clipping (overflow: hidden|clip) ancestor's
	// visible box. Scrollability is handled per axis: content beyond an
	// auto/scroll ancestor is reachable on that axis and never reported, while
	// the other axis may still be clipped and lost.
	const clippingBox = (element) => {
		let reachableX = false;
		let reachableY = false;
		let node = element.parentElement;
		while (node && node !== document.documentElement) {
			if (isOverlay(node)) return null;
			const style = CSS(node);
			const clipsX = style.overflowX === "hidden" || style.overflowX === "clip";
			const clipsY = style.overflowY === "hidden" || style.overflowY === "clip";
			if (clipsX || clipsY) {
				const rect = node.getBoundingClientRect();
				// The sr-only clip convention is a 1px absolute box (see rule 4's
				// SKIP_SR_SELECTOR); its "clipping" is the pattern, not a defect.
				if (
					style.position === "absolute" &&
					rect.width <= 1 &&
					rect.height <= 1
				)
					return null;
				return {
					node,
					clipsX: clipsX && !reachableX,
					clipsY: clipsY && !reachableY,
					left: rect.left + node.clientLeft,
					top: rect.top + node.clientTop,
					width: node.clientWidth,
					height: node.clientHeight,
				};
			}
			// An auto/scroll axis only reaches content when it really
			// overflows (the spec also computes the other axis to auto when
			// just one is set, so check the actual scroll extent, not the
			// computed value alone).
			if (
				(style.overflowX === "auto" || style.overflowX === "scroll") &&
				node.scrollWidth - node.clientWidth > 1
			)
				reachableX = true;
			if (
				(style.overflowY === "auto" || style.overflowY === "scroll") &&
				node.scrollHeight - node.clientHeight > 1
			)
				reachableY = true;
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
		if (inClosedDetails(element)) continue;
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
				: {
						note: "painted outside a hidden/clip ancestor; the part is unreachable",
					},
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
		if (inClosedDetails(container)) continue;
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
				(itemStyle.alignSelf === "start" ||
					itemStyle.alignSelf === "flex-start")
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
		if (inClosedDetails(element)) continue;
		if (element.clientWidth <= 1 || element.clientHeight <= 1) continue;
		const clipY = style.overflowY === "hidden" || style.overflowY === "clip";
		const clamp = style.webkitLineClamp;
		const singleLine =
			style.whiteSpace === "nowrap" || (clamp !== "none" && clamp !== "");
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
		// A closed disclosure's controls are neither visible nor tab stops
		// until it opens (see inClosedDetails).
		if (inClosedDetails(element)) continue;
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
		const owner = element.parentElement?.closest(
			interactiveSelector.split(",").join(","),
		);
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
				if (style.position === "fixed" || style.display === "inline")
					return false;
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
			metrics: {
				scrollWidth: docWidth,
				clientWidth: viewWidth,
				deltaPx: docWidth - viewWidth,
			},
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
			if (style.display === "none" || style.visibility === "hidden")
				return false;
			if (style.position !== "static" && style.position !== "relative")
				return false;
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
				const smaller = Math.min(
					one.width * one.height,
					two.width * two.height,
				);
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
