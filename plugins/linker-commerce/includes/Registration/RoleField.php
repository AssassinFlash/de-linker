<?php
/**
 * The registration form's business-type radios.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Registration;

/**
 * Renders the business type through WooCommerce's own field pipeline with its
 * documented `woocommerce_form_field_{type}` extension point, the way the
 * grouped country select does (CountryField). Each native input is nested
 * inside its option label (#351), so auth.css can overlay the whole pill
 * with the input and the input itself — focusable, clickable, its checked
 * state announced — is the pill's hit area. WooCommerce's own radio markup
 * keeps the input a sibling of the label, which the pill design could only
 * dress by hiding the input off pointer events; the nesting is the
 * configurator's established pattern for its choice cards
 * (plugins/linker-tools/src/configurator/residential/ResidentialForm.tsx and
 * configurator.css, .linker-form__choice label).
 */
final class RoleField {

	/**
	 * The field type registered in Fields::fields().
	 */
	public const TYPE = 'linker_role';

	/**
	 * The business type's markup; every other field is untouched.
	 *
	 * @param string               $field The field HTML so far ('' for this type).
	 * @param string               $key   Field name.
	 * @param array<string, mixed> $args  Field arguments after WooCommerce's own.
	 * @param mixed                $value Current value.
	 */
	public function render( $field, $key, $args, $value ): string {
		if ( CustomerRole::META !== $key ) {
			return (string) $field;
		}
		$id       = (string) ( $args['id'] ?? $key );
		$classes  = array_map( 'strval', (array) ( $args['class'] ?? array() ) );
		$input    = array_map( 'strval', (array) ( $args['input_class'] ?? array() ) );
		$labels   = array_map( 'strval', (array) ( $args['label_class'] ?? array() ) );
		$label    = (string) ( $args['label'] ?? '' );
		$required = ! empty( $args['required'] );
		if ( $required ) {
			$indicators = '&nbsp;<span class="required" aria-hidden="true">*</span>';
			if ( ! in_array( 'validate-required', $classes, true ) ) {
				$classes[] = 'validate-required';
			}
		} else {
			// phpcs:ignore WordPress.WP.I18n.TextDomainMismatch -- WooCommerce's own optional marker, kept in its text domain.
			$indicators = '&nbsp;<span class="optional">(' . esc_html__( 'optional', 'woocommerce' ) . ')</span>';
		}
		$attributes = array();
		foreach ( (array) ( $args['custom_attributes'] ?? array() ) as $attribute => $attribute_value ) {
			$attributes[ (string) $attribute ] = (string) $attribute_value;
		}
		if ( $required ) {
			// WooCommerce puts aria-required on each radio input of a required
			// group; the client check of the card reads it there.
			$attributes += array( 'aria-required' => 'true' );
		}
		$options  = CustomerRole::options();
		$first_id = $id . '_' . (string) array_key_first( $options );
		$html     = '<p class="form-row ' . esc_attr( implode( ' ', $classes ) ) . '" id="' . esc_attr( $id ) . '_field">';
		$html    .= '<label for="' . esc_attr( $first_id ) . '" class="' . esc_attr( implode( ' ', $labels ) ) . '">' . esc_html( $label ) . $indicators . '</label>';
		$html    .= '<span class="woocommerce-input-wrapper">';
		foreach ( $options as $option_key => $option_text ) {
			$option_id = $id . '_' . (string) $option_key;
			$html     .= '<label for="' . esc_attr( $option_id ) . '" class="radio' . ( $labels ? ' ' . esc_attr( implode( ' ', $labels ) ) : '' ) . '">';
			$html     .= '<input type="radio" class="input-radio' . ( $input ? ' ' . esc_attr( implode( ' ', $input ) ) : '' ) . '" value="' . esc_attr( (string) $option_key ) . '" name="' . esc_attr( $key ) . '"';
			foreach ( $attributes as $attribute => $attribute_value ) {
				$html .= ' ' . esc_attr( (string) $attribute ) . '="' . esc_attr( $attribute_value ) . '"';
			}
			$html .= ' id="' . esc_attr( $option_id ) . '"' . checked( $value, $option_key, false ) . ' />';
			$html .= esc_html( (string) $option_text );
			$html .= '</label>';
		}
		$html .= '</span></p>';
		return $html;
	}
}
