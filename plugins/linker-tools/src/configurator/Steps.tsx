/**
 * The three screens as a vertical rail (variant B), not a clickable wizard.
 *
 * On a narrow viewport the shell — rail plus the project-type cards — sticks
 * under the site header, and the steps sit in one row. German labels wrap, so
 * that height is not a constant: the rail measures the shell and publishes it
 * for the sections' scroll-margin. The sticky rule stays in configurator.css.
 */

/**
 * WordPress dependencies
 */
import { useEffect, useRef } from '@wordpress/element';
import { __ } from '@wordpress/i18n';

/** Matches `.linker-shell { top }` in the narrow-viewport sticky rule. */
const STICKY_TOP_PX = 89;

function stepClass( step: number, current: number ): string {
	if ( step === current ) {
		return 'linker-steps__item is-current';
	}
	if ( step < current ) {
		return 'linker-steps__item is-reached';
	}
	return 'linker-steps__item';
}

export function Steps( { current }: { current: 1 | 2 | 3 } ) {
	const rail = useRef< HTMLElement >( null );
	const steps = [
		__( 'Inputs', 'linker-tools' ),
		__( 'Solution', 'linker-tools' ),
		__( 'Design report', 'linker-tools' ),
	];

	useEffect( () => {
		const node = rail.current?.closest( '.linker-shell' );
		const root = rail.current?.closest(
			'[data-linker-app="configurator"]'
		);
		if (
			! ( node instanceof HTMLElement ) ||
			! ( root instanceof HTMLElement )
		) {
			return;
		}
		const publish = () => {
			// The section keeps its own 32px gap below whatever is covering it.
			const offset =
				STICKY_TOP_PX + node.getBoundingClientRect().height + 32;
			root.style.setProperty(
				'--linker-steps-scroll-offset',
				`${ offset }px`
			);
		};
		publish();
		if ( typeof ResizeObserver === 'undefined' ) {
			return;
		}
		const observer = new ResizeObserver( publish );
		observer.observe( node );
		return () => observer.disconnect();
	}, [] );

	return (
		<nav
			className="linker-steps"
			ref={ rail }
			aria-label={ __( 'Configurator', 'linker-tools' ) }
		>
			<p className="linker-steps__cap">
				{ __( 'Configurator', 'linker-tools' ) }
			</p>
			<ol className="linker-steps__list">
				{ steps.map( ( label, index ) => (
					<li
						key={ label }
						className={ stepClass( index + 1, current ) }
						aria-current={
							index + 1 === current ? 'step' : undefined
						}
					>
						<span
							className="linker-steps__number"
							aria-hidden="true"
						>
							{ String( index + 1 ).padStart( 2, '0' ) }
						</span>
						{ label }
					</li>
				) ) }
			</ol>
			<p className="linker-steps__foot">
				{ __(
					'Three steps. The result follows the inputs you enter.',
					'linker-tools'
				) }
			</p>
		</nav>
	);
}
