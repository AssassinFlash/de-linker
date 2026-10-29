import { useEffect, useState } from "react";
import type { RefObject } from "react";

/** The planner hides inactive workspaces with `hidden`/`inert` and keeps them
 * mounted, so a GPU surface has to notice that its own tree is no longer
 * displayed. Returns true while the host sits inside such a subtree. */
export function useHiddenAncestor(
	host: RefObject<HTMLElement | null>,
): boolean {
	const [hidden, setHidden] = useState(false);
	useEffect(() => {
		const element = host.current;
		if (!element) return;
		const read = () => !!element.closest("[hidden], [inert]");
		setHidden(read());
		const observer = new MutationObserver(() => setHidden(read()));
		for (
			let parent = element.parentElement;
			parent;
			parent = parent.parentElement
		) {
			observer.observe(parent, {
				attributes: true,
				attributeFilter: ["hidden", "inert"],
			});
			if (parent.hasAttribute("data-linker-planner")) break;
		}
		return () => observer.disconnect();
	}, [host]);
	return hidden;
}
