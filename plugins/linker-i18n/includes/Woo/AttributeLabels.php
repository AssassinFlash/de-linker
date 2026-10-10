<?php
/**
 * Product attribute names through gettext.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Woo;

/**
 * Gives the product attribute names a translation through this plugin's
 * .po files: WooCommerce stores one label per attribute and has no
 * translation for it (docs/research/2026-10-09/i18n-opensource-replication.md §3.2).
 */
final class AttributeLabels {

	/**
	 * The label in the current language (filter `woocommerce_attribute_label`).
	 *
	 * @param mixed $label Attribute label.
	 * @return mixed
	 */
	public function label( $label ) {
		if ( ! is_string( $label ) ) {
			return $label;
		}
		return $this->labels()[ $label ] ?? $label;
	}

	/**
	 * The attribute labels of the live shop on 2026-10-09 (wc/v3/products/attributes).
	 *
	 * @return array<string, string> English label => label in the current language.
	 */
	private function labels(): array {
		return array(
			'Application'                => __( 'Application', 'linker-i18n' ),
			'Battery voltage'            => __( 'Battery voltage', 'linker-i18n' ),
			'Brand'                      => __( 'Brand', 'linker-i18n' ),
			'Installation type'          => __( 'Installation type', 'linker-i18n' ),
			'Model'                      => __( 'Model', 'linker-i18n' ),
			'Monitoring / communication' => __( 'Monitoring / communication', 'linker-i18n' ),
			'Phase'                      => __( 'Phase', 'linker-i18n' ),
			'Power range'                => __( 'Power range', 'linker-i18n' ),
			'Product family'             => __( 'Product family', 'linker-i18n' ),
			'Series'                     => __( 'Series', 'linker-i18n' ),
		);
	}
}
