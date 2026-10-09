<?php
/**
 * Shared part of the plugins' PHPUnit bootstrap, loaded after the plugin's own
 * Composer autoloader: WP_Mock in strict mode, so an unexpected hook or
 * WordPress function call fails the test.
 *
 * @package Linker
 */

declare( strict_types = 1 );

WP_Mock::activateStrictMode();
WP_Mock::bootstrap();
