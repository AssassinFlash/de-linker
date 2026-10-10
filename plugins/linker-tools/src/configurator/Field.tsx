/**
 * A labelled form field with an optional unit, hint and error, wired for
 * screen readers (the error is announced and linked to the input).
 */

/**
 * External dependencies
 */
import type { ReactElement } from 'react';

/**
 * WordPress dependencies
 */
import { cloneElement } from '@wordpress/element';

export interface FieldProps {
	id: string;
	label: string;
	unit?: string;
	hint?: string;
	error?: string;
	children: ReactElement< Record< string, unknown > >;
}

export function Field( {
	id,
	label,
	unit,
	hint,
	error,
	children,
}: FieldProps ) {
	const described = [
		hint ? `${ id }-hint` : '',
		error ? `${ id }-error` : '',
	]
		.filter( Boolean )
		.join( ' ' );
	const control = cloneElement( children, {
		'aria-invalid': error ? true : undefined,
		'aria-describedby':
			[ children.props[ 'aria-describedby' ], described ]
				.filter( Boolean )
				.join( ' ' ) || undefined,
	} );
	return (
		<div
			className={ `linker-field${ error ? ' linker-field--error' : '' }` }
		>
			<label className="linker-field__label" htmlFor={ id }>
				{ label }
				{ unit ? (
					<span className="linker-sr-only">{ ` (${ unit })` }</span>
				) : null }
			</label>
			<div className="linker-field__control">
				{ control }
				{ unit ? (
					<span className="linker-field__unit" aria-hidden="true">
						{ unit }
					</span>
				) : null }
			</div>
			{ hint ? (
				<p className="linker-field__hint" id={ `${ id }-hint` }>
					{ hint }
				</p>
			) : null }
			<p
				className="linker-field__error"
				id={ `${ id }-error` }
				role="alert"
			>
				{ error ?? '' }
			</p>
		</div>
	);
}
