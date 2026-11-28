<?php
/**
 * Install or restore the bilingual archive metadata, article links and edge routes.
 *
 * wp eval-file batch-t4-crawl-seal.php snapshot > before-t4.json
 * wp eval-file batch-t4-crawl-seal.php apply|restore before-t4.json
 *
 * @package Linker\Migrate
 */

namespace Linker\Commerce\Migrate\T4;

use Linker\Commerce\Mail\NativeTransaction;
use Linker\I18n\{Jobs, Languages, LinkLocalizer, Twins};
use Linker\I18n\Translation\{Aligner, DeepSeekClient, Fields, HtmlTokenizer, Planner, Rules, Segmenter, State, Translator, Validator};
use Linker\I18n\Woo\Projection;
use RuntimeException;
use WP_CLI;

if ( ! defined( 'WP_CLI' ) || ! WP_CLI ) {
	return;
}

const EDGE = <<<'RULE'
# BEGIN Linker edge crawl seal
<IfModule mod_rewrite.c>
RewriteEngine On

RewriteRule ^(?:forum|home|plugin)\.php$ - [G,L,NC]
RewriteRule ^archiver(?:/|$) - [G,L,NC]

RewriteRule ^wp-content/themes/picostrap5-child-base/\*$ - [G,L]

RewriteCond %{REQUEST_URI} ^/(?:de/)?$
RewriteCond %{QUERY_STRING} (^|&)s(=|&|$) [NC]
RewriteCond %{QUERY_STRING} (^|&)post_type=product(&|$) [NC]
RewriteRule ^ - [G,L]

RewriteCond %{QUERY_STRING} (^|&)wc-ajax=%25%25endpoint%25%25(&|$) [NC]
RewriteRule ^ - [G,L]

RewriteRule ^de/brand/([^/]+)/?$ {site}/de/marke/$1/ [R=301,L,NE]

RewriteRule ^product/?$ {site}/products/ [R=301,L,QSD,NE]
RewriteRule ^produkte/?$ {site}/de/produkte/ [R=301,L,QSD,NE]
RewriteRule ^shop/?$ {site}/products/ [R=301,L,QSD,NE]
RewriteRule ^de/shop/?$ {site}/de/produkte/ [R=301,L,QSD,NE]
RewriteRule ^de/faq-download/?$ {site}/de/faq-dokumente/ [R=301,L,QSD,NE]
RewriteRule ^de/service-support/?$ {site}/de/kundendienst/ [R=301,L,QSD,NE]
RewriteRule ^de/loesung/nutzspeicher/?$ {site}/de/loesung/grossspeicher/ [R=301,L,QSD,NE]
RewriteRule ^de/produkt-kategorie/(?:heimspeicher/)?res-zubehoer/?$ {site}/de/produkt-kategorie/zubehoer/ [R=301,L,QSD,NE]
RewriteRule ^de/produkt-kategorie/ci-speicher/?$ {site}/de/produkt-kategorie/gewerbespeicher/ [R=301,L,QSD,NE]
RewriteRule ^product-category/(?:residential-storage/)?res-accessories/?$ {site}/product-category/accessories/ [R=301,L,QSD,NE]
RewriteRule ^product-category/(?:residential-storage/)?res-batteries(?:-hv|-lv)?/?$ {site}/product-category/home-storage/ [R=301,L,QSD,NE]
RewriteRule ^product-category/(?:residential-storage/)?res-inverters/?$ {site}/product-category/inverters/ [R=301,L,QSD,NE]
RewriteRule ^product-category/(?:residential-storage/)?res-ev-chargers/?$ {site}/product-category/ev-chargers/ [R=301,L,QSD,NE]
RewriteRule ^product-category/residential-storage/?$ {site}/product-category/home-storage/ [R=301,L,QSD,NE]
RewriteRule ^product-category/ci-storage/?$ {site}/product-category/commercial-storage/ [R=301,L,QSD,NE]
RewriteRule ^product-category/(?:ci-storage/)?(?:ci-hybrid|ci-ac-coupled|ci-all-in-one)/?$ {site}/product-category/commercial-storage/all-in-one-systems/ [R=301,L,QSD,NE]
RewriteRule ^product-category/(?:ci-storage/)?ci-batteries/?$ {site}/product-category/commercial-storage/battery-systems/ [R=301,L,QSD,NE]
RewriteRule ^product-category/(?:ci-storage/)?ci-accessories/?$ {site}/product-category/accessories/ [R=301,L,QSD,NE]
RewriteRule ^product-category/(?:ci-storage/)?ci-inverters/?$ {site}/product-category/inverters/ [R=301,L,QSD,NE]
RewriteRule ^product-category/(?:ci-storage/)?ci-ems/?$ {site}/product-category/ems-monitoring/ [R=301,L,QSD,NE]
RewriteRule ^product/pylontech-fc0500m-40s/?$ {site}/product-category/home-storage/ [R=301,L,QSD,NE]
RewriteRule ^product/chint-dtsu666-ct/?$ {site}/product/chint-dtsu666/ [R=301,L,QSD,NE]
RewriteRule ^de/produkt/chint-dtsu666-ct/?$ {site}/de/produkt/chint-dtsu666/ [R=301,L,QSD,NE]
RewriteRule ^product/goodwe-lynx-home-a-g4-stackable-lfp-battery-module-3-3-kwh/?$ {site}/product-category/home-storage/ [R=301,L,QSD,NE]
RewriteRule ^de/produkt/goodwe-lynx-home-a-g4-stackable-lfp-battery-module-3-3-kwh/?$ {site}/de/produkt-kategorie/heimspeicher/ [R=301,L,QSD,NE]
RewriteRule ^product/mbs-kbu-58-(?:800|1000)-5-a-split-core-current-transformer-class-0-5/?$ {site}/product-category/accessories/meters-current-transformers/ [R=301,L,QSD,NE]
RewriteRule ^de/produkt/mbs-kbu-58-(?:800|1000)-5-a-split-core-current-transformer-class-0-5/?$ {site}/de/produkt-kategorie/zubehoer/energiezaehler-stromwandler/ [R=301,L,QSD,NE]
RewriteRule ^my-account/projects/?$ {site}/my-account/ [R=301,L,QSD,NE]
RewriteRule ^de/mein-konto/projects/?$ {site}/de/mein-konto/ [R=301,L,QSD,NE]
</IfModule>
# END Linker edge crawl seal
RULE;

