/** Keyboard ownership of the existing helper/sheet; workspace keeps page semantics. */
import { useCallback, useEffect, useRef, useState } from '@wordpress/element';

/** Current helper sheet breakpoint in genie.css; the desktop dock is nonmodal. */
const SHEET_WIDTH = 860;
const CONTROLS = 'button, a[href], input, textarea, summary, [tabindex]';
function usable( node: HTMLElement ): boolean {
	// Closed details may retain geometric boxes under the site's popover CSS,
	// but native keyboard navigation only admits their summary.
	const closed = node.closest( 'details:not([open])' );
	if (
		closed &&
		! closed.querySelector( ':scope > summary' )?.contains( node )
	) {
		return false;
	}
	return (
		node.isConnected &&
		! node.matches( ':disabled, [hidden], [tabindex="-1"]' ) &&
		! node.closest( '[hidden], [inert]' ) &&
		node.getClientRects().length > 0
	);
}
export function useHelperDialog( {
	open,
	workspace,
	close,
}: {
	open: boolean;
	workspace: boolean;
	close: () => void;
} ) {
	const panel = useRef< HTMLElement >( null );
	const opener = useRef< HTMLElement | null >( null );
	const opened = useRef( false );
	const currentlyOpen = useRef( open );
	currentlyOpen.current = open;
	const closing = useRef( close );
	closing.current = close;
	const [ mobile, setMobile ] = useState( window.innerWidth <= SHEET_WIDTH );
	const remember = useCallback( ( candidate?: unknown ) => {
		if ( opened.current ) {
			return;
		}
		const active = panel.current?.ownerDocument.activeElement;
		if ( candidate instanceof HTMLElement ) {
			opener.current = candidate;
		} else {
			opener.current = active instanceof HTMLElement ? active : null;
		}
	}, [] );
	useEffect( () => {
		const resize = () => setMobile( window.innerWidth <= SHEET_WIDTH );
		window.addEventListener( 'resize', resize );
		return () => window.removeEventListener( 'resize', resize );
	}, [] );
	useEffect( () => {
		const content = panel.current;
		const root =
			content?.closest< HTMLElement >( '[data-linker-genie-mount]' ) ??
			content;
		if ( workspace || ! open || ! root ) {
			return;
		}
		opened.current = true;
		const attributes = [ 'role', 'aria-modal', 'aria-label' ].map(
			( name ) => ( { name, value: root.getAttribute( name ) } )
		);
		root.setAttribute( 'role', 'dialog' );
		root.setAttribute(
			'aria-label',
			content?.getAttribute( 'aria-label' ) ?? 'Genie'
		);
		if ( mobile ) {
			root.setAttribute( 'aria-modal', 'true' );
		} else {
			root.removeAttribute( 'aria-modal' );
		}
		const overflow = document.body.style.overflow;
		if ( mobile ) {
			document.body.style.overflow = 'hidden';
		}
		const background: { node: HTMLElement; inert: boolean }[] = [];
		if ( mobile ) {
			let branch: HTMLElement = root;
			while ( branch.parentElement ) {
				for ( const sibling of branch.parentElement.children ) {
					if (
						sibling !== branch &&
						sibling instanceof HTMLElement
					) {
						background.push( {
							node: sibling,
							inert: Boolean( sibling.inert ),
						} );
						sibling.inert = true;
					}
				}
				branch = branch.parentElement;
			}
		}
		const controls = () =>
			[ ...root.querySelectorAll< HTMLElement >( CONTROLS ) ].filter(
				usable
			);
		const focusInitial = () => {
			const field = root.querySelector< HTMLTextAreaElement >(
				'.linker-genie-app__input'
			);
			( field && usable( field )
				? field
				: ( controls()[ 0 ] ?? root )
			).focus( { preventScroll: true } );
		};
		const frame = requestAnimationFrame( focusInitial );
		const key = ( event: KeyboardEvent ) => {
			if ( event.defaultPrevented ) {
				return;
			}
			if ( event.key === 'Escape' ) {
				event.preventDefault();
				event.stopPropagation();
				closing.current();
				return;
			}
			if ( ! mobile || event.key !== 'Tab' ) {
				return;
			}
			const items = controls();
			const first = items[ 0 ];
			const last = items.at( -1 );
			if ( ! first || ! last ) {
				event.preventDefault();
				root.focus();
				return;
			}
			if (
				event.shiftKey &&
				( root.ownerDocument.activeElement === first ||
					! root.contains( root.ownerDocument.activeElement ) )
			) {
				event.preventDefault();
				last.focus();
			} else if (
				! event.shiftKey &&
				( root.ownerDocument.activeElement === last ||
					! root.contains( root.ownerDocument.activeElement ) )
			) {
				event.preventDefault();
				first.focus();
			}
		};
		document.addEventListener( 'keydown', key );
		return () => {
			cancelAnimationFrame( frame );
			document.removeEventListener( 'keydown', key );
			background.forEach( ( item ) => {
				if ( item.node.inert ) {
					item.node.inert = item.inert;
				}
			} );
			if ( mobile && document.body.style.overflow === 'hidden' ) {
				document.body.style.overflow = overflow;
			}
			attributes.forEach( ( item ) => {
				if ( item.value === null ) {
					root.removeAttribute( item.name );
				} else {
					root.setAttribute( item.name, item.value );
				}
			} );
			opened.current = false;
			const fallback = document.querySelector< HTMLElement >(
				'.hero-cinematic textarea, #system-search .lk-dialog-prompt, #installer-mobile-query, [data-linker-genie-open]'
			);
			const target =
				opener.current && usable( opener.current )
					? opener.current
					: fallback;
			const active = root.ownerDocument.activeElement;
			if (
				( ! currentlyOpen.current || ! root.isConnected ) &&
				( ! active ||
					active === document.body ||
					root.contains( active ) ) &&
				target &&
				usable( target )
			) {
				target.focus( { preventScroll: true } );
			}
		};
	}, [ open, workspace, mobile ] );
	return { panel, remember, mobile };
}
