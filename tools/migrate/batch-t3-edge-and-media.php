<?php
/**
 * Publish the T3 edge rules, security contact, page styles and image derivatives.
 *
 * Usage: wp eval-file batch-t3-edge-and-media.php snapshot > before-t3.json
 * wp eval-file batch-t3-edge-and-media.php apply|restore before-t3.json
 * wp eval-file batch-t3-edge-and-media.php apply before-t3.json domain
 *
 * @package Linker\Migrate
 */

namespace Linker\Commerce\Migrate\T3;

use Linker\I18n\Jobs;
use Linker\I18n\Languages;
use Linker\I18n\LinkLocalizer;
use Linker\I18n\Twins;
use Linker\I18n\Translation\{Aligner, DeepSeekClient, Fields, HtmlTokenizer, Planner, Rules, Segmenter, State, Translator, Validator};
use Linker\I18n\Woo\Projection;
use Linker\Commerce\Migrate\T3Pages;
use RuntimeException;
use WP_CLI;

if ( ! defined( 'WP_CLI' ) || ! WP_CLI ) {
	return;
}

require_once __DIR__ . '/batch-t3-pages.php';
require_once __DIR__ . '/batch-t3-media.php';

const DYNAMIC = <<<'RULE'
<IfModule mod_rewrite.c>
RewriteEngine On
RewriteCond %{REQUEST_FILENAME} !-f
RewriteRule ^ - [E=no-brotli:1]
</IfModule>
RULE;
const DOMAIN  = <<<'RULE'
<IfModule LiteSpeed>
SetEnv no-brotli 1
</IfModule>
RULE;
const BEGIN   = '# BEGIN Linker edge compression and headers';
const END     = '# END Linker edge compression and headers';
const HEADERS = <<<'RULE'
<IfModule mod_headers.c>
Header always unset X-Powered-By
Header unset X-Powered-By
</IfModule>
RULE;
const SOCIAL  = 'seopress_social_option_name';
const TWITTER = 'seopress_social_accounts_twitter';

/**
 * Read the exact site file or private receipt.
 *
 * @param string $path Local path.
 * @throws RuntimeException If the local file cannot be read.
 */