const OPTION = 'seopress_titles_option_name';
const PAGED  = 'seopress_titles_archives_paged_noindex';
const TITLES = array(
	'en' => 'Pylontech OPTIM US L260-OMNI 260 kWh C&I Storage | Linker',
	'de' => 'Pylontech OPTIM US L260-OMNI – 260 kWh Speicher | Linker',
);
const DESCRIPTIONS = array(
	'accessories' => array(
		'en' => 'Smart meters, current transformers, backup transfer switches and monitoring accessories for PV storage systems from GoodWe, SAJ and Chint at Linker.',
		'de' => 'Smart Meter, Stromwandler, Notstrom-Umschalter und Kommunikationszubehör für PV-Speicher von GoodWe, SAJ und Chint – Datenblätter bei Linker.',
	),
	'meters-current-transformers' => array(
		'en' => 'Three-phase smart meters and split-core current transformers from GoodWe and Chint for solar self-consumption, export control and C&I monitoring.',
		'de' => 'Dreiphasige Energiezähler, Smart Meter und Klappstromwandler von GoodWe und Chint für PV-Eigenverbrauch, Einspeisemanagement und Gewerbeanlagen.',
	),
);
const ARTICLES = array(
	'gateway-meter-cloud-monitoring-data-layer'  => array( 'res-accessories', 'accessories' ),
	'remote-monitoring-after-installation'       => array( 'res-accessories', 'accessories' ),
	'indoor-vs-outdoor-battery-storage-planning' => array( 'res-batteries', 'home-storage' ),
);

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
	$tmp = tempnam( dirname( $path ), '.linker-t4-' );
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

/** Resolve the EN object and its reviewed DE translation from the installed catalog. */
function pair( string $type, string $slug ): array {
	if ( 'product_cat' === $type ) {
		$term = get_term_by( 'slug', $slug, $type );
		$en   = $term ? $term->term_id : 0;
		$de   = $en ? pll_get_term( $en, 'de' ) : 0;
	} else {
		$ids = get_posts( array( 'name' => $slug, 'post_type' => $type, 'post_status' => 'publish', 'lang' => 'en', 'fields' => 'ids', 'numberposts' => 1, 'suppress_filters' => false ) );
		$en  = $ids[0] ?? 0;
		$de  = $en ? pll_get_post( $en, 'de' ) : 0;
	}
	if ( ! $en || ! $de || (int) $de === (int) $en ) {
		throw new RuntimeException( 'Missing translation pair: ' . $slug );
	}
	return array( 'en' => (int) $en, 'de' => (int) $de );
}

