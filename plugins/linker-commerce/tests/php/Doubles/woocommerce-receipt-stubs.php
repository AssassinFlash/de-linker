<?php // phpcs:disable WordPress.Files.FileName.InvalidClassFileName,WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedNamespaceFound -- PHPStan reads the native WooCommerce signature.
/**
 * WooCommerce's native order-email verification signature for PHPStan.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Automattic\WooCommerce\Internal\Utilities;

/** WooCommerce order access. */
class Users {
	/**
	 * Whether a receipt reader must verify the order's billing email.
	 *
	 * @param int         $order_id       Native order identity.
	 * @param string|null $supplied_email Email the reader supplied.
	 * @param string      $context        Native order view.
	 */
	public static function should_user_verify_order_email( int $order_id, ?string $supplied_email = null, string $context = 'view' ): bool {}
}
