import { useEffect, useRef, useState } from '@wordpress/element';
import type { GenieConfig } from '../config';
import {
	type DraftContext,
	pageDraftContext,
	mountPageDraftContext,
} from './draftContext';

/**
 * The mounted surfaces share the page’s native owner and editor.
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
		() => provided ?? pageDraftContext( config )
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
		const release = provided ? undefined : mountPageDraftContext( context );
		return () => {
			unsubscribe();
			release?.();
		};
	}, [ context, provided ] );
	return context;
}
