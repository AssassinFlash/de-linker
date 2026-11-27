<?php
/**
 * Publish the bilingual inverter descriptions, SEO settings, icon and canonical host.
 *
 * wp eval-file batch-t1-seo-options.php snapshot > before-options.json
 * wp eval-file batch-t1-seo-options.php apply|restore before-options.json
 *
 * @package Linker\Migrate
 */

namespace Linker\Migrate\SeoT1;

use Linker\I18n\Jobs;
use RuntimeException;
use WP_CLI;

if ( ! defined( 'WP_CLI' ) || ! WP_CLI ) {
	return;
}

const HOST_BLOCK = <<<'HTACCESS'
# BEGIN Linker canonical host
<IfModule mod_rewrite.c>
RewriteEngine On
RewriteCond %{HTTP_HOST} ^www\.de-linker\.com$ [NC]
RewriteRule ^ https://de-linker.com%{REQUEST_URI} [R=301,L,NE]
RewriteCond %{HTTPS} !=on
RewriteCond %{HTTP:X-Forwarded-Proto} !^https$ [NC]
RewriteCond %{HTTP_HOST} ^de-linker\.com$ [NC]
RewriteRule ^ https://de-linker.com%{REQUEST_URI} [R=301,L,NE]
</IfModule>
# END Linker canonical host

HTACCESS;

const OPTIONS = array(
	'seopress_titles_option_name'      => array(
		'seopress_titles_home_site_desc' => 'PV and energy storage for installers and EPCs: hybrid inverters, LFP batteries and complete storage systems from GoodWe, SAJ, Pylontech and Chint. Partner pricing and documented compatibility.',
		'seopress_titles_tax_titles'     => array(
			'product_brand' => array( 'title' => '%%term_title%% | %%sitetitle%%', 'description' => '', 'noindex' => '' ),
		),
	),
	'seopress_xml_sitemap_option_name' => array(
		'seopress_xml_sitemap_taxonomies_list' => array( 'product_brand' => array( 'include' => '1' ) ),
	),
	'seopress_advanced_option_name'    => array( 'seopress_advanced_advanced_attachments' => '' ),
);

const TERMS = array(
	'en' => array( 449, 'inverters', 'Single- and three-phase inverters and power modules from GoodWe and SAJ.' ),
	'de' => array( 610, 'wechselrichter', 'Ein- und dreiphasige Wechselrichter und Leistungsmodule von GoodWe und SAJ.' ),
);

/** Replace or remove a single file. Visitors see either complete version. */
function write_file( string $path, ?string $body, int $mode ): void {
	if ( null === $body ) {
		if ( is_file( $path ) && ! unlink( $path ) ) {
			throw new RuntimeException( "Cannot remove $path" );
		}
		return;
	}
	$tmp = tempnam( dirname( $path ), '.linker-t1-' );
	if ( false === $tmp ) {
		throw new RuntimeException( "Cannot stage $path" );
	}
	try {
		if ( strlen( $body ) !== file_put_contents( $tmp, $body ) || ! chmod( $tmp, $mode ) || ! rename( $tmp, $path ) ) {
			throw new RuntimeException( "Cannot install $path" );
		}
	} finally {
		if ( is_file( $tmp ) ) {
			unlink( $tmp );
		}
	}
}

function bytes( string $path ): string {
	$data = file_get_contents( $path );
	if ( false === $data ) {
		throw new RuntimeException( "Cannot read $path" );
	}
	return $data;
}

/** Retain only settings owned by this publication. */
function options_snapshot(): array {
	$selected = array();
	foreach ( OPTIONS as $name => $fields ) {
		$option = get_option( $name );
		foreach ( $fields as $key => $value ) {
			$selected[ $name ][ $key ] = is_array( $value )
				? ( $option[ $key ]['product_brand'] ?? null )
				: ( $option[ $key ] ?? null );
		}
	}
	return $selected;
}

function snapshot(): array {
	$terms = array();
	foreach ( TERMS as $lang => list( $id, $slug ) ) {
		$term = get_term( $id, 'product_cat', OBJECT, 'raw' );
		if ( ! $term instanceof \WP_Term || $slug !== $term->slug || $lang !== pll_get_term_language( $id ) || (int) pll_get_term( TERMS['en'][0], $lang ) !== $id ) {
			throw new RuntimeException( "Expected the published $lang inverter category." );
		}
		$terms[ $id ] = $term->description;
	}
	$icon = ABSPATH . 'favicon.ico';
	$file = ABSPATH . '.htaccess';
	return array(
		'home'          => get_option( 'home' ),
		'terms'         => $terms,
		'options'       => options_snapshot(),
		'favicon'       => is_file( $icon ) ? base64_encode( bytes( $icon ) ) : null,
		'favicon_mode'  => is_file( $icon ) ? fileperms( $icon ) & 0777 : null,
		'htaccess'      => bytes( $file ),
		'htaccess_mode' => fileperms( $file ) & 0777,
	);
}

