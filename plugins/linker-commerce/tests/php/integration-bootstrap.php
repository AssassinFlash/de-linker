<?php
/**
 * PHPUnit bootstrap of the integration tests: loads the local WordPress
 * instance named by LINKER_WP_ROOT, after checking that its linker-commerce is
 * this checkout. Notices and deprecations of WordPress and WooCommerce
 * themselves are not turned into failures (phpunit.integration.xml.dist).
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

$linker_commerce_root = getenv( 'LINKER_WP_ROOT' );
if ( ! is_string( $linker_commerce_root ) || ! is_file( $linker_commerce_root . '/wp-load.php' ) ) {
	fwrite( STDERR, "LINKER_WP_ROOT must name the WordPress directory of a local instance (just up), e.g. ~/de-linker-local/a/wordpress.\n" ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_fwrite
	exit( 1 );
}

require_once dirname( __DIR__, 2 ) . '/vendor/autoload.php';

// A CLI request to the instance's front end: no theme, no page output.
define( 'WP_USE_THEMES', false ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedConstantFound -- WordPress's own constant.
// phpcs:disable WordPress.Security.ValidatedSanitizedInput -- defaults for a command-line run, read by WordPress, not by this file.
$_SERVER['HTTP_HOST']   = $_SERVER['HTTP_HOST'] ?? 'localhost';
$_SERVER['REQUEST_URI'] = $_SERVER['REQUEST_URI'] ?? '/';
// phpcs:enable
require_once $linker_commerce_root . '/wp-load.php';

$linker_commerce_installed = realpath( WP_PLUGIN_DIR . '/linker-commerce' );
if ( realpath( dirname( __DIR__, 2 ) ) !== $linker_commerce_installed || ! in_array( 'linker-commerce/linker-commerce.php', (array) get_option( 'active_plugins', array() ), true ) ) {
	fwrite( STDERR, "The instance's linker-commerce must be this checkout and active; it is {$linker_commerce_installed}.\n" ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_fwrite, WordPress.Security.EscapeOutput.OutputNotEscaped
	exit( 1 );
}

// Exercise the real internal SMTP configuration path with the local file-capture mailer.
$linker_commerce_test_outbox = new \Linker\Commerce\Mail\Outbox(
	new \Linker\Commerce\Mail\JobStore(),
	new \Linker\Commerce\Mail\Throttle(),
	new \Linker\Commerce\Mail\TestMode(),
	new \Linker\Commerce\Mail\InternalSmtp( __DIR__ . '/../fixtures/internal-smtp.env' )
);
foreach ( array( 'pre_wp_mail', 'wp_mail_failed', 'wp_mail_succeeded', 'phpmailer_init', \Linker\Commerce\Mail\Outbox::HOOK ) as $linker_commerce_mail_hook ) {
	foreach ( $GLOBALS['wp_filter'][ $linker_commerce_mail_hook ]->callbacks[10] as $linker_commerce_callback ) {
		$linker_commerce_handler = $linker_commerce_callback['function'];
		if ( is_array( $linker_commerce_handler ) && $linker_commerce_handler[0] instanceof \Linker\Commerce\Mail\Outbox ) {
			remove_filter( $linker_commerce_mail_hook, $linker_commerce_handler );
			$linker_commerce_local_handler = array( $linker_commerce_test_outbox, $linker_commerce_handler[1] );
			if ( is_callable( $linker_commerce_local_handler ) ) {
				add_filter( $linker_commerce_mail_hook, $linker_commerce_local_handler, 10, $linker_commerce_callback['accepted_args'] );
			}
		}
	}
}