/** Capture a single-valued metadata field, including absence. */
function meta( string $kind, int $id, string $key ): mixed {
	return metadata_exists( $kind, $id, $key ) ? get_metadata( $kind, $id, $key, true ) : null;
}

/** Record each field touched by the editorial change and its translation baseline. */
function entry( string $type, string $slug, string $field ): array {
	$ids  = pair( $type, $slug );
	$kind = 'product_cat' === $type ? State::TERM : State::POST;
	$row  = compact( 'kind', 'ids', 'field' );
	foreach ( $ids as $lang => $id ) {
		$row['original'][ $lang ] = 'post_content' === $field ? get_post_field( $field, $id, 'raw' ) : meta( $kind, $id, $field );
		foreach ( 'en' === $lang ? array( State::NOTE, State::STATUS ) : array( State::SOURCE_HASH, State::UNITS ) as $key ) {
			$row['state'][ $lang ][ $key ] = meta( $kind, $id, $key );
		}
	}
	return $row;
}

function snapshot(): array {
	$file = ABSPATH . '.htaccess';
	$rows = array( 'l260' => entry( 'product', 'pylontech-optim-us-l260-omni', '_seopress_titles_title' ) );
	foreach ( array_keys( DESCRIPTIONS ) as $slug ) {
		$rows[ $slug ] = entry( 'product_cat', $slug, '_seopress_titles_desc' );
	}
	foreach ( array_keys( ARTICLES ) as $slug ) {
		$rows[ $slug ] = entry( 'post', $slug, 'post_content' );
	}
	return array(
		'home' => get_option( 'home' ), 'htaccess' => bytes( $file ), 'mode' => fileperms( $file ) & 0777,
		'paged' => get_option( OPTION )[ PAGED ] ?? null, 'entries' => $rows,
	);
}

function edge( array $before ): string {
	$original = $before['htaccess'];
	$anchor   = '# BEGIN Linker edge compression and headers';
	$host     = strpos( $original, '# END Linker canonical host' );
	$pos      = strpos( $original, $anchor );
	if ( false === $host || false === $pos || $host >= $pos || str_contains( $original, '# BEGIN Linker edge crawl seal' ) ) {
		throw new RuntimeException( 'Unexpected rewrite blocks in the original snapshot.' );
	}
	$nl    = str_contains( $original, "\r\n" ) ? "\r\n" : "\n";
	$block = str_replace( array( '{site}', "\n" ), array( untrailingslashit( $before['home'] ), $nl ), EDGE );
	return substr_replace( $original, $block . $nl . $nl, $pos, 0 );
}

function write_meta( string $kind, int $id, string $key, mixed $value ): void {
	if ( null === $value ) {
		delete_metadata( $kind, $id, $key );
	} else {
		update_metadata( $kind, $id, $key, wp_slash( $value ) );
	}
	if ( meta( $kind, $id, $key ) !== $value ) {
		throw new RuntimeException( 'Metadata write failed for ' . $key );
	}
}

function values( string $slug, array $row ): array {
	if ( 'l260' === $slug ) {
		return TITLES;
	}
	if ( isset( DESCRIPTIONS[ $slug ] ) ) {
		return DESCRIPTIONS[ $slug ];
	}
	list( $from, $to ) = ARTICLES[ $slug ];
	$old = "/product-category/residential-storage/$from/";
	$de  = 'accessories' === $to ? '/de/produkt-kategorie/zubehoer/' : '/de/produkt-kategorie/heimspeicher/';
	return array(
		'en' => str_replace( $old, "/product-category/$to/", $row['original']['en'] ),
		'de' => str_replace( $old, $de, $row['original']['de'] ),
	);
}

