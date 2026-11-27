<?php
/**
 * Publish the bilingual compatibility matrix and its Markdown representation.
 *
 * Usage:
 * wp eval-file batch-t2-geo-matrix.php snapshot > before-t2.json
 * wp eval-file batch-t2-geo-matrix.php apply|restore before-t2.json
 *
 * @package Linker\Migrate
 */

namespace Linker\Commerce\Migrate\MatrixT2;

use Linker\Commerce\Mail\NativeTransaction;
use Linker\I18n\Jobs;
use Linker\I18n\Languages;
use Linker\I18n\LinkLocalizer;
use Linker\I18n\Twins;
use Linker\I18n\Translation\{Aligner, DeepSeekClient, Fields, HtmlTokenizer, Planner, Rules, Segmenter, State, Translator, Validator};
use Linker\I18n\Woo\Projection;
use RuntimeException;
use WP_CLI;

if ( ! defined( 'WP_CLI' ) || ! WP_CLI ) {
	return;
}

/** Native translator used only for recording and reading the human translation baseline. */
function translator(): Translator {
	$languages = new Languages();
	$tokenizer = new HtmlTokenizer();
	$links     = new LinkLocalizer( $languages, $tokenizer );
	$rules     = Rules::load( WP_PLUGIN_DIR . '/linker-i18n/data' );
	return new Translator( $languages, new Planner( new Segmenter( $tokenizer ), new Aligner() ), new Fields(), new State(), DeepSeekClient::from_environment( $rules ), new Validator( $rules ), new Twins( $languages, $links, new Projection( $languages ) ), $links );
}

const EDGE = <<<'RULE'
# BEGIN Linker markdown negotiation
<IfModule mod_rewrite.c>
RewriteEngine On
RewriteCond %{HTTP:Accept} text/markdown [NC]
RewriteRule ^ - [E=Cache-Control:no-cache]
</IfModule>
# END Linker markdown negotiation
RULE;

const PAGES = array(
	'en' => array(
		'inverter-battery-compatibility',
		'Inverter & HV Battery Compatibility Matrix',
		'Inverter & HV Battery Compatibility Matrix | Linker',
		'Verified GoodWe and SAJ inverter-to-battery pairings, control modules, meter rules and VDE-AR-N 4105 / EN 50549 certificates for European PV projects.',
	),
	'de' => array(
		'wechselrichter-speicher-kompatibilitaet',
		'Wechselrichter- & Hochvoltspeicher-Kompatibilitätsmatrix',
		'Wechselrichter- & Speicher-Kompatibilitätsmatrix | Linker',
		'Geprüfte GoodWe- und SAJ-Kombinationen für Wechselrichter und Hochvoltspeicher, Steuermodule, Zählerregeln sowie VDE-AR-N 4105- und EN 50549-Zertifikate.',
	),
);

/**
 * The matrix page template and reviewed metadata.
 *
 * @param string $language Page language.
 */
function page_meta( string $language ): array {
	list( , , $title, $description ) = PAGES[ $language ];
	return array(
		'_wp_page_template'              => 'page-templates/empty.php',
		'_seopress_titles_title'         => $title,
		'_seopress_titles_desc'          => $description,
		'_seopress_social_fb_title'      => $title,
		'_seopress_social_fb_desc'       => $description,
		'_seopress_social_twitter_title' => $title,
		'_seopress_social_twitter_desc'  => $description,
	);
}

/**
 * Read the exact bytes of a local recovery or deployment file.
 *
 * @param string $path Site file or snapshot.
 * @throws RuntimeException When the local file cannot be read.
 */
