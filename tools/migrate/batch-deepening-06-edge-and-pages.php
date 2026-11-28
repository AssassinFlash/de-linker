<?php
/**
 * Publish or restore the bilingual WindPress pages and their public cache rules.
 *
 * wp eval-file batch-deepening-06-edge-and-pages.php apply|restore /private/backup.json
 *
 * @package Linker\Migrate
 */

namespace Linker\Commerce\Migrate\Deepening06;

use Linker\Commerce\Mail\NativeTransaction;
use Linker\I18n\Jobs;
use Linker\I18n\Languages;
use Linker\I18n\LinkLocalizer;
use Linker\I18n\Twins;
use Linker\I18n\Translation\{Aligner, DeepSeekClient, Fields, HtmlTokenizer, Planner, Rules, Segmenter, State, Translator, Validator};
use Linker\I18n\Woo\Projection;
use Linker\Tools\Planner\Application;
use RuntimeException;
use WP_CLI;

if ( ! defined( 'WP_CLI' ) || ! WP_CLI ) {
	return;
}

const PAIRS = array( 13 => 6913, 862 => 6865, 874 => 6919, 746 => 6871, 749 => 6923, 792 => 6921, 1755 => 6917 );
const STYLES = array(
	862  => array( 'about-journal.css', 'mobile-photo-topics.css' ),
	874  => array( 'capability-page.css' ),
	746  => array( 'solution-journal.css' ),
	749  => array( 'residential-journal.css' ),
	792  => array( 'commercial-journal.css' ),
	1755 => array( 'utility-journal.css', 'utility-middle.css' ),
);

const CONTACT = <<<'APACHE'
# BEGIN Linker contact cache bypass
<IfModule mod_rewrite.c>
RewriteEngine On
RewriteCond %{QUERY_STRING} !^$ [OR]
RewriteCond %{HTTP_COOKIE} (^|;[[:space:]]*)(?:wp_woocommerce_session_[^=;]*|woocommerce_items_in_cart)=
RewriteRule ^(?:contact|de/kontakt)/?$ - [E=Cache-Control:no-cache]
</IfModule>
# END Linker contact cache bypass
APACHE;

const ASSETS = <<<'APACHE'
# BEGIN Linker static asset cache
<IfModule mod_rewrite.c>
RewriteEngine On
RewriteCond %{QUERY_STRING} (^|&)ver=[^&]+ [NC]
RewriteRule \.(?:js|mjs|css)$ - [E=LINKER_IMMUTABLE_ASSET:1,NC]
RewriteRule -[a-f0-9]{16,}\.(?:js|mjs|css)$ - [E=LINKER_IMMUTABLE_ASSET:1,NC]
RewriteRule \.(?:woff2?|ttf|otf|webp|avif|png|jpe?g|gif|svg|ico)$ - [E=LINKER_IMMUTABLE_ASSET:1,NC]
</IfModule>
<IfModule mod_expires.c>
ExpiresActive On
ExpiresByType font/woff2 "access plus 1 year"
ExpiresByType font/woff "access plus 1 year"
ExpiresByType image/webp "access plus 1 year"
ExpiresByType image/avif "access plus 1 year"
ExpiresByType image/png "access plus 1 year"
ExpiresByType image/jpeg "access plus 1 year"
ExpiresByType image/gif "access plus 1 year"
ExpiresByType image/svg+xml "access plus 1 year"
ExpiresByType image/x-icon "access plus 1 year"
</IfModule>
<IfModule mod_headers.c>
Header set Cache-Control "public, max-age=31536000, immutable" env=LINKER_IMMUTABLE_ASSET
Header unset Expires env=LINKER_IMMUTABLE_ASSET
</IfModule>
# END Linker static asset cache
APACHE;

function bytes( string $path ): string {
	$data = file_get_contents( $path );
	if ( false === $data ) {
		throw new RuntimeException( "Cannot read $path" );
	}
	return $data;
}

/** Stage on the target filesystem and preserve the original permissions. */
function publish_file( string $file, string $data, int $mode ): void {
	$tmp = tempnam( dirname( $file ), '.linker-d06-' );
	if ( false === $tmp ) {
		throw new RuntimeException( "Cannot stage $file" );
	}
	try {
		if ( strlen( $data ) !== file_put_contents( $tmp, $data ) || ! chmod( $tmp, $mode ) || ! rename( $tmp, $file ) ) {
			throw new RuntimeException( "Cannot publish $file" );
		}
	} finally {
		if ( is_file( $tmp ) ) {
			unlink( $tmp );
		}
	}
}

