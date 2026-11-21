import { connectForms, createWidgets } from './widget';

const config = window.linkerTurnstileConfig;
if ( config ) {
	const widgets = createWidgets( config );
	window.linkerTurnstile = widgets;
	connectForms( document, widgets );
	document.addEventListener( 'linker:inquiry-form-mounted', ( event ) => {
		if ( event.target instanceof HTMLFormElement ) {
			connectForms( event.target, widgets );
		}
	} );
}
