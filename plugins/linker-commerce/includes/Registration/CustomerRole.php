<?php
/**
 * What kind of business a customer is.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Registration;

/**
 * The customer's business type, asked at registration: installer, EPC
 * contractor or distributor (docs/specs/11-commerce.md, journey step 2; the
 * site's customers, AGENTS.md §1).
 */
final class CustomerRole {

	/**
	 * Customer meta holding the business type.
	 */
	public const META = 'linker_customer_role';

	/**
	 * The business types by key.
	 *
	 * @return array<string, string>
	 */
	public static function options(): array {
		return array(
			'installer'   => __( 'Installer', 'linker-commerce' ),
			'epc'         => __( 'EPC contractor', 'linker-commerce' ),
			'distributor' => __( 'Distributor', 'linker-commerce' ),
		);
	}

	/**
	 * The name of a stored business type, '' for none.
	 *
	 * @param string $key Stored key.
	 */
	public static function label( string $key ): string {
		return self::options()[ $key ] ?? '';
	}
}
