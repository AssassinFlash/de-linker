<?php
/**
 * The registration form's grouped country select.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Registration;

/**
 * Renders `billing_country` through WooCommerce's own field pipeline with its
 * documented `woocommerce_form_field_{type}` extension point. The grouped
 * order is the owner's (#224): Germany, the rest of the EU, then every other
 * country. WooCommerce's selectWoo script makes the select searchable
 * (assets/account-ui.js initializes it).
 */
final class CountryField {

	/**
	 * The field type registered in Fields::fields().
	 */
	public const TYPE = 'linker_country';

	/**
	 * The registration country field's markup; every other field is untouched.
	 *
	 * @param string               $field The field HTML so far ('' for this type).
	 * @param string               $key   Field name.
	 * @param array<string, mixed> $args  Field arguments after WooCommerce's own.
	 * @param mixed                $value Current value.
	 */
	public function render( $field, $key, $args, $value ): string {
		if ( 'billing_country' !== $key ) {
			return (string) $field;
		}
		$id       = (string) ( $args['id'] ?? $key );
		$classes  = array_map( 'strval', (array) ( $args['class'] ?? array() ) );
		$input    = array_map( 'strval', (array) ( $args['input_class'] ?? array() ) );
		$input[]  = 'linker-country-select';
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
		$attributes = array(
			'name'  => $key,
			'id'    => $id,
			'class' => implode( ' ', $input ),
		);
		if ( $required ) {
			// The card's client check keys on aria-required; the native
			// attribute is the same rule in browsers without that script.
			$attributes['required']      = 'required';
			$attributes['aria-required'] = 'true';
		}
		foreach ( (array) ( $args['custom_attributes'] ?? array() ) as $attribute => $attribute_value ) {
			$attributes[ (string) $attribute ] = (string) $attribute_value;
		}
		$html  = '<p class="form-row ' . esc_attr( implode( ' ', $classes ) ) . '" id="' . esc_attr( $id ) . '_field">';
		$html .= '<label for="' . esc_attr( $id ) . '" class="' . esc_attr( implode( ' ', (array) ( $args['label_class'] ?? array() ) ) ) . '">' . esc_html( $label ) . $indicators . '</label>';
		$html .= '<span class="woocommerce-input-wrapper"><select';
		foreach ( $attributes as $attribute => $attribute_value ) {
			$html .= ' ' . esc_attr( $attribute ) . '="' . esc_attr( $attribute_value ) . '"';
		}
		$html  .= '>';
		$groups = CountryOptions::groups();
		$html  .= $this->group( __( 'Europe', 'linker-commerce' ), $groups['europe'], (string) $value );
		$html  .= $this->group( __( 'Other countries', 'linker-commerce' ), $groups['rest'], (string) $value );
		$html  .= '</select></span></p>';
		return $html;
	}

	/**
	 * One optgroup with its options.
	 *
	 * @param string                $label Group label.
	 * @param array<string, string> $items Country code → name.
	 * @param string                $value Selected country code.
	 */
	private function group( string $label, array $items, string $value ): string {
		if ( array() === $items ) {
			return '';
		}
		$html = '<optgroup label="' . esc_attr( $label ) . '">';
		foreach ( $items as $code => $name ) {
			$html .= '<option value="' . esc_attr( $code ) . '"' . selected( $value, $code, false ) . '>' . esc_html( $name ) . '</option>';
		}
		return $html . '</optgroup>';
	}
}