/** The WordPress rewrite block is owned by core, the planner and the Woo PDF route. */
function check_edge( string $text ): void {
	$rules = ( new Application( '' ) )->cache_rules( 'RewriteEngine On' );
	$text  = str_replace( "\r\n", "\n", $text );
	preg_match( '/^# BEGIN WordPress$\n(.*?)^# END WordPress$/ms', $text, $match );
	$before = strstr( $match[1] ?? '', 'RewriteCond %{REQUEST_FILENAME} !-f', true );
	if ( false === $before || ! str_contains( $before, $rules . "\n" ) || ! preg_match( '/^RewriteRule [^\n]+index\.php\?linker_public_document=\$1 \[END,NC,QSA\]$/m', $before ) ) {
		throw new RuntimeException( 'The WordPress planner or document rewrite is missing or out of order.' );
	}
}

function published_edge( string $before ): string {
	check_edge( $before );
	if ( 1 !== substr_count( $before, '# BEGIN WordPress' ) || 1 !== substr_count( $before, '# END WordPress' ) || str_contains( $before, '# BEGIN Linker static asset cache' ) || str_contains( $before, '# BEGIN Linker contact cache bypass' ) ) {
		throw new RuntimeException( 'Unexpected rewrite markers in the preimage.' );
	}
	$nl = str_contains( $before, "\r\n" ) ? "\r\n" : "\n";
	return str_replace(
		array( '# BEGIN WordPress', '# END WordPress' ),
		array( str_replace( "\n", $nl, CONTACT ) . $nl . $nl . '# BEGIN WordPress', '# END WordPress' . $nl . $nl . str_replace( "\n", $nl, ASSETS ) ),
		$before
	);
}

function published_body( string $body, int $en, bool $german ): string {
	if ( 13 === $en ) {
		$section = '<section class="hero-cinematic">';
		if ( 1 !== substr_count( $body, $section ) || str_contains( $body, 'class="lk-hero-media"' ) ) {
			throw new RuntimeException( 'Unexpected homepage hero in the preimage.' );
		}
		$photo = '/wp-content/uploads/2026/09/linker-linking-value-serving-you';
		$alt   = $german ? 'Gewerbliche Photovoltaik- und Batteriespeicheranlage von Linker' : 'Commercial solar and battery energy storage installation supplied by Linker';
		$image = '<img class="lk-hero-media" src="' . $photo . '.webp" srcset="' . $photo . '-768x576.webp 768w, ' . $photo . '.webp 1024w" sizes="(max-width: 600px) 768px, 100vw" width="1024" height="768" alt="' . $alt . '" fetchpriority="high" loading="eager" decoding="async" />';
		return str_replace( $section, $section . $image, $body );
	}

	foreach ( STYLES[ $en ] as $name ) {
		$css   = bytes( WP_PLUGIN_DIR . '/linker-commerce/content/windpress/' . $name );
		$start = 'capability-page.css' === $name ? '<style>' : '<style data-site-css="' . $name . '">';
		$block = $start . $css . '</style>';
		if ( 1 !== substr_count( $body, $block ) ) {
			throw new RuntimeException( "Inline stylesheet differs from $name (page $en)." );
		}
		$body = str_replace( $block, '', $body );
	}
	if ( in_array( $en, array( 746, 749, 792 ), true ) ) {
		foreach ( array( 'capability-cards', 'app-details' ) as $name ) {
			$body = str_replace( '[linker_marketing_style name="' . $name . '"]', '', $body );
		}
	}
	return $body;
}

/** Record all translation metadata, including fields registered after earlier migrations. */
function page_state( int $id, bool $german ): array {
	$post = get_post( $id );
	if ( ! $post instanceof \WP_Post || 'page' !== $post->post_type || 'publish' !== $post->post_status ) {
		throw new RuntimeException( "Expected published page $id." );
	}
	$meta = array();
	foreach ( array_keys( get_post_meta( $id ) ) as $key ) {
		if ( str_starts_with( $key, '_linker_i18n_' ) ) {
			$meta[ $key ] = get_post_meta( $id, $key, false );
		}
	}
	ksort( $meta );
	$fields = ( new Fields() )->of_post( $post, $german );
	unset( $fields['post_content'] );
	return array( 'body' => $post->post_content, 'meta' => $meta, 'fields' => $fields );
}

function snapshot( string $edge ): array {
	$state = array(
		'site'          => get_option( 'home' ),
		'htaccess'      => bytes( $edge ),
		'htaccess_mode' => fileperms( $edge ) & 0777,
		'pages'         => array(),
	);
	published_edge( $state['htaccess'] );
	foreach ( PAIRS as $en => $de ) {
		if ( (int) pll_get_post( $en, 'de' ) !== $de || 'en' !== pll_get_post_language( $en ) ) {
			throw new RuntimeException( "Language pair changed for page $en." );
		}
		foreach ( array( $en, $de ) as $id ) {
			$row                     = page_state( $id, $id === $de );
			$row['published']        = published_body( $row['body'], $en, $id === $de );
			$state['pages'][ $id ] = $row;
		}
	}
	return $state;
}