function read_file( string $path ): string {
	$text = file_get_contents( $path ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- Snapshot exact local file bytes.
	if ( false === $text ) {
		throw new RuntimeException( 'Cannot read ' . esc_html( $path ) );
	}
	return $text;
}

/**
 * Insert the site rule outside both plugin-managed blocks.
 *
 * @param string $original Original .htaccess bytes.
 * @throws RuntimeException When the managed blocks cannot be identified.
 */
function edge_rules( string $original ): string {
	$anchor  = '# END NON_LSCACHE';
	$end     = strpos( $original, '# BEGIN WordPress' );
	$newline = str_contains( $original, "\r\n" ) ? "\r\n" : "\n";
	$block   = $newline . $newline . str_replace( "\n", $newline, EDGE );
	$pos     = strpos( $original, $anchor );
	if ( false !== $pos && false !== $end && str_starts_with( substr( $original, $pos, $end - $pos ), $anchor . $block ) && 2 === substr_count( $original, 'Linker markdown negotiation' ) ) {
		return $original;
	}
	if ( false === $pos || false === $end || $pos >= $end || 1 !== substr_count( $original, $anchor ) || str_contains( $original, 'Linker markdown negotiation' ) ) {
		throw new RuntimeException( 'Unexpected managed blocks in .htaccess.' );
	}
	return substr_replace( $original, $block, $pos + strlen( $anchor ), 0 );
}

/**
 * Atomically replace the rewrite rules with the original permissions.
 *
 * @param string $body Complete rewrite file.
 * @param int    $mode Saved filesystem mode.
 * @throws RuntimeException When staging or replacement fails.
 */
function install_edge( string $body, int $mode ): void {
	$path = ABSPATH . '.htaccess';
	$tmp  = tempnam( dirname( $path ), '.matrix-' );
	if ( false === $tmp ) {
		throw new RuntimeException( 'Cannot stage .htaccess.' );
	}
	try {
		// phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_file_put_contents, WordPress.WP.AlternativeFunctions.file_system_operations_chmod, WordPress.WP.AlternativeFunctions.rename_rename -- Stage with the original permissions and atomically rename on the same filesystem.
		if ( strlen( $body ) !== file_put_contents( $tmp, $body ) || ! chmod( $tmp, $mode ) || ! rename( $tmp, $path ) ) {
			throw new RuntimeException( 'Cannot install .htaccess.' );
		}
	} finally {
		if ( is_file( $tmp ) ) {
			wp_delete_file( $tmp );
		}
	}
}

/** Capture the page fields, Polylang pair and translation metadata we will write. */
function pages(): array {
	$result = array();
	foreach ( PAGES as $language => list( $slug ) ) {
		$post = get_page_by_path( $slug, OBJECT, 'page' );
		if ( ! $post ) {
			$result[ $language ] = null;
			continue;
		}
		$meta = array();
		foreach ( array_merge( array_keys( page_meta( $language ) ), array( State::STATUS, State::NOTE, State::SOURCE_HASH, State::UNITS ) ) as $key ) {
			$meta[ $key ] = get_post_meta( $post->ID, $key, false );
		}
		$result[ $language ] = array(
			'id'       => $post->ID,
			'title'    => $post->post_title,
			'content'  => $post->post_content,
			'status'   => $post->post_status,
			'language' => pll_get_post_language( $post->ID ),
			'pair'     => pll_get_post_translations( $post->ID ),
			'meta'     => $meta,
		);
	}
	return $result;
}

/**
 * Keep both reviewed translations under this migration during page writes.
 */
function pause_post_translation(): void {
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
 * Install the two reviewed pages and retain their IDs on every repeat.
 *
 * @param array<string,mixed> $current Original language pair.
 * @throws RuntimeException When the page or its native translation cannot be saved.
 */
function publish_pages( array $current ): void {
	$ids = array();
	foreach ( PAGES as $language => list( $slug, $title ) ) {
		$page = $current[ $language ];
		if ( $page && $language !== $page['language'] ) {
			throw new RuntimeException( 'Another language uses the matrix slug.' );
		}
		$post = array(
			'post_type'    => 'page',
			'post_name'    => $slug,
			'post_title'   => $title,
			'post_status'  => 'publish',
			'post_content' => '[linker_compatibility_matrix]',
		);
		if ( $page ) {
			$post['ID'] = $page['id'];
		}
		if ( ! $page || $title !== $page['title'] || $post['post_content'] !== $page['content'] || 'publish' !== $page['status'] ) {
			$id = wp_insert_post( wp_slash( $post ), true );
			if ( is_wp_error( $id ) || ! $id ) {
				throw new RuntimeException( 'Cannot publish matrix page ' . esc_html( $slug ) );
			}
		} else {
			$id = $page['id'];
		}
		$ids[ $language ] = $id;
		pll_set_post_language( $id, $language );
		foreach ( page_meta( $language ) as $key => $value ) {
			update_post_meta( $id, $key, wp_slash( $value ) );
		}
	}
	pll_save_post_translations( $ids );
	$translator = translator();
	if ( State::SYNCED !== $translator->adopt_current( State::POST, $ids['en'] ) || ! $translator->current( State::POST, $ids['en'] ) ) {
		throw new RuntimeException( 'Could not adopt the reviewed German matrix.' );
	}
}

/**
 * Restore the saved page identities, metadata and language pairing.
 *
 * @param array<string,mixed> $current Current language pair.
 * @param array<string,mixed> $before  Original page snapshot.
 * @throws RuntimeException When the page identity changed or restoration fails.
 */
function restore_pages( array $current, array $before ): void {
	foreach ( $before as $lang => $saved ) {
		$page = $current[ $lang ];
		if ( ! $saved ) {
			if ( $page && ( '[linker_compatibility_matrix]' !== $page['content'] || ! wp_delete_post( $page['id'], true ) ) ) {
				throw new RuntimeException( 'Cannot restore the original empty matrix route.' );
			}
			continue;
		}
		if ( ! $page || $page['id'] !== $saved['id'] ) {
			throw new RuntimeException( 'Original matrix page ID has changed.' );
		}
		$id = wp_update_post(
			wp_slash(
				array(
					'ID'           => $page['id'],
					'post_title'   => $saved['title'],
					'post_content' => $saved['content'],
					'post_status'  => $saved['status'],
				)
			),
			true
		);
		if ( is_wp_error( $id ) ) {
			throw new RuntimeException( esc_html( $id->get_error_message() ) );
		}
		pll_set_post_language( $id, $saved['language'] );
		foreach ( $saved['meta'] as $key => $values ) {
			delete_post_meta( $id, $key );
			foreach ( $values as $value ) {
				add_post_meta( $id, $key, wp_slash( $value ) );
			}
		}
	}
	foreach ( array_filter( $before ) as $page ) {
		pll_save_post_translations( $page['pair'] );
	}
}

/**
 * Whether the live pages match the reviewed pair and translation baseline.
 *
 * @param array<string,mixed> $pages Current page snapshot.
 */
function published( array $pages ): bool {
	foreach ( PAGES as $lang => list( , $title ) ) {
		$page = $pages[ $lang ];
		if ( ! $page || $title !== $page['title'] || 'publish' !== $page['status'] || '[linker_compatibility_matrix]' !== $page['content'] || $lang !== $page['language'] ) {
			return false;
		}
		foreach ( page_meta( $lang ) as $key => $value ) {
			if ( array( $value ) !== $page['meta'][ $key ] ) {
				return false;
			}
		}
	}
	return (int) pll_get_post( $pages['en']['id'], 'de' ) === $pages['de']['id'] && translator()->current( State::POST, $pages['en']['id'] );
}

( static function ( array $args ): void {
	$path    = ABSPATH . '.htaccess';
	$current = array(
		'home'     => get_option( 'home' ),
		'htaccess' => read_file( $path ),
		'mode'     => fileperms( $path ) & 0777,
		'pages'    => pages(),
	);
	$mode    = $args[0] ?? 'snapshot';
	if ( 'snapshot' === $mode ) {
		echo wp_json_encode( $current, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR ) . "\n";
		return;
	}
	if ( ! in_array( $mode, array( 'apply', 'restore' ), true ) || empty( $args[1] ) ) {
		WP_CLI::error( 'Use snapshot or apply|restore <snapshot.json>.' );
	}
	$before = json_decode( read_file( $args[1] ), true, 512, JSON_THROW_ON_ERROR );
	if ( $current['home'] !== $before['home'] || $current['mode'] !== $before['mode'] ) {
		WP_CLI::error( 'Snapshot does not match the installation.' );
	}
	$after = edge_rules( $before['htaccess'] );
	if ( ! in_array( $current['htaccess'], array( $before['htaccess'], $after ), true ) ) {
		WP_CLI::error( '.htaccess changed after the snapshot.' );
	}
	$applying = 'apply' === $mode;
	$edge     = $applying ? $after : $before['htaccess'];
	$ready    = $applying ? published( $current['pages'] ) : $current['pages'] === $before['pages'];
	if ( $ready && $edge === $current['htaccess'] ) {
		WP_CLI::success( '0 changes. Bilingual matrix and edge rules already match.' );
		return;
	}
	if ( ! $ready && ( $applying ? $current['pages'] !== $before['pages'] : ! published( $current['pages'] ) ) ) {
		WP_CLI::error( 'Matrix pages changed after the snapshot.' );
	}
	pause_post_translation();
	if ( ! $ready ) {
		NativeTransaction::run(
			static function () use ( $applying, $current, $before ): void {
				if ( $applying ) {
					publish_pages( $current['pages'] );
				} else {
					restore_pages( $current['pages'], $before['pages'] );
				}
			}
		);
	}
	if ( $edge !== $current['htaccess'] ) {
		install_edge( $edge, $current['mode'] );
	}
	foreach ( array_unique( array( 1000, (int) apply_filters( 'seopress_sitemaps_max_posts_per_sitemap', 1000 ) ) ) as $max ) { // phpcs:ignore WooCommerce.Commenting.CommentHooks.MissingHookComment, WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- Use the configured native SEOPress sitemap size.
		delete_transient( "seopress_sitemap_lastmod_all_page_{$max}" );
	}
	$actual = pages();
	if ( $applying ? ! published( $actual ) : $actual !== $before['pages'] ) {
		WP_CLI::error( 'Bilingual matrix readback differs from the requested state.' );
	}
	WP_CLI::success( 'Bilingual matrix and Markdown edge rules verified.' );
} )( $args ?? array() );
