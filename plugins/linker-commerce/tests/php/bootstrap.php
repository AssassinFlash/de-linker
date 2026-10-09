<?php
/**
 * PHPUnit bootstrap: this plugin's Composer autoloader, then the bootstrap the
 * plugins share.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

require_once dirname( __DIR__, 2 ) . '/vendor/autoload.php';
require_once dirname( __DIR__, 4 ) . '/tools/php/bootstrap.php';