function bytes( string $path ): string {
	$body = file_get_contents( $path ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- Read exact local file bytes.
	if ( false === $body ) {
		throw new RuntimeException( 'Cannot read ' . esc_html( $path ) );
	}
	return $body;
}

/**
 * Install a complete site file with its original permissions.
 *
 * @param string $path Absolute path.
 * @param string $body Complete file content.
 * @param int    $mode File permissions.
 * @throws RuntimeException When a write or rename fails.
 */
function install_file( string $path, string $body, int $mode ): void {
	if ( is_file( $path ) && bytes( $path ) === $body && ( fileperms( $path ) & 0777 ) === $mode ) {
		return;
	}
	$tmp = tempnam( dirname( $path ), '.linker-t3-' );
	if ( false === $tmp ) {
		throw new RuntimeException( 'Cannot stage the site file.' );
	}
	try {
		// phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_file_put_contents, WordPress.WP.AlternativeFunctions.file_system_operations_chmod, WordPress.WP.AlternativeFunctions.rename_rename -- Preserve permissions and atomically publish on the same filesystem.
		if ( strlen( $body ) !== file_put_contents( $tmp, $body ) || ! chmod( $tmp, $mode ) || ! rename( $tmp, $path ) ) {
			throw new RuntimeException( 'Cannot publish ' . esc_html( $path ) );
		}
	} finally {
		if ( is_file( $tmp ) ) {
			wp_delete_file( $tmp );
		}
	}
}

/**
 * Update only the owner-managed block immediately ahead of LiteSpeed.
 *
 * @param string $original Current rewrite file.
 * @param string $strategy Dynamic routes or domain-wide fallback.
 * @throws RuntimeException For partial markers or unexpected managed block order.
 */
function edge( string $original, string $strategy ): string {
	$nl    = str_contains( $original, "\r\n" ) ? "\r\n" : "\n";
	$clean = $original;
	foreach ( array( DYNAMIC, DOMAIN ) as $variant ) {
		$block = implode( "\n", array( BEGIN, $variant, HEADERS, END, '', '' ) );
		$clean = str_replace( str_replace( "\n", $nl, $block ), '', $clean );
	}
	$offset = strpos( $clean, '# BEGIN LSCACHE' );
	$host   = strpos( $clean, '# END Linker canonical host' );
	if ( str_contains( $clean, BEGIN ) || str_contains( $clean, END ) || false === $host || false === $offset || $host >= $offset || 1 !== substr_count( $clean, '# BEGIN LSCACHE' ) ) {
		throw new RuntimeException( 'Unexpected edge markers or LiteSpeed block order.' );
	}
	$block = implode( "\n", array( BEGIN, 'domain' === $strategy ? DOMAIN : DYNAMIC, HEADERS, END, '', '' ) );
	return substr_replace( $clean, str_replace( "\n", $nl, $block ), $offset, 0 );
}

/**
 * Read the installed LiteSpeed query-string list in its stored representation.
 *
 * @param mixed $stored WordPress option.
 * @return list<string>
 * @throws RuntimeException For unreadable settings.
 */
function query_list( $stored ): array {
	$list = is_string( $stored ) ? json_decode( $stored, true, 512, JSON_THROW_ON_ERROR ) : $stored;
	if ( ! is_array( $list ) || ! array_is_list( $list ) || array_filter( $list, 'is_string' ) !== $list ) {
		throw new RuntimeException( 'Cannot read the LiteSpeed query parameters.' );
	}
	return $list;
}

/**
 * Ask the installed plugin to regenerate its cache-key rules.
 *
 * @param string[] $parameters Desired parameters.
 * @throws RuntimeException If LiteSpeed did not commit the setting.
 */
function set_query_list( array $parameters ): void {
	if ( query_list( get_option( 'litespeed.conf.cache-drop_qs' ) ) === $parameters ) {
		return;
	}
	\LiteSpeed\Conf::cls()->update_confs( array( 'cache-drop_qs' => $parameters ) );
	if ( query_list( get_option( 'litespeed.conf.cache-drop_qs' ) ) !== $parameters ) {
		throw new RuntimeException( 'LiteSpeed did not save the query parameters.' );
	}
}

/**
 * Snapshot the individual files, option fields, pages and media used by T3.
 *
 * @return array<string,mixed>
 */
function snapshot(): array {
	$path = ABSPATH . '.well-known/security.txt';
	$file = ABSPATH . '.htaccess';
	return array(
		'home'          => get_option( 'home' ),
		'htaccess'      => bytes( $file ),
		'htaccess_mode' => fileperms( $file ) & 0777,
		'drop_qs'       => get_option( 'litespeed.conf.cache-drop_qs' ),
		'exclusions'    => get_option( 'litespeed.conf.cache-exc' ),
		'login_cookie'  => get_option( 'litespeed.conf.cache-login_cookie' ),
		'well_known'    => is_dir( dirname( $path ) ),
		'security'      => is_file( $path ) ? bytes( $path ) : null,
		'security_mode' => is_file( $path ) ? fileperms( $path ) & 0777 : null,
		'twitter'       => get_option( SOCIAL )[ TWITTER ] ?? null,
		'pages'         => T3Pages\snapshot(),
		'media'         => media_snapshot(),
	);
}

/** Native translator used only for recording and reading the human translation baseline. */
function translator(): Translator {
	$languages = new Languages();
	$tokenizer = new HtmlTokenizer();
	$links     = new LinkLocalizer( $languages, $tokenizer );
	$rules     = Rules::load( WP_PLUGIN_DIR . '/linker-i18n/data' );
	return new Translator( $languages, new Planner( new Segmenter( $tokenizer ), new Aligner() ), new Fields(), new State(), DeepSeekClient::from_environment( $rules ), new Validator( $rules ), new Twins( $languages, $links, new Projection( $languages ) ), $links );
}

/** Keep the reviewed translations under the control of this paired write. */
function pause_translation(): void {
	global $wp_filter;
	foreach ( array( 'pre_post_update', 'wp_after_insert_post' ) as $hook ) {
		foreach ( $wp_filter[ $hook ]->callbacks[10] ?? array() as $callback ) {
			$handler = $callback['function'];
			if ( is_array( $handler ) && $handler[0] instanceof Jobs ) {
				remove_action( $hook, $handler, 10 );
			}
		}
	}
}

/**
 * Manage the one security contact file. Other well-known resources belong to SEOPress.
 *
 * @param array<string,mixed> $before Original receipt.
 * @param bool                $apply Install the published contact file.
 * @throws RuntimeException When the directory or contact cannot be restored.
 */
function security_file( array $before, bool $apply ): void {
	$path   = ABSPATH . '.well-known/security.txt';
	$source = bytes( WP_PLUGIN_DIR . '/linker-commerce/assets/well-known/security.txt' );
	$body   = $apply ? $source : $before['security'];
	if ( null !== $body ) {
		if ( ! wp_mkdir_p( dirname( $path ) ) ) {
			throw new RuntimeException( 'Cannot create the security contact directory.' );
		}
		install_file( $path, $body, $apply ? 0644 : $before['security_mode'] );
	} elseif ( is_file( $path ) ) {
		if ( bytes( $path ) !== $source ) {
			throw new RuntimeException( 'The security contact changed after publication.' );
		}
		wp_delete_file( $path );
	}
	if ( ! $apply && ! $before['well_known'] && is_dir( dirname( $path ) ) && array( '.', '..' ) === scandir( dirname( $path ) ) ) {
		rmdir( dirname( $path ) ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_rmdir -- Remove only the now-empty task-created directory.
	}
}

( static function ( array $args ): void {
	$mode = $args[0] ?? 'snapshot';
	if ( 'snapshot' === $mode ) {
		echo wp_json_encode( snapshot(), JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR ) . "\n";
		return;
	}
	if ( ! in_array( $mode, array( 'apply', 'restore' ), true ) || empty( $args[1] ) || ! in_array( $args[2] ?? 'dynamic', array( 'dynamic', 'domain' ), true ) ) {
		WP_CLI::error( 'Use snapshot, apply <receipt> [dynamic|domain], or restore <receipt>.' );
	}
	$apply  = 'apply' === $mode;
	$before = json_decode( bytes( $args[1] ), true, 512, JSON_THROW_ON_ERROR );
	if ( get_option( 'home' ) !== $before['home'] || get_option( 'litespeed.conf.cache-exc' ) !== $before['exclusions'] || get_option( 'litespeed.conf.cache-login_cookie' ) !== $before['login_cookie'] ) {
		WP_CLI::error( 'The target or its private cache settings differ from the receipt.' );
	}
	$file      = ABSPATH . '.htaccess';
	$original  = query_list( $before['drop_qs'] );
	$desired   = array_values( array_unique( array_merge( $original, array( 'srsltid' ) ) ) );
	$current   = query_list( get_option( 'litespeed.conf.cache-drop_qs' ) );
	$published = bytes( $file );
	$strategy  = $args[2] ?? ( str_contains( $published, DOMAIN ) ? 'domain' : 'dynamic' );
	if ( $original !== $current && $desired !== $current ) {
		WP_CLI::error( 'The cache-key settings changed after the snapshot.' );
	}
	set_query_list( $apply ? $desired : $original );
	$generated = bytes( $file );
	if ( $apply && ! preg_match( '/^CacheKeyModify -qs:srsltid\s*$/m', $generated ) ) {
		WP_CLI::error( 'The native LiteSpeed cache-key rule is missing.' );
	}
	// Preserve all other managed blocks, including the WordPress PDF and planner routes.
	$before_wp = strstr( $before['htaccess'], '# BEGIN WordPress' );
	if ( false === $before_wp || strstr( $generated, '# BEGIN WordPress' ) !== $before_wp ) {
		WP_CLI::error( 'The WordPress rewrite block differs from the snapshot.' );
	}
	if ( ! $apply && edge( $generated, $strategy ) !== edge( $before['htaccess'], $strategy ) ) {
		WP_CLI::error( 'Unrelated rewrite rules changed after the snapshot.' );
	}
	install_file( $file, $apply ? edge( $generated, $strategy ) : $before['htaccess'], $before['htaccess_mode'] );
	security_file( $before, $apply );
	$social = get_option( SOCIAL );
	$old    = $social[ TWITTER ] ?? null;
	$next   = $apply ? '' : $before['twitter'];
	if ( $old !== $before['twitter'] && '' !== $old ) {
		WP_CLI::error( 'The social account setting changed after the snapshot.' );
	}
	if ( $next !== $old ) {
		if ( null === $next ) {
			unset( $social[ TWITTER ] );
		} else {
			$social[ TWITTER ] = $next;
		}
		update_option( SOCIAL, $social );
	}
	pause_translation();
	if ( $apply ) {
		media_apply( $before['media'] );
		T3Pages\apply( $before['pages'], translator() );
	} else {
		T3Pages\restore( $before['pages'] );
		media_restore( $before['media'] );
	}
	WP_CLI::success( $apply ? 'T3 media, content and edge settings published.' : 'T3 snapshot restored.' );
} )( $args ?? array() );
