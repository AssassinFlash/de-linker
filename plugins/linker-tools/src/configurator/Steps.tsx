/**
 * The three screens as a vertical rail (variant B), not a clickable wizard.
 *
 * On a narrow viewport only this rail sticks under the site header, and the
 * steps sit in one row. German labels wrap, so that height is not a constant:
 * the rail measures itself and publishes it for the sections' scroll-margin.
 * The shell must not be the sticky element — it contains the section the
 * margin is meant to clear. The sticky rule stays in configurator.css.
 */

/**
 * WordPress dependencies
 */
import { useEffect, useRef } from '@wordpress/element';
import { __ } from '@wordpress/i18n';

/** Matches `.linker-steps { top }` in the narrow-viewport sticky rule. */
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
		const node = rail.current;
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
			// Ceil: Chromium applies scroll-margin a fraction short of a
			// subpixel sum, which would leave the title under the bar.
			const offset = Math.ceil(
				STICKY_TOP_PX + node.getBoundingClientRect().height + 32
			);
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
						<span className="linker-steps__label">{ label }</span>
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
