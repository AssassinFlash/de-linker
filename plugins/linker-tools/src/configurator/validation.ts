/**
 * Form validation from the engine's own request schemas (./schema, exported
 * from the Pydantic models by services/engine/scripts/export_schemas.py), so
 * an input rule exists once. Errors come back per field, worded here.
 */

/**
 * External dependencies
 */
import Ajv, { type ErrorObject } from 'ajv';
import type { FieldErrors, FieldValues, Resolver } from 'react-hook-form';

/**
 * WordPress dependencies
 */
import { __, sprintf } from '@wordpress/i18n';

/**
 * Internal dependencies
 */
import { formatNumber } from './format';
import type { Locale } from './types';

const ajv = new Ajv( { allErrors: true, strict: false } );

function field( error: ErrorObject ): string {
	if ( error.keyword === 'required' ) {
		return String( error.params.missingProperty );
	}
	return error.instancePath.replace( /^\//, '' ).split( '/' )[ 0 ] || 'form';
}

export function message( error: ErrorObject, locale: Locale ): string {
	const limit = () => formatNumber( Number( error.params.limit ), locale );
	switch ( error.keyword ) {
		case 'required':
			return __( 'Please fill in this field.', 'linker-tools' );
		case 'pattern':
			return __(
				'Enter a German postcode with five digits.',
				'linker-tools'
			);
		case 'minimum':
			return sprintf(
				/* translators: %s: smallest allowed value */
				__( 'Enter at least %s.', 'linker-tools' ),
				limit()
			);
		case 'exclusiveMinimum':
			return sprintf(
				/* translators: %s: value the input must exceed */
				__( 'Enter more than %s.', 'linker-tools' ),
				limit()
			);
		case 'maximum':
		case 'exclusiveMaximum':
			return sprintf(
				/* translators: %s: largest allowed value */
				__( 'Enter at most %s.', 'linker-tools' ),
				limit()
			);
		case 'type':
			return __( 'Enter a number.', 'linker-tools' );
		default:
			return __( 'Check this value.', 'linker-tools' );
	}
}

/**
 * A react-hook-form resolver: `toInput` turns the form into the request body,
 * the schema decides, the messages name the field.
 *
 * @param schema  JSON Schema of the request body.
 * @param toInput Maps the form values to the body the engine expects.
 * @param locale  Language of the number formatting in messages.
 */
export function schemaResolver< Form extends FieldValues >(
	schema: object,
	toInput: ( values: Form ) => unknown,
	locale: Locale
): Resolver< Form > {
	const validate = ajv.compile( schema );
	return async ( values ) => {
		if ( validate( toInput( values ) ) ) {
			return { values, errors: {} };
		}
		const errors: Record< string, { type: string; message: string } > = {};
		for ( const error of validate.errors ?? [] ) {
			const name = field( error );
			if ( ! errors[ name ] ) {
				errors[ name ] = {
					type: error.keyword,
					message: message( error, locale ),
				};
			}
		}
		return { values: {}, errors: errors as FieldErrors< Form > };
	};
}
