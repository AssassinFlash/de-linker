/* Homepage previews use the published screenshots; each caption opens its live configurator view. */
(() => {
	const section = document.getElementById('configurator-showcase');
	if (!section) return;

	const tablist = section.querySelector('[role="tablist"]');
	const tabs = Array.from(tablist.querySelectorAll('[role="tab"]'));
	const address = section.querySelector('[data-showcase-address]');

	function select(tab) {
		for (const item of tabs) {
			const active = item === tab;
			item.setAttribute('aria-selected', String(active));
			item.tabIndex = active ? 0 : -1;
			document.getElementById(item.getAttribute('aria-controls')).hidden = !active;
		}
		address.textContent = 'de-linker.com' + tab.pathname + tab.search;
		const listBounds = tablist.getBoundingClientRect();
		const tabBounds = tab.getBoundingClientRect();
		if (tabBounds.left < listBounds.left || tabBounds.right > listBounds.right) {
			tablist.scrollLeft += tabBounds.left - listBounds.left;
		}
	}

	for (const [index, tab] of tabs.entries()) {
		tab.addEventListener('click', (event) => {
			if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
			event.preventDefault();
			select(tab);
		});
		tab.addEventListener('keydown', (event) => {
			let next;
			switch (event.key) {
				case 'ArrowRight': next = (index + 1) % tabs.length; break;
				case 'ArrowLeft': next = (index + tabs.length - 1) % tabs.length; break;
				case 'Home': next = 0; break;
				case 'End': next = tabs.length - 1; break;
				case ' ': next = index; break;
				default: return;
			}
			event.preventDefault();
			select(tabs[next]);
			tabs[next].focus({ preventScroll: true });
		});
	}
})();
