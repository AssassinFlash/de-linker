<?php
/** Render the actual native email without transport or mail logging.
 *
 * @package Linker\Commerce
 */
declare(strict_types=1);
namespace Linker\Commerce\Mail;

use WC_Email;
/** Shared capture keeps the native locale, template, routing and sender filters. */
final class Capture {
	/**
	 * @param WC_Email        $email Actual native producer.
	 * @param callable():void $render Native rendering. */
	public static function run( WC_Email $email, callable $render ): ?Message {
		$message = null;
		$capture = static function ( $pre, array $atts ) use ( &$message ) {
			if ( null === $pre ) {
				$message = Message::from_wp_mail( $atts );
			}return true;
		};
		$logging = static fn( bool $enabled, string $id, WC_Email $current ): bool=>$current === $email ? false : $enabled;
		add_filter( 'woocommerce_email_log_enabled', $logging, 10, 3 );
		add_filter( 'pre_wp_mail', $capture, 9, 2 );
		try {
			$render();
		} finally {
			remove_filter( 'pre_wp_mail', $capture, 9 );
			remove_filter( 'woocommerce_email_log_enabled', $logging, 10 );}
		return $message;
	}
}
