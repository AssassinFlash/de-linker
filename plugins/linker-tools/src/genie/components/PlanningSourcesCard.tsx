/** Saved-source facts from the native owner read, independent of model prose. */
import { __, sprintf } from '@wordpress/i18n';
import type {
	PlanningSourcesBlock,
	PlanningSourcesAvailableBlock,
	PageContext,
} from '../api/turn';
import type { GenieConfig } from '../config';

function destination(
	block: PlanningSourcesAvailableBlock,
	links?: GenieConfig[ 'configuratorLinks' ]
): string | null {
	try {
		const url = new URL( block.url, window.location.href );
		const allowed = Object.values( links ?? {} ).some( ( value ) => {
			if ( ! value ) {
				return false;
			}
			const base = new URL( value, window.location.href );
			return url.origin === base.origin && url.pathname === base.pathname;
		} );
		const runs = block.binding.planning_run_ids;
		if (
			! allowed ||
			url.username ||
			url.password ||
			url.hash !== '#lp-calculations' ||
			[ ...url.searchParams.keys() ].some(
				( key ) =>
					! [ 'project', 'run', 'compare' ].includes( key ) ||
					url.searchParams.getAll( key ).length !== 1
			) ||
			url.searchParams.get( 'project' ) !==
				block.binding.planning_project_id ||
			( runs.length === 1
				? url.searchParams.get( 'run' ) !== runs[ 0 ] ||
					url.searchParams.has( 'compare' )
				: runs.length !== 2 ||
					url.searchParams.get( 'compare' ) !== runs.join( ',' ) ||
					url.searchParams.has( 'run' ) )
		) {
			return null;
		}
		return url.href;
	} catch {
		return null;
	}
}

export function PlanningSourcesCard( {
	block,
	configuratorLinks,
	currentPage,
}: {
	block: PlanningSourcesBlock;
	configuratorLinks?: GenieConfig[ 'configuratorLinks' ];
	currentPage?: PageContext;
} ) {
	if ( block.status === 'unavailable' ) {
		return (
			<section className="linker-genie-attachment" role="status">
				<p>
					{ __(
						'The saved calculation details could not be verified for this response.',
						'linker-tools'
					) }
				</p>
			</section>
		);
	}
	const missing = __( 'Not recorded in this saved result', 'linker-tools' );
	const unidentified = __(
		'Not identified in this saved result',
		'linker-tools'
	);
	const href = destination( block, configuratorLinks );
	const previousContext =
		currentPage?.planning_project_id !== undefined &&
		( currentPage.planning_project_id !==
			block.binding.planning_project_id ||
			currentPage.planning_revision !== block.binding.planning_revision ||
			JSON.stringify( currentPage.planning_run_ids ?? [] ) !==
				JSON.stringify( block.binding.planning_run_ids ) );
	return (
		<section
			className="linker-genie-attachment"
			aria-label={ __(
				'Calculation sources and periods',
				'linker-tools'
			) }
		>
			<p className="linker-genie-attachment__title">
				{ __( 'Calculation sources and periods', 'linker-tools' ) }
			</p>
			<p>{ __( 'From the selected saved result.', 'linker-tools' ) }</p>
			{ previousContext && (
				<p>
					{ __(
						'This source card belongs to an earlier response, not the current request.',
						'linker-tools'
					) }
				</p>
			) }
			{ block.results.map( ( result, index ) => (
				<div key={ index }>
					<p>
						{ sprintf(
							// translators: %d is the saved result's project revision.
							__( 'Saved revision %d', 'linker-tools' ),
							result.revision
						) }
					</p>
					{ result.groups.map( ( group, at ) => (
						<div key={ at }>
							{ group.role !== 'selected' && (
								<p>
									{ group.role === 'baseline'
										? __(
												'Baseline calculation',
												'linker-tools'
											)
										: __(
												'Comparison calculation',
												'linker-tools'
											) }
								</p>
							) }
							<dl className="linker-genie-attachment__facts linker-genie-attachment__facts--sources">
								{ group.kind === 'pv' && (
									<>
										<div>
											<dt>
												{ __(
													'PV input to the calculation',
													'linker-tools'
												) }
											</dt>
											<dd>
												{ group.input_quantity
													? {
															pv_available_ac:
																'AC',
															pv_available_dc:
																'DC',
														}[
															group.input_quantity
														]
													: unidentified }
											</dd>
										</div>
										<div>
											<dt>
												{ __(
													'PV source scope',
													'linker-tools'
												) }
											</dt>
											<dd>
												{ group.source_scope
													? {
															whole_reference: __(
																'Whole PV reference',
																'linker-tools'
															),
															selected_dc_group:
																__(
																	'Selected DC group',
																	'linker-tools'
																),
														}[ group.source_scope ]
													: unidentified }
											</dd>
										</div>
										<div>
											<dt>
												{ __(
													'Radiation database',
													'linker-tools'
												) }
											</dt>
											<dd>
												{ group.radiation_database ??
													missing }
											</dd>
										</div>
										<div>
											<dt>
												{ __(
													'Meteorological database',
													'linker-tools'
												) }
											</dt>
											<dd>
												{ group.meteorological_database ??
													missing }
											</dd>
										</div>
										{ Object.hasOwn(
											group,
											'weather_selection_period'
										) && (
											<div>
												<dt>
													{ __(
														'Weather selection period',
														'linker-tools'
													) }
												</dt>
												<dd>
													{ group.weather_selection_period
														? `${ group.weather_selection_period.start_year }–${ group.weather_selection_period.end_year }`
														: missing }
												</dd>
											</div>
										) }
										{ Object.hasOwn(
											group,
											'synthetic_calculation_year'
										) && (
											<div>
												<dt>
													{ __(
														'Synthetic calculation year',
														'linker-tools'
													) }
												</dt>
												<dd>
													{ group.synthetic_calculation_year ??
														missing }
												</dd>
											</div>
										) }
									</>
								) }
								<div>
									<dt>
										{ group.kind === 'pv'
											? __(
													'PV calculation period (UTC)',
													'linker-tools'
												)
											: __(
													'Energy calculation period (UTC)',
													'linker-tools'
												) }
									</dt>
									<dd>
										{ group.periods_utc.length
											? group.periods_utc.map(
													( period, n ) => (
														<div key={ n }>
															{ period ? (
																<>
																	<time
																		dateTime={
																			period.start_utc
																		}
																	>
																		{
																			period.start_utc
																		}
																	</time>
																	{ ' – ' }
																	<time
																		dateTime={
																			period.end_utc
																		}
																	>
																		{
																			period.end_utc
																		}
																	</time>
																</>
															) : (
																missing
															) }
														</div>
													)
												)
											: missing }
									</dd>
								</div>
								<div>
									<dt>
										{ __(
											'Saved project time zone',
											'linker-tools'
										) }
									</dt>
									<dd>{ group.timezone ?? missing }</dd>
								</div>
							</dl>
						</div>
					) ) }
				</div>
			) ) }
			{ href && (
				<a className="linker-genie-app__document" href={ href }>
					{ __( 'Open saved result', 'linker-tools' ) }
				</a>
			) }
		</section>
	);
}
