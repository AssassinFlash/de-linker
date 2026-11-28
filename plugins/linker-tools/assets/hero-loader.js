( () => {
	const hero = document.querySelector( '.hero-cinematic' );
	const config = document.querySelector( '[data-linker-hero-loader]' );
	if ( ! hero || ! config || ! window.linkerLoadGenieEntry ) {
		return;
	}

	const entry = JSON.parse( config.textContent );
	const controls = '.hero-send, .hero-capsule, [data-linker-assistant-open]';
	let pending;
	let loading = false;
	let ready = false;
	function fail() {
		loading = false;
		const target = pending;
		pending = null;
		if ( target?.href ) {
			window.location.assign( target.href );
		}
	}
	function boot() {
		if ( ! ready && ! loading ) {
			loading = true;
			window.linkerLoadGenieEntry( entry ).catch( fail );
		}
	}
	for ( const type of [ 'focusin', 'pointerdown', 'input' ] ) {
		hero.addEventListener( type, ( event ) => {
			if ( event.target.matches( '.hero-prompt' ) ) {
				boot();
			}
		} );
	}
	hero.addEventListener( 'click', ( event ) => {
		const target = event.target.closest( controls );
		if (
			ready ||
			! target ||
			event.ctrlKey ||
			event.metaKey ||
			event.shiftKey ||
			event.altKey
		) {
			return;
		}
		event.preventDefault();
		pending = target;
		boot();
	} );
	hero.addEventListener( 'keydown', ( event ) => {
		if (
			ready ||
			event.key !== 'Enter' ||
			event.shiftKey ||
			event.isComposing ||
			event.keyCode === 229 ||
			! event.target.matches( '.hero-prompt' )
		) {
			return;
		}
		event.preventDefault();
		pending = hero.querySelector( '.hero-send' );
		boot();
	} );
	window.addEventListener(
		'linker-genie-hero-ready',
		() => {
			ready = true;
			pending?.click();
			pending = null;
		},
		{ once: true }
	);
} )();
