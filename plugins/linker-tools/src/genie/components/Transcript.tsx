/** Keep the reading position as a long answer grows (Genie spec goal 9). */
import { useLayoutEffect, useRef, useState } from '@wordpress/element';
import type { ReactNode } from 'react';
import { __ } from '@wordpress/i18n';

export function Transcript( {
	children,
	followKey,
}: {
	children: ReactNode;
	followKey: number;
} ) {
	const scroll = useRef< HTMLDivElement >( null );
	const previousTop = useRef( 0 );
	const [ latest, setLatest ] = useState( false );
	const jump = ( settle = false ) => {
		setLatest( false );
		if ( scroll.current ) {
			scroll.current.scrollTop = scroll.current.scrollHeight;
			previousTop.current = scroll.current.scrollTop;
		}
		// The button disappears on activation; settle the explicit jump after
		// that layout update too. Incoming answer growth never calls this.
		if ( ! settle ) {
			return;
		}
		requestAnimationFrame( () => {
			if ( scroll.current ) {
				scroll.current.scrollTop = scroll.current.scrollHeight;
				previousTop.current = scroll.current.scrollTop;
			}
		} );
	};
	useLayoutEffect( () => {
		if ( followKey > 0 ) {
			jump();
		}
	}, [ followKey ] );

	return (
		<div className="linker-genie-reading">
			<div
				className="linker-genie-app__transcript"
				ref={ scroll }
				tabIndex={ 0 }
				onScroll={ () => {
					const el = scroll.current;
					if ( ! el ) return;
					const gap =
						el.scrollHeight - el.clientHeight - el.scrollTop;
					if ( gap <= 160 ) setLatest( false );
					else if ( el.scrollTop < previousTop.current )
						setLatest( true );
					previousTop.current = el.scrollTop;
				} }
			>
				<div className="linker-genie-transcript-content">
					{ children }
				</div>
			</div>
			<div className="linker-genie-reading-controls">
				{ latest ? (
					<button
						type="button"
						className="linker-genie-jump"
						onClick={ () => jump( true ) }
					>
						<svg
							viewBox="0 0 24 24"
							width="18"
							height="18"
							fill="none"
							stroke="currentColor"
							strokeWidth="1.65"
							strokeLinecap="round"
							strokeLinejoin="round"
							aria-hidden="true"
						>
							<path d="M12 4v16m-6-6 6 6 6-6" />
						</svg>
						<span className="screen-reader-text">
							{ __( 'Jump to latest', 'linker-tools' ) }
						</span>
					</button>
				) : null }
			</div>
		</div>
	);
}
