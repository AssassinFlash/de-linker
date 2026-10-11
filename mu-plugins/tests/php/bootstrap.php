<?php
/**
 * PHPUnit bootstrap: what wp-settings.php defines before a must-use plugin
 * loads, then the plugin itself.
 *
 * @package Linker\Mu
 */

declare( strict_types = 1 );

// phpcs:disable WordPress.WP.AlternativeFunctions, WordPress.PHP.NoSilencedErrors.Discouraged, WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedConstantFound -- a test bootstrap runs outside WordPress: it builds its temporary instance directory with PHP itself and defines WordPress's own constants.

require_once dirname( __DIR__, 2 ) . '/vendor/autoload.php';

// The constants the recorder reads; a temporary wp-content, so that including
// the plugin (which starts the recorder) never touches a real installation.
define( 'ABSPATH', sys_get_temp_dir() . '/linker-mu-test-instance/' );
define( 'WP_CONTENT_DIR', ABSPATH . 'wp-content' );
@mkdir( WP_CONTENT_DIR, 0755, true );

require_once dirname( __DIR__, 2 ) . '/linker-error-recorder.php';
