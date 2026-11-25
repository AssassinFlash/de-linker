(function () {
	const dialog = document.getElementById( 'tv-blog-author-dialog' );
	const trigger = document.querySelector( '.reader-author-cta' );
	if ( ! dialog || ! trigger || typeof dialog.showModal !== 'function' ) {
		return;
	}

	const frame = dialog.querySelector( '.reader-author-dialog-frame' );
	const loading = dialog.querySelector( '.reader-author-dialog-loading' );
	const fallback = dialog.querySelector( '.reader-author-dialog-fallback' );
	let frameSize;
	let timeout;

	function showFallback() {
		clearTimeout( timeout );
		frameSize?.disconnect();
		loading.hidden = true;
		frame.hidden = true;
		fallback.hidden = false;
	}

	frame.addEventListener( 'error', showFallback );
	trigger.setAttribute( 'aria-haspopup', 'dialog' );
	trigger.setAttribute( 'aria-controls', dialog.id );

	trigger.addEventListener( 'click', ( event ) => {
		if ( event.metaKey || event.ctrlKey || event.shiftKey || event.altKey ) {
			return;
		}
		event.preventDefault();
		dialog.showModal();
		if ( ! frame.hasAttribute( 'src' ) ) {
			timeout = setTimeout( showFallback, 10000 );
			frame.src = frame.dataset.src;
		}
	} );

	frame.addEventListener( 'load', () => {
		if ( ! frame.hasAttribute( 'src' ) ) {
			return;
		}
		clearTimeout( timeout );
		const content = frame.contentDocument;
		const form = content?.querySelector( '.linker-article-contact-main' );
		const feedback = form?.querySelector( '.linker-form-error, .linker-form-success' );
		frameSize?.disconnect();
		loading.hidden = true;
		fallback.hidden = !! form;
		frame.hidden = ! form;
		if ( form ) {
			frameSize = new ResizeObserver( () => {
				frame.style.height = Math.ceil( form.getBoundingClientRect().height ) + 'px';
			} );
			frameSize.observe( form );
			content.addEventListener( 'keydown', ( event ) => {
				if ( event.key === 'Escape' ) {
					event.preventDefault();
					dialog.close();
				}
			} );
			if ( feedback && dialog.open ) {
				feedback.tabIndex = -1;
				feedback.focus();
			}
		}
	} );

	dialog.addEventListener( 'close', () => trigger.focus( { preventScroll: true } ) );
})();