function published( array $before ): array {
	$after = $before;
	foreach ( TERMS as list( $id, , $text ) ) {
		$after['terms'][ $id ] = $text;
	}
	foreach ( OPTIONS as $name => $fields ) {
		foreach ( $fields as $key => $value ) {
			$after['options'][ $name ][ $key ] = is_array( $value ) ? $value['product_brand'] : $value;
		}
	}
	$after['favicon']      = base64_encode( bytes( WP_PLUGIN_DIR . '/linker-commerce/assets/icons/favicon.ico' ) );
	$after['favicon_mode'] = 0644;
	if ( ! str_starts_with( $before['htaccess'], HOST_BLOCK ) ) {
		if ( str_contains( $before['htaccess'], '# BEGIN Linker canonical host' ) || str_contains( $before['htaccess'], '# END Linker canonical host' ) ) {
			throw new RuntimeException( 'Review the existing canonical host block before updating it.' );
		}
		$after['htaccess'] = HOST_BLOCK . "\n" . $before['htaccess'];
	}
	return $after;
}

/** The English and German originals are both reviewed; keep the translator out of this CLI process. */
function pause_term_translation(): void {
	global $wp_filter;
	foreach ( array( 'edit_terms', 'edited_term' ) as $hook ) {
		foreach ( $wp_filter[ $hook ]->callbacks[10] ?? array() as $callback ) {
			$handler = $callback['function'];
			if ( is_array( $handler ) && $handler[0] instanceof Jobs ) {
				remove_action( $hook, $handler, 10 );
			}
		}
	}
}

function publish( array $current, array $target ): void {
	pause_term_translation();
	foreach ( $target['terms'] as $id => $text ) {
		if ( $current['terms'][ $id ] !== $text ) {
			$result = wp_update_term( $id, 'product_cat', array( 'description' => wp_slash( $text ) ) );
			if ( is_wp_error( $result ) ) {
				throw new RuntimeException( $result->get_error_message() );
			}
		}
	}
	foreach ( OPTIONS as $name => $fields ) {
		$option = get_option( $name );
		foreach ( $fields as $key => $value ) {
			$next = $target['options'][ $name ][ $key ];
			if ( is_array( $value ) ) {
				if ( null === $next ) {
					unset( $option[ $key ]['product_brand'] );
				} else {
					$option[ $key ]['product_brand'] = $next;
				}
			} elseif ( null === $next ) {
				unset( $option[ $key ] );
			} else {
				$option[ $key ] = $next;
			}
		}
		if ( $target['options'][ $name ] !== $current['options'][ $name ] ) {
			update_option( $name, $option );
		}
	}
	if ( $current['favicon'] !== $target['favicon'] || $current['favicon_mode'] !== $target['favicon_mode'] ) {
		write_file( ABSPATH . 'favicon.ico', null === $target['favicon'] ? null : base64_decode( $target['favicon'], true ), $target['favicon_mode'] ?? 0644 );
	}
	if ( $current['htaccess'] !== $target['htaccess'] ) {
		write_file( ABSPATH . '.htaccess', $target['htaccess'], $target['htaccess_mode'] );
	}
	foreach ( array( 'post', 'page', 'product' ) as $type ) {
		foreach ( array_unique( array( 1000, (int) apply_filters( 'seopress_sitemaps_max_posts_per_sitemap', 1000 ) ) ) as $max ) {
			delete_transient( "seopress_sitemap_lastmod_all_{$type}_{$max}" );
		}
	}
}

$current = snapshot();
$mode    = $args[0] ?? 'snapshot';
if ( 'snapshot' === $mode ) {
	WP_CLI::line( wp_json_encode( $current, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR ) );
	return;
}
if ( ! in_array( $mode, array( 'apply', 'restore' ), true ) || empty( $args[1] ) ) {
	WP_CLI::error( 'Use snapshot, apply <snapshot.json>, or restore <snapshot.json>.' );
}
$before = json_decode( bytes( $args[1] ), true, 512, JSON_THROW_ON_ERROR );
if ( $current['home'] !== $before['home'] ) {
	WP_CLI::error( 'The snapshot belongs to a different WordPress installation.' );
}
$after  = published( $before );
$target = 'apply' === $mode ? $after : $before;
if ( $current === $target ) {
	WP_CLI::success( 'SEO settings, bilingual copy and files already match.' );
	return;
}
// Accept interrupted writes only when each owned item is still its original or approved value.
foreach ( array( 'terms', 'options' ) as $group ) {
	foreach ( $current[ $group ] as $key => $value ) {
		if ( $value !== $before[ $group ][ $key ] && $value !== $after[ $group ][ $key ] ) {
			WP_CLI::error( "The $group entry $key changed after the snapshot." );
		}
	}
}
foreach ( array( 'favicon', 'favicon_mode', 'htaccess', 'htaccess_mode' ) as $key ) {
	if ( $current[ $key ] !== $before[ $key ] && $current[ $key ] !== $after[ $key ] ) {
		WP_CLI::error( "$key changed after the snapshot." );
	}
}
publish( $current, $target );
if ( snapshot() !== $target ) {
	WP_CLI::error( 'Published settings or files differ from the requested state.' );
}
WP_CLI::success( 'SEO settings, bilingual copy and files verified.' );
