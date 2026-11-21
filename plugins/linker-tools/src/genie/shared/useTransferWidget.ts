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

/** Mount the shared widget only while an anonymous customer's transfer card is visible. */
export function useTransferWidget( action: Action, visible: boolean ) {
	const container = useRef< HTMLDivElement >( null );
	const token = useRef( '' );
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
			}
		);
		return () => {
			token.current = '';
			dispose?.();
		};
	}, [ action, visible ] );
	return {
		container,
		token,
		refresh: () => {
			if ( visible && container.current ) {
				window.linkerTurnstile?.refresh( container.current );
			}
		},
	};
}
