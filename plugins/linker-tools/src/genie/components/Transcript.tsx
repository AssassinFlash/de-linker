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
	const content = useRef< HTMLDivElement >( null );
	const [ latest, setLatest ] = useState( false );
	const jump = ( settle = false ) => {
		setLatest( false );
		if ( scroll.current ) {
			scroll.current.scrollTop = scroll.current.scrollHeight;
		}
		// The button disappears on activation; settle the explicit jump after
		// that layout update too. Incoming answer growth never calls this.
		if ( ! settle ) {
			return;
		}
		requestAnimationFrame( () => {
			if ( scroll.current ) {
				scroll.current.scrollTop = scroll.current.scrollHeight;
			}
		} );
	};
	useLayoutEffect( () => {
		if ( followKey > 0 ) {
			jump();
		}
	}, [ followKey ] );
	useLayoutEffect( () => {
		const reveal = () => {
			if ( scroll.current ) {
				setLatest(
					scroll.current.scrollHeight -
						scroll.current.clientHeight -
						scroll.current.scrollTop >=
						48
				);
			}
		};
		reveal();
		if ( ! content.current || typeof ResizeObserver === 'undefined' ) {
			return;
		}
		const observer = new ResizeObserver( reveal );
		observer.observe( content.current );
		return () => observer.disconnect();
	} );
	return (
		<div className="linker-genie-reading">
			<div
				className="linker-genie-app__transcript"
				ref={ scroll }
				tabIndex={ 0 }
				onScroll={ () => {
					if ( scroll.current ) {
						// Local 48px affordance: tolerate one line/touch movement.
						setLatest(
							scroll.current.scrollHeight -
								scroll.current.clientHeight -
								scroll.current.scrollTop >=
								48
						);
					}
				} }
			>
				<div
					className="linker-genie-transcript-content"
					ref={ content }
				>
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
