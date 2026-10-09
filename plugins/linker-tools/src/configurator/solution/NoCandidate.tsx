/**
 * No system qualifies: which rules excluded the inverters and what to relax.
 */

/**
 * WordPress dependencies
 */
import { __, _n, sprintf } from '@wordpress/i18n';

/**
 * Internal dependencies
 */
import type { ResidentialResult } from '../types';

export function NoCandidate( {
	result,
	onBack,
}: {
	result: ResidentialResult;
	onBack: () => void;
} ) {
	const counts = new Map< string, { label: string; count: number } >();
	for ( const excluded of result.candidates.excluded ) {
		for ( const rule of excluded.failed ) {
			const entry = counts.get( rule.id ) ?? {
				label: rule.label,
				count: 0,
			};
			entry.count += 1;
			counts.set( rule.id, entry );
		}
	}
	const reasons = [ ...counts.values() ].sort(
		( a, b ) => b.count - a.count
	);
	return (
		<div className="linker-empty linker-empty--none">
			<h3>
				{ __(
					'No system in our range meets every rule',
					'linker-tools'
				) }
			</h3>
			{ result.warnings.length > 0 ? (
				<ul className="linker-notes">
					{ result.warnings.map( ( warning ) => (
						<li key={ warning }>{ warning }</li>
					) ) }
				</ul>
			) : null }
			{ reasons.length > 0 ? (
				<>
					<p>
						{ __(
							'Rules that excluded the inverters:',
							'linker-tools'
						) }
					</p>
					<ul className="linker-reasons">
						{ reasons.map( ( reason ) => (
							<li key={ reason.label }>
								{ reason.label }{ ' ' }
								<span className="linker-reasons__count">
									{ sprintf(
										/* translators: %d: number of inverters */
										_n(
											'%d inverter',
											'%d inverters',
											reason.count,
											'linker-tools'
										),
										reason.count
									) }
								</span>
							</li>
						) ) }
					</ul>
				</>
			) : null }
			{ result.relaxations.length > 0 ? (
				<>
					<p>
						{ __(
							'What would change the result:',
							'linker-tools'
						) }
					</p>
					<ul className="linker-relaxations">
						{ result.relaxations.map( ( relaxation ) => (
							<li key={ relaxation }>{ relaxation }</li>
						) ) }
					</ul>
				</>
			) : null }
			<button
				type="button"
				className="linker-button linker-button--secondary"
				onClick={ onBack }
			>
				{ __( 'Change the inputs', 'linker-tools' ) }
			</button>
		</div>
	);
}
