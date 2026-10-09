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

// WordPress is not loaded: the REST controller's parent class is a stand-in.
if ( ! class_exists( 'WP_REST_Controller' ) ) {
	class_alias( Linker\Commerce\Tests\Support\RestControllerDouble::class, 'WP_REST_Controller' );
}
