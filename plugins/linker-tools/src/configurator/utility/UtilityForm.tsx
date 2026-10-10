/**
 * Utility-scale projects are quoted per project: an inquiry form that opens
 * an e-mail to the team with the details filled in.
 */

/**
 * WordPress dependencies
 */
import { useState } from '@wordpress/element';
import { __ } from '@wordpress/i18n';

/**
 * Internal dependencies
 */
import type { Config } from '../config';

// Company and service questions go to the team address (owner ruling,
// AGENTS.md section 2, 2026-10-05).
export const TEAM_EMAIL = 'sales@de-linker.com';

export function inquiryLink(
	fields: [ string, string ][],
	subject: string
): string {
	const body = fields
		.filter( ( [ , value ] ) => value.trim() )
		.map( ( [ label, value ] ) => `${ label }: ${ value.trim() }` )
		.join( '\n' );
	return `mailto:${ TEAM_EMAIL }?subject=${ encodeURIComponent( subject ) }&body=${ encodeURIComponent( body ) }`;
}

export function UtilityForm( { config }: { config: Config } ) {
	const [ values, setValues ] = useState( {
		site: '',
		power: '',
		energy: '',
		grid: '',
		timeline: '',
		message: '',
	} );
	const labels = {
		site: __( 'Site (postcode or place)', 'linker-tools' ),
		power: __( 'Power (MW)', 'linker-tools' ),
		energy: __( 'Storage capacity (MWh)', 'linker-tools' ),
		grid: __( 'Grid connection', 'linker-tools' ),
		timeline: __( 'Planned commissioning', 'linker-tools' ),
		message: __( 'Project details', 'linker-tools' ),
	};
	const subject = __( 'Utility-scale storage inquiry', 'linker-tools' );
	const link = inquiryLink(
		( Object.keys( labels ) as ( keyof typeof labels )[] ).map( ( key ) => [
			labels[ key ],
			values[ key ],
		] ),
		subject
	);
	return (
		<section
			className="linker-section"
			aria-labelledby="linker-utility-title"
			lang={ config.locale }
		>
			<h2 className="linker-section__title" id="linker-utility-title">
				{ __( 'Utility-scale inquiry', 'linker-tools' ) }
			</h2>
			<p className="linker-section__note">
				{ __(
					'We quote utility-scale storage per project. Describe the project and our team replies within one business day.',
					'linker-tools'
				) }
			</p>
			<div className="linker-form">
				<div className="linker-form__grid">
					{ (
						Object.keys( labels ) as ( keyof typeof labels )[]
					 ).map( ( key ) => (
						<div className="linker-field" key={ key }>
							<label
								className="linker-field__label"
								htmlFor={ `linker-utility-${ key }` }
							>
								{ labels[ key ] }
							</label>
							{ key === 'message' ? (
								<textarea
									id={ `linker-utility-${ key }` }
									rows={ 4 }
									value={ values[ key ] }
									onChange={ ( event ) =>
										setValues( {
											...values,
											[ key ]: event.target.value,
										} )
									}
								/>
							) : (
								<input
									id={ `linker-utility-${ key }` }
									value={ values[ key ] }
									onChange={ ( event ) =>
										setValues( {
											...values,
											[ key ]: event.target.value,
										} )
									}
								/>
							) }
						</div>
					) ) }
				</div>
				<div className="linker-form__submit">
					<a
						className="linker-button linker-button--primary"
						href={ link }
					>
						{ __( 'Write to our team', 'linker-tools' ) }
					</a>
					<p className="linker-field__hint">{ TEAM_EMAIL }</p>
				</div>
			</div>
		</section>
	);
}
