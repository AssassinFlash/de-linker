/**
 * The files picked for the next turn (#236): each is prepared as it is
 * picked (prepare.ts), shown over the composer, and sent with the turn.
 *
 * One state for every composer that takes files: the dock and the home
 * page's hero (#232) use the same hook, so a photo is turned into the same
 * JPEG and refused for the same reasons wherever it is picked.
 */

/**
 * WordPress dependencies
 */
import { useCallback, useRef, useState } from '@wordpress/element';

/**
 * Internal dependencies
 */
import {
	MAX_FILES,
	MAX_TURN_BYTES,
	prepare,
	type Refusal,
	type Upload,
} from './prepare';

/** Why a pick is not sent: a file's refusal, or the turn's own limits. */
export type PickRefusal = Refusal | 'count' | 'turn_size';

export interface Picked {
	key: number;
	name: string;
	state: 'preparing' | 'ready' | 'refused';
	upload?: Upload;
	bytes?: number;
	reason?: PickRefusal;
}

export interface Attachments {
	picked: Picked[];
	/** The files ready to send. */
	uploads: Upload[];
	/** A file is still being prepared: the send waits for it. */
	busy: boolean;
	add: ( files: ArrayLike< File > ) => void;
	remove: ( key: number ) => void;
	clear: () => void;
	/** Puts a failed turn's files back over the composer. */
	restore: ( uploads: Upload[] ) => void;
}

let nextKey = 1;

export function useAttachments(): Attachments {
	const [ picked, setPicked ] = useState< Picked[] >( [] );
	// The picks as of the last change, for a burst of picks in one render.
	const current = useRef< Picked[] >( [] );
	const update = useCallback( ( change: ( items: Picked[] ) => Picked[] ) => {
		current.current = change( current.current );
		setPicked( current.current );
	}, [] );

	const add = useCallback(
		( files: ArrayLike< File > ) => {
			for ( const file of Array.from( files ) ) {
				const key = nextKey++;
				const kept = current.current.filter(
					( item ) => item.state !== 'refused'
				).length;
				if ( kept >= MAX_FILES ) {
					update( ( items ) => [
						...items,
						{
							key,
							name: file.name,
							state: 'refused',
							reason: 'count',
						},
					] );
					continue;
				}
				update( ( items ) => [
					...items,
					{ key, name: file.name, state: 'preparing' },
				] );
				void prepare( file ).then( ( result ) =>
					update( ( items ) =>
						withTurnLimit(
							items.map( ( item ) => {
								if ( item.key !== key ) {
									return item;
								}
								return result.ok
									? {
											...item,
											name: result.upload.name,
											state: 'ready',
											upload: result.upload,
											bytes: result.bytes,
										}
									: {
											...item,
											state: 'refused',
											reason: result.reason,
										};
							} )
						)
					)
				);
			}
		},
		[ update ]
	);

	const remove = useCallback(
		( key: number ) =>
			update( ( items ) =>
				withTurnLimit( items.filter( ( item ) => item.key !== key ) )
			),
		[ update ]
	);
	const clear = useCallback( () => update( () => [] ), [ update ] );
	const restore = useCallback(
		( uploads: Upload[] ) =>
			update( () =>
				withTurnLimit(
					uploads.map( ( upload ) => ( {
						key: nextKey++,
						name: upload.name,
						state: 'ready' as const,
						upload,
						bytes: decodedBytes( upload.data ),
					} ) )
				)
			),
		[ update ]
	);

	return {
		picked,
		uploads: picked
			.filter( ( item ) => item.state === 'ready' && item.upload )
			.map( ( item ) => item.upload as Upload ),
		busy: picked.some( ( item ) => item.state === 'preparing' ),
		add,
		remove,
		clear,
		restore,
	};
}

/**
 * The decoded size of a base64 payload, so a restored file meets the same
 * turn limit as the file that was picked.
 *
 * @param data Base64, without a data-URL prefix.
 */
function decodedBytes( data: string ): number {
	let padding = 0;
	if ( data.endsWith( '==' ) ) {
		padding = 2;
	} else if ( data.endsWith( '=' ) ) {
		padding = 1;
	}
	return Math.max( 0, Math.floor( ( data.length * 3 ) / 4 ) - padding );
}

/**
 * The picks with the turn's byte limit applied: a file that would take the
 * turn past MAX_TURN_BYTES is refused, in the order picked.
 *
 * @param items The picks.
 */
export function withTurnLimit( items: Picked[] ): Picked[] {
	let total = 0;
	return items.map( ( item ) => {
		if ( item.state === 'refused' && item.reason !== 'turn_size' ) {
			return item;
		}
		if ( item.state === 'refused' && item.upload ) {
			// A file refused for the turn's size may fit again after a removal.
			item = { ...item, state: 'ready', reason: undefined };
		}
		if ( item.state !== 'ready' ) {
			return item;
		}
		total += item.bytes ?? 0;
		return total > MAX_TURN_BYTES
			? { ...item, state: 'refused', reason: 'turn_size' }
			: item;
	} );
}
