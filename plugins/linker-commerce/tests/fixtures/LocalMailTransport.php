<?php
/**
 * Local SMTP configuration for WordPress's file-capture mailer.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Fixtures;

/** The real Outbox routing and mailer hooks deliver only to the local sink. */
final class LocalMailTransport {
	/**
	 * Install after loading the isolated instance.
	 *
	 * @throws \RuntimeException Outside the local file-capture environment.
	 */
	public static function install(): void {
		if ( ! defined( 'LINKER_LOCAL_MAIL_DIR' ) || 'local' !== wp_get_environment_type() ) {
			throw new \RuntimeException( 'The local mail sink is required.' );
		}
		$outbox = new \Linker\Commerce\Mail\Outbox(
			new \Linker\Commerce\Mail\JobStore(),
			new \Linker\Commerce\Mail\Throttle(),
			new \Linker\Commerce\Mail\TestMode(),
			new \Linker\Commerce\Mail\InternalSmtp( __DIR__ . '/internal-smtp.env' )
		);
		foreach ( array( 'pre_wp_mail', 'wp_mail_failed', 'wp_mail_succeeded', 'phpmailer_init', \Linker\Commerce\Mail\Outbox::HOOK ) as $name ) {
			foreach ( $GLOBALS['wp_filter'][ $name ]->callbacks[10] as $callback ) {
				$handler = $callback['function'];
				if ( is_array( $handler ) && $handler[0] instanceof \Linker\Commerce\Mail\Outbox ) {
					remove_filter( $name, $handler );
					$local = array( $outbox, $handler[1] );
					if ( is_callable( $local ) ) {
						add_filter( $name, $local, 10, $callback['accepted_args'] );
					}
				}
			}
		}
	}
}
