/**
 * Phone shortcuts to the existing, expanded sections — not a second wizard.
 * No calculation, candidate selection or handoff rule lives here.
 */

/**
 * WordPress dependencies
 */
import { useEffect, useRef, useState } from '@wordpress/element';
import { __ } from '@wordpress/i18n';

export interface MobileStep {
	id: string;
	label: string;
}

export function MobileNavigation( { steps }: { steps: MobileStep[] } ) {
	const [ current, setCurrent ] = useState( steps[ 0 ].id );
	const [ visible, setVisible ] = useState( true );
	const navigation = useRef< HTMLElement >( null );
	useEffect( () => {
		const node = navigation.current;
		const app = node?.closest( '.linker-configurator' );
		if ( ! node || ! ( app instanceof HTMLElement ) ) {
			return;
		}
		const reserve = () =>
			app.style.setProperty(
				'--linker-mobile-nav-height',
				`${ Math.ceil( node.getBoundingClientRect().height ) }px`
			);
		reserve();
		const observer =
			typeof ResizeObserver !== 'undefined'
				? new ResizeObserver( reserve )
				: null;
		observer?.observe( node );
		return () => {
			observer?.disconnect();
			app.style.removeProperty( '--linker-mobile-nav-height' );
		};
	}, [] );
	function scrollTo( id: string ) {
		document.getElementById( id )?.scrollIntoView( {
			block: 'start',
			behavior: 'smooth',
		} );
	}
	useEffect( () => {
		const update = () => {
			// Match the clearance already published by Steps for section scrolling.
			const root = document.querySelector(
				'[data-linker-app="configurator"]'
			);
			const clearance = root
				? parseFloat(
						getComputedStyle( root ).getPropertyValue(
							'--linker-steps-scroll-offset'
						)
					) || 0
				: 0;
			let active = steps[ 0 ].id;
			for ( const step of steps ) {
				const section = document.getElementById( step.id );
				if (
					section &&
					section.getBoundingClientRect().top <= clearance + 1
				) {
					active = step.id;
				}
			}
			setCurrent( active );
			const app = root?.getBoundingClientRect();
			setVisible(
				! app ||
					( app.bottom > window.innerHeight &&
						app.top < window.innerHeight )
			);
		};
		update();
		window.addEventListener( 'scroll', update, { passive: true } );
		window.addEventListener( 'resize', update );
		return () => {
			window.removeEventListener( 'scroll', update );
			window.removeEventListener( 'resize', update );
		};
	}, [ steps ] );

	return (
		<nav
			className="linker-mobile-nav"
			ref={ navigation }
			hidden={ ! visible }
			aria-label={ __( 'Configurator navigation', 'linker-tools' ) }
		>
			{ steps.map( ( step, index ) => (
				<button
					key={ step.id }
					type="button"
					className="linker-mobile-nav__step"
					aria-current={ current === step.id ? 'step' : undefined }
					onClick={ () => scrollTo( step.id ) }
				>
					<span
						aria-hidden="true"
						className="linker-mobile-nav__number"
					>
						{ String( index + 1 ).padStart( 2, '0' ) }
					</span>
					<span>{ step.label }</span>
				</button>
			) ) }
		</nav>
	);
}
