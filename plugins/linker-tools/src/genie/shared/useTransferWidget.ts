import { useEffect, useRef } from '@wordpress/element';

type Action = 'genie_inquiry' | 'genie_contact';

declare global {
	interface Window {
		linkerTurnstile?: {
			mount: (
				node: HTMLElement,
				action: Action,
				onToken: ( token: string ) => void
			) => () => void;
			refresh: ( node: HTMLElement ) => void;
		};
	}
}

/**
 * Mount the shared widget only while an anonymous customer's transfer card is visible.
 * @param action
 * @param visible
 * @param source
 */
export function useTransferWidget(
	action: Action,
	visible: boolean,
	source: string
) {
	const container = useRef< HTMLDivElement >( null );
	const token = useRef( '' );
	const pending = useRef< ( () => void ) | null >( null );
	useEffect( () => {
		const node = container.current;
		if ( ! visible || ! node ) {
			return;
		}
		const dispose = window.linkerTurnstile?.mount(
			node,
			action,
			( value ) => {
				token.current = value;
				if ( value && pending.current ) {
					const send = pending.current;
					pending.current = null;
					send();
				}
			}
		);
		return () => {
			pending.current = null;
			token.current = '';
			dispose?.();
		};
	}, [ action, visible, source ] );
	return {
		container,
		token,
		wait: ( send: () => void ) => {
			if ( ! window.linkerTurnstile ) {
				return false;
			}
			pending.current = send;
			container.current?.scrollIntoView( { block: 'nearest' } );
			return true;
		},
		cancel: () => {
			pending.current = null;
		},
		refresh: () => {
			if ( visible && container.current ) {
				window.linkerTurnstile?.refresh( container.current );
			}
		},
	};
}
