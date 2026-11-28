for (const form of document.querySelectorAll('form[data-linker-contact-shell="1"]')) {
	const nonce = form.elements.namedItem('linker_contact_nonce');
	const requestId = form.elements.namedItem('linker_request_id');
	const alert = form.querySelector('[data-contact-session-error]');
	let pending;
	let submitting = false;

	function hydrate() {
		if (nonce.value && requestId.value) return Promise.resolve(true);
		if (!pending) {
			pending = fetch(form.dataset.linkerContactSessionUrl, {
				method: 'POST', credentials: 'same-origin', cache: 'no-store',
			}).then(async response => {
				if (!response.ok) throw new Error('contact session');
				const data = await response.json();
				if (!data.nonce || !data.requestId) throw new Error('contact fields');
				nonce.value ||= data.nonce;
				requestId.value ||= data.requestId;
				form.dataset.linkerContactReady = '1';
				alert.hidden = true;
				return true;
			}).catch(() => {
				alert.hidden = false;
				return false;
			}).finally(() => { pending = undefined; });
		}
		return pending;
	}

	for (const event of ['focusin', 'pointerdown', 'input']) {
		form.addEventListener(event, hydrate);
	}
	form.addEventListener('submit', async event => {
		if (form.dataset.linkerContactReady === '1' && nonce.value && requestId.value) return;
		event.preventDefault();
		event.stopImmediatePropagation();
		if (submitting) return;
		submitting = true;
		const ready = await hydrate();
		submitting = false;
		if (ready) form.requestSubmit(event.submitter ?? undefined);
	}, true);
}
