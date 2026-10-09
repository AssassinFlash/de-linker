<?php
/**
 * Constants PHPStan needs to read the mu-plugins without an instance: the one
 * linker-local writes into an instance's wp-config.php, and WPINC, which
 * wp-settings.php defines and szepeviktor/phpstan-wordpress's bootstrap does not.
 *
 * @package Linker\Local
 */

define( 'LINKER_LOCAL_DIR', '/instance' );
define( 'WPINC', 'wp-includes' ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedConstantFound -- WordPress's own constant.
