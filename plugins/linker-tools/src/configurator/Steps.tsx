/**
 * The three screens of the configurator as one ordered list.
 */

/**
 * WordPress dependencies
 */
import { __ } from '@wordpress/i18n';

export function Steps( { current }: { current: 1 | 2 | 3 } ) {
	const steps = [
		__( 'Inputs', 'linker-tools' ),
		__( 'Solution', 'linker-tools' ),
		__( 'Design report', 'linker-tools' ),
	];
	return (
		<ol className="linker-steps">
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
