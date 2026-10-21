/** Measure the actual visible composer node after mount, opening, width and font changes. */
import {
	useCallback,
	useLayoutEffect,
	useRef,
	useState,
} from '@wordpress/element';

/** Existing composer contract: at most six 24px lines, then scroll. */
const LINE_HEIGHT = 24;
const MAX_HEIGHT = 6 * LINE_HEIGHT;

export function useComposerSize( value: string, visible: boolean ) {
	const field = useRef< HTMLTextAreaElement | null >( null );
	const [ node, setNode ] = useState< HTMLTextAreaElement | null >( null );
	const observer = useRef< ResizeObserver | null >( null );
	const ref = useCallback( ( next: HTMLTextAreaElement | null ) => {
		// Disconnect synchronously when React removes/replaces this particular field.
		observer.current?.disconnect();
		observer.current = null;
		field.current = next;
		setNode( next );
	}, [] );
	const measure = useCallback( () => {
		const current = field.current;
		if (
			! current ||
			! visible ||
			current.getBoundingClientRect().width === 0
		) {
			return;
		}
		current.style.height = `${ LINE_HEIGHT }px`;
		const natural = Math.max( current.scrollHeight, LINE_HEIGHT );
		current.style.height = `${ Math.min( natural, MAX_HEIGHT ) }px`;
		current.style.overflowY = natural > MAX_HEIGHT ? 'auto' : 'hidden';
	}, [ visible ] );
	useLayoutEffect( () => {
		measure();
	}, [ value, node, measure ] );
	useLayoutEffect( () => {
		if ( ! node ) {
			return;
		}
		let active = true;
		let width = node.getBoundingClientRect().width;
		if ( typeof ResizeObserver !== 'undefined' ) {
			const watching = new ResizeObserver( () => {
				if ( ! active || field.current !== node ) {
					return;
				}
				const next = node.getBoundingClientRect().width;
				if ( next !== width ) {
					width = next;
					measure();
				}
			} );
			observer.current = watching;
			watching.observe( node );
		}
		const fonts = node.ownerDocument.fonts;
		const fontsReady = () => {
			if ( active && field.current === node ) {
				measure();
			}
		};
		void fonts?.ready.then( fontsReady );
		fonts?.addEventListener( 'loadingdone', fontsReady );
		return () => {
			active = false;
			observer.current?.disconnect();
			observer.current = null;
			fonts?.removeEventListener( 'loadingdone', fontsReady );
		};
	}, [ node, measure ] );
	return { field, ref };
}