function change_entry( string $slug, array $row, array $current, bool $apply, Translator $translator ): void {
	$desired = values( $slug, $row );
	$target  = $apply ? $desired : $row['original'];
	if ( $row['ids'] !== $current['ids'] ) {
		throw new RuntimeException( 'Translation pairing changed: ' . $slug );
	}
	foreach ( $target as $lang => $value ) {
		$old = $current['original'][ $lang ];
		if ( $old === $value ) {
			continue;
		}
		if ( $old !== $row['original'][ $lang ] && $old !== $desired[ $lang ] ) {
			throw new RuntimeException( 'Editorial field changed since snapshot: ' . $slug );
		}
		$id = $row['ids'][ $lang ];
		if ( 'post_content' !== $row['field'] ) {
			write_meta( $row['kind'], $id, $row['field'], $value );
		} else {
			$result = wp_update_post( wp_slash( array( 'ID' => $id, 'post_content' => $value ) ), true );
			if ( is_wp_error( $result ) || get_post_field( 'post_content', $id, 'raw' ) !== $value ) {
				throw new RuntimeException( 'Cannot update article ' . $slug );
			}
		}
	}
	$en = $row['ids']['en'];
	if ( $apply ) {
		if ( $target !== $current['original'] || ! $translator->current( $row['kind'], $en ) ) {
			if ( State::SYNCED !== $translator->adopt_current( $row['kind'], $en ) ) {
				throw new RuntimeException( 'Incomplete German translation: ' . $slug );
			}
		}
	} else {
		foreach ( $row['state'] as $lang => $fields ) {
			foreach ( $fields as $key => $value ) {
				if ( $current['state'][ $lang ][ $key ] !== $value ) {
					write_meta( $row['kind'], $row['ids'][ $lang ], $key, $value );
				}
			}
		}
	}
}

function migrate( array $before, bool $apply ): void {
	global $wpdb;
	// A failed database transaction can leave its post and metadata reads in Redis.
	foreach ( $before['entries'] as $row ) {
		foreach ( $row['ids'] as $id ) {
			if ( State::POST === $row['kind'] ) {
				clean_post_cache( $id );
			} else {
				clean_term_cache( $id, 'product_cat' );
			}
		}
	}
	$current = snapshot();
	$rules   = edge( $before );
	if ( $current['home'] !== $before['home'] || ! in_array( $current['htaccess'], array( $before['htaccess'], $rules ), true ) || ! in_array( $current['paged'], array( $before['paged'], '' ), true ) ) {
		throw new RuntimeException( 'Site, rewrite rules or pagination setting differ from the snapshot.' );
	}
	pause_translation();
	$translator = translator();
	NativeTransaction::run( static function () use ( $before, $current, $apply, $translator, $wpdb ): void {
		foreach ( $before['entries'] as $slug => $row ) {
			change_entry( $slug, $row, $current['entries'][ $slug ], $apply, $translator );
		}
		if ( $apply ) {
			$remaining = $wpdb->get_col( "SELECT ID FROM {$wpdb->posts} WHERE post_type='post' AND post_status='publish' AND (post_content LIKE '%/product-category/residential-storage/%' OR post_content LIKE '%/product-category/ci-storage/%')" );
			if ( $remaining || $wpdb->last_error ) {
				throw new RuntimeException( 'Published posts with legacy category links: ' . implode( ',', $remaining ) . ' ' . $wpdb->last_error );
			}
		}
		$options = get_option( OPTION );
		$next    = $apply ? '' : $before['paged'];
		if ( null === $next ) {
			unset( $options[ PAGED ] );
		} else {
			$options[ PAGED ] = $next;
		}
		update_option( OPTION, $options );
	} );
	install_file( ABSPATH . '.htaccess', $apply ? $rules : $before['htaccess'], $before['mode'] );
	flush_rewrite_rules( false );
	foreach ( array( 'post', 'page', 'product', 'category', 'product_cat', 'product_brand' ) as $type ) {
		foreach ( array_unique( array( 1000, (int) apply_filters( 'seopress_sitemaps_max_posts_per_sitemap', 1000 ) ) ) as $size ) {
			delete_transient( 'seopress_sitemap_lastmod_all_' . $type . '_' . $size );
		}
	}
}

$operation = $args[0] ?? '';
if ( 'snapshot' === $operation ) {
	WP_CLI::line( wp_json_encode( snapshot(), JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR ) );
} elseif ( in_array( $operation, array( 'apply', 'restore' ), true ) && isset( $args[1] ) ) {
	try {
		migrate( json_decode( bytes( $args[1] ), true, 512, JSON_THROW_ON_ERROR ), 'apply' === $operation );
	} catch ( \Throwable $failure ) {
		WP_CLI::error( $failure->getMessage() );
	}
	WP_CLI::success( 'Crawl seal: ' . $operation );
} else {
	WP_CLI::error( 'Usage: snapshot | apply <snapshot> | restore <snapshot>' );
}
