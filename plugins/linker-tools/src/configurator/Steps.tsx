/**
 * The three screens of the configurator as one ordered list.
 *
 * On a narrow viewport the list sticks under the site header. Its rendered
 * height is not a constant — German labels wrap to a second row — so the
 * list measures itself and publishes that height for the sections'
 * scroll-margin. The sticky rule itself stays in configurator.css.
 */

/**
 * WordPress dependencies
 */
import { useEffect, useRef } from '@wordpress/element';
import { __ } from '@wordpress/i18n';

/** Matches `.linker-steps { top }` in the narrow-viewport sticky rule. */
const STICKY_TOP_PX = 89;

export function Steps( { current }: { current: 1 | 2 | 3 } ) {
	const list = useRef< HTMLOListElement >( null );
	const steps = [
		__( 'Inputs', 'linker-tools' ),
		__( 'Solution', 'linker-tools' ),
		__( 'Design report', 'linker-tools' ),
	];

	useEffect( () => {
		const node = list.current;
		const root = node?.closest( '[data-linker-app="configurator"]' );
		if ( ! node || ! ( root instanceof HTMLElement ) ) {
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
		<ol className="linker-steps" ref={ list }>
			{ steps.map( ( label, index ) => (
				<li
					key={ label }
					className={
						index + 1 <= current
							? 'linker-steps__item is-reached'
							: 'linker-steps__item'
					}
					aria-current={ index + 1 === current ? 'step' : undefined }
				>
					<span className="linker-steps__number" aria-hidden="true">
						{ index + 1 }
					</span>
					{ label }
				</li>
			) ) }
		</ol>
	);
}
