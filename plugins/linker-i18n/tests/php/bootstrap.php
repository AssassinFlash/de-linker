<?php
/**
 * PHPUnit bootstrap: Composer autoloader and WP_Mock in strict mode, so an
 * unexpected hook or WordPress function call fails the test.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

require_once dirname( __DIR__, 2 ) . '/vendor/autoload.php';

WP_Mock::activateStrictMode();
WP_Mock::bootstrap();
