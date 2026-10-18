/** Local presentation of an already complete answer; never a transport stream. */
import { useEffect, useRef, useState } from '@wordpress/element';
import { __ } from '@wordpress/i18n';
import { MessageBody } from './MessageBody';

function motionAllowed(): boolean {
	return (
		typeof window.matchMedia === 'function' &&
		! window.matchMedia( '(prefers-reduced-motion: reduce)' ).matches
	);
}

export function Reply( {
	text,
	animate = false,
	onComplete,
	locale = 'en',
}: {
	text: string;
	animate?: boolean;
	onComplete?: () => void;
	locale?: 'en' | 'de';
} ) {
	const [ progress, setProgress ] = useState(
		animate && motionAllowed() ? 0 : 1
	);
	const skipped = useRef( false );
	useEffect( () => {
		if ( ! animate || ! motionAllowed() ) {
			setProgress( 1 );
			return;
		}
		setProgress( 0 );
		skipped.current = false;
		// Local design choice: cap the reveal at 1.2s. It must not add a long
		// artificial wait after the backend has already delivered the answer.
		const duration = Math.min(
			1200,
			Math.max( 300, Array.from( text ).length * 3 )
		);
		const started = performance.now();
		let frame = 0;
		const tick = ( now: number ) => {
			if ( skipped.current ) {
				return;
			}
			const next = Math.min( 1, ( now - started ) / duration );
			setProgress( next );
			if ( next < 1 ) {
				frame = requestAnimationFrame( tick );
			}
		};
		frame = requestAnimationFrame( tick );
		return () => cancelAnimationFrame( frame );
	}, [ text, animate ] );
	const revealing = progress < 1;
	useEffect( () => {
		if ( animate && ! revealing ) {
			onComplete?.();
		}
	}, [ animate, revealing, onComplete ] );
	return (
		<div className="linker-genie-reply">
			{ revealing ? (
				<div className="screen-reader-text">
					<MessageBody text={ text } locale={ locale } />
				</div>
			) : null }
			<div
				aria-hidden={ revealing || undefined }
				data-testid="reply-reveal"
			>
				<MessageBody
					text={ text }
					progress={ progress }
					locale={ locale }
				/>
			</div>
			{ revealing ? (
				<button
					type="button"
					className="linker-genie-reply__show"
					onClick={ () => {
						skipped.current = true;
						setProgress( 1 );
					} }
				>
					{ __( 'Show full response', 'linker-tools' ) }
				</button>
			) : null }
		</div>
	);
}