/** Adopt the existing reviewed text only for pairs already marked synchronized. */
function translator(): Translator {
	$languages = new Languages();
	$tokenizer = new HtmlTokenizer();
	$links     = new LinkLocalizer( $languages, $tokenizer );
	$rules     = Rules::load( WP_PLUGIN_DIR . '/linker-i18n/data' );
	return new Translator( $languages, new Planner( new Segmenter( $tokenizer ), new Aligner() ), new Fields(), new State(), DeepSeekClient::from_environment( $rules ), new Validator( $rules ), new Twins( $languages, $links, new Projection( $languages ) ), $links );
}

function migrate_pages( array $pages, bool $apply ): void {
	global $wp_filter;
	foreach ( array( 'pre_post_update', 'wp_after_insert_post' ) as $hook ) {
		foreach ( $wp_filter[ $hook ]->callbacks[10] ?? array() as $callback ) {
			$handler = $callback['function'];
			if ( is_array( $handler ) && $handler[0] instanceof Jobs ) {
				remove_action( $hook, $handler, 10 );
			}
		}
	}
	$translator = translator();
	foreach ( PAIRS as $en => $de ) {
		$changed = false;
		foreach ( array( $en, $de ) as $id ) {
			$row = $pages[ $id ];
			$now = page_state( $id, $id === $de );
			if ( $now['fields'] !== $row['fields'] || ! in_array( $now['body'], array( $row['body'], $row['published'] ), true ) || (int) pll_get_post( $en, 'de' ) !== $de ) {
				throw new RuntimeException( "Page $id changed independently." );
			}
			$target = $apply ? $row['published'] : $row['body'];
			if ( $now['body'] === $target ) {
				continue;
			}
			if ( $apply && $now['meta'] !== $row['meta'] ) {
				throw new RuntimeException( "Translation metadata changed for page $id." );
			}
			$result = wp_update_post( wp_slash( array( 'ID' => $id, 'post_content' => $target ) ), true );
			if ( is_wp_error( $result ) || $target !== get_post_field( 'post_content', $id, 'raw' ) ) {
				throw new RuntimeException( "Cannot update page $id." );
			}
			$changed = true;
			if ( ! $apply ) {
				foreach ( array_unique( array_merge( array_keys( $row['meta'] ), array_keys( $now['meta'] ) ) ) as $key ) {
					if ( ( $row['meta'][ $key ] ?? null ) === ( $now['meta'][ $key ] ?? null ) ) {
						continue;
					}
					delete_post_meta( $id, $key );
					foreach ( $row['meta'][ $key ] ?? array() as $value ) {
						add_post_meta( $id, $key, wp_slash( $value ) );
					}
				}
			}
		}
		if ( $apply && $changed && array( State::SYNCED ) === ( $pages[ $en ]['meta'][ State::STATUS ] ?? array() ) && ( State::SYNCED !== $translator->adopt_current( State::POST, $en ) || ! $translator->current( State::POST, $en ) ) ) {
			throw new RuntimeException( "Cannot record the reviewed translation for page $en." );
		}
	}
}

( static function ( array $args ): void {
	if ( ( $args[0] ?? '' ) === '--' ) {
		array_shift( $args );
	}
	$mode = preg_replace( '/^--/', '', $args[0] ?? '' );
	if ( count( $args ) !== 2 || ! in_array( $mode, array( 'apply', 'restore' ), true ) ) {
		WP_CLI::error( 'Use --apply <backup> or --restore <backup>.' );
	}
	$file  = $args[1];
	$apply = 'apply' === $mode;
	$edge  = ABSPATH . '.htaccess';
	if ( $apply && ! is_file( $file ) ) {
		publish_file( $file, wp_json_encode( snapshot( $edge ), JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR ), 0600 );
	}
	$before = json_decode( bytes( $file ), true, 512, JSON_THROW_ON_ERROR );
	if ( get_option( 'home' ) !== $before['site'] || ( fileperms( $edge ) & 0777 ) !== $before['htaccess_mode'] ) {
		WP_CLI::error( 'Site identity or rewrite file permissions differ from the preimage.' );
	}
	$published = published_edge( $before['htaccess'] );
	$current   = bytes( $edge );
	if ( $current !== $published && $current !== $before['htaccess'] ) {
		WP_CLI::error( 'The rewrite file changed independently.' );
	}
	NativeTransaction::run( static fn () => migrate_pages( $before['pages'], $apply ) );
	$target = $apply ? $published : $before['htaccess'];
	if ( $current !== $target ) {
		publish_file( $edge, $target, $before['htaccess_mode'] );
	}
	check_edge( bytes( $edge ) );
	WP_CLI::success( $apply ? 'Cache rules and bilingual pages published.' : 'Cache rules and bilingual pages restored.' );
} )( $args ?? array() );
