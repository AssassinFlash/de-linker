import { useEffect, useRef, useState } from '@wordpress/element';
import type { GenieConfig } from '../config';
import { DraftContext } from './draftContext';

/**
 * One context per mounted surface, with the native cold lookup shared by both bundles.
 * @param config    The currently mounted native routes and REST nonce.
 * @param onChanged Clear the previous principal's mounted presentation.
 * @param provided  The homepage controller's shared surface context, when present.
 */
export function useDraftContext(
	config: Pick< GenieConfig, 'restUrl' | 'restNonce' >,
	onChanged: () => void,
	provided?: DraftContext
) {
	const changed = useRef( onChanged );
	changed.current = onChanged;
	const [ context ] = useState(
		() => provided ?? new DraftContext( config, () => undefined )
	);
	const [ , render ] = useState( 0 );
	useEffect( () => {
		let previous = context.identity?.scope;
		const unsubscribe = context.subscribe( () => {
			const next = context.identity?.scope;
			if ( previous && next && previous !== next ) {
				changed.current();
			}
			previous = next;
			render( ( value ) => value + 1 );
		} );
		const check = () => {
			void context.verify( true ).catch( () => undefined );
		};
		const checkpoint = () => context.checkpoint();
		const visible = () => {
			if ( document.visibilityState === 'hidden' ) {
				checkpoint();
			}
			if ( document.visibilityState === 'visible' ) {
				check();
			}
		};
		if ( provided ) {
			return unsubscribe;
		}
		void context.verify( false ).catch( () => undefined );
		window.addEventListener( 'focus', check );
		window.addEventListener( 'pageshow', check );
		window.addEventListener( 'pagehide', checkpoint );
		window.addEventListener( 'linker-genie-identity-change', check );
		document.addEventListener( 'visibilitychange', visible );
		return () => {
			unsubscribe();
			context.dispose();
			window.removeEventListener( 'focus', check );
			window.removeEventListener( 'pageshow', check );
			window.removeEventListener( 'pagehide', checkpoint );
			window.removeEventListener( 'linker-genie-identity-change', check );
			document.removeEventListener( 'visibilitychange', visible );
		};
	}, [ context, provided ] );
	return context;
}
