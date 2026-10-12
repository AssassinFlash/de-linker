/**
 * The Solution Configurator: inputs, then the proposed system, then the design report.
 */

/**
 * WordPress dependencies
 */
import { useMemo, useRef, useState } from '@wordpress/element';
import { __ } from '@wordpress/i18n';

/**
 * Internal dependencies
 */
import { engineClient, type EngineClient } from './api/engine';
import { storeClient, type StoreClient } from './api/store';
import { CommercialPanel } from './commercial/CommercialPanel';
import type { Config } from './config';
import { ResidentialPanel } from './residential/ResidentialPanel';
import { Steps } from './Steps';
import { UtilityForm } from './utility/UtilityForm';
import './configurator.css';

export type Segment = 'residential' | 'commercial' | 'utility';

export interface AppProps {
	config: Config;
	/** Clients for tests and stories; the page uses the real endpoints. */
	engine?: EngineClient;
	store?: StoreClient;
	initialSegment?: Segment;
}

export function App( { config, engine, store, initialSegment }: AppProps ) {
	const clients = useMemo(
		() => ( {
			engine: engine ?? engineClient( config.engineUrl ),
			store: store ?? storeClient( config.restUrl ),
		} ),
		[ config, engine, store ]
	);
	const [ segment, setSegment ] = useState< Segment >(
		initialSegment ?? 'residential'
	);
	const tabs = useRef< Record< Segment, HTMLButtonElement | null > >( {
		residential: null,
		commercial: null,
		utility: null,
	} );
	const segments: { id: Segment; label: string }[] = [
		{ id: 'residential', label: __( 'Residential', 'linker-tools' ) },
		{ id: 'commercial', label: __( 'Commercial', 'linker-tools' ) },
		{ id: 'utility', label: __( 'Utility-scale', 'linker-tools' ) },
	];

	function onTabKey( event: React.KeyboardEvent, index: number ) {
		const step = { ArrowRight: 1, ArrowLeft: -1 }[ event.key ];
		if ( ! step ) {
			return;
		}
		const next =
			segments[ ( index + step + segments.length ) % segments.length ];
		setSegment( next.id );
		tabs.current[ next.id ]?.focus();
	}

	return (
		<div className="linker-configurator" lang={ config.locale }>
			<div className="linker-shell">
				<Steps current={ 1 } />
				<div className="linker-stage">
					<header className="linker-configurator__header">
						<h1 className="linker-configurator__title">
							{ __( 'Solution Configurator', 'linker-tools' ) }
						</h1>
						<p className="linker-configurator__lead">
							{ __(
								'Size your system and get the bill of materials.',
								'linker-tools'
							) }
						</p>
					</header>
					<section
						className="linker-block"
						aria-labelledby="linker-project-title"
					>
						<div className="linker-block__head">
							<h2
								className="linker-block__title"
								id="linker-project-title"
							>
								{ __( 'Project type', 'linker-tools' ) }
							</h2>
							<p className="linker-block__step">
								{ __(
									'Step 1 · Which project are you sizing?',
									'linker-tools'
								) }
							</p>
						</div>
						<div
							className="linker-segments"
							role="radiogroup"
							aria-label={ __( 'Project type', 'linker-tools' ) }
						>
							{ segments.map( ( item, index ) => (
								<button
									key={ item.id }
									ref={ ( node ) => {
										tabs.current[ item.id ] = node;
									} }
									type="button"
									role="radio"
									id={ `linker-tab-${ item.id }` }
									aria-checked={ segment === item.id }
									tabIndex={ segment === item.id ? 0 : -1 }
									className="linker-segments__tab"
									onClick={ () => setSegment( item.id ) }
									onKeyDown={ ( event ) =>
										onTabKey( event, index )
									}
								>
									{ item.label }
								</button>
							) ) }
						</div>
					</section>
					<div
						id={ `linker-panel-${ segment }` }
						className="linker-configurator__panel"
					>
						{ segment === 'residential' ? (
							<ResidentialPanel
								config={ config }
								engine={ clients.engine }
								store={ clients.store }
							/>
						) : null }
						{ segment === 'commercial' ? (
							<CommercialPanel
								config={ config }
								engine={ clients.engine }
								store={ clients.store }
							/>
						) : null }
						{ segment === 'utility' ? (
							<UtilityForm config={ config } />
						) : null }
					</div>
				</div>
			</div>
		</div>
	);
}
