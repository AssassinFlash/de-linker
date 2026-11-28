<?php
/**
 * Install or restore the reviewed search copy, capability links, image sizes and ETR specifications.
 *
 * Usage: wp eval-file batch-t5-sku-and-content-mesh.php snapshot > before-t5.json
 * wp eval-file batch-t5-sku-and-content-mesh.php apply|restore before-t5.json
 *
 * @package Linker\Migrate
 */

namespace Linker\Commerce\Migrate\T5;

use Linker\Commerce\Mail\NativeTransaction;
use Linker\Commerce\Products\Publication\EvidenceBindings;
use Linker\I18n\{Jobs, Languages, LinkLocalizer, Twins};
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
 * Resolve the EN object and its reviewed DE translation from the installed catalog.
 *
 * @param string $type Post type or product category taxonomy.
 * @param string $slug English object slug.
 * @return array{en:int,de:int}
 * @throws RuntimeException When the catalog has no distinct translation.
 */
function pair( string $type, string $slug ): array {
	if ( 'product_cat' === $type ) {
		$term = get_term_by( 'slug', $slug, $type );
		$en   = $term ? $term->term_id : 0;
		$de   = $en ? pll_get_term( $en, 'de' ) : 0;
	} else {
		$ids = get_posts(
			array(
				'name'             => $slug,
				'post_type'        => $type,
				'post_status'      => 'publish',
				'lang'             => 'en',
				'fields'           => 'ids',
				'numberposts'      => 1,
				'suppress_filters' => false,
			)
		);
		$en  = $ids[0] ?? 0;
		$de  = $en ? pll_get_post( $en, 'de' ) : 0;
	}
	if ( ! $en || ! $de || (int) $de === (int) $en ) {
		throw new RuntimeException( esc_html( 'Missing translation pair: ' . esc_html( $slug ) ) );
	}
	return array(
		'en' => (int) $en,
		'de' => (int) $de,
	);
}

/**
 * Capture a single-valued metadata field, including absence.
 *
 * @param string $kind Metadata object type.
 * @param int    $id   Object ID.
 * @param string $key  Metadata key.
 */
function meta( string $kind, int $id, string $key ): mixed {
	return metadata_exists( $kind, $id, $key ) ? get_metadata( $kind, $id, $key, true ) : null;
}

/**
 * Set or remove a metadata field and read back its stored value.
 *
 * @param string $kind  Metadata object type.
 * @param int    $id    Object ID.
 * @param string $key   Metadata key.
 * @param mixed  $value Snapshot or published value.
 * @throws RuntimeException When the stored value differs.
 */
function write_meta( string $kind, int $id, string $key, mixed $value ): void {
	if ( null === $value ) {
		delete_metadata( $kind, $id, $key );
	} else {
		update_metadata( $kind, $id, $key, wp_slash( $value ) );
	}
	if ( meta( $kind, $id, $key ) !== $value ) {
		throw new RuntimeException( esc_html( 'Metadata write failed for ' . esc_html( $key ) ) );
	}
}

/**
 * Capture the native fields and translation baseline of one pair.
 *
 * @param string                     $type Post type or taxonomy.
 * @param string                     $slug English source slug.
 * @param array<string,list<string>> $fields Metadata keys and post fields by language.
 * @return array<string,mixed>
 */
function entry( string $type, string $slug, array $fields ): array {
	$ids  = pair( $type, $slug );
	$kind = 'product_cat' === $type ? State::TERM : State::POST;
	$row  = compact( 'ids', 'kind' );
	foreach ( $ids as $lang => $id ) {
		foreach ( $fields[ $lang ] ?? array() as $key ) {
			$row['values'][ $lang ][ $key ] = in_array( $key, array( 'post_content', 'post_excerpt' ), true )
				? get_post_field( $key, $id, 'raw' ) : meta( $kind, $id, $key );
		}
		foreach ( 'en' === $lang ? array( State::NOTE, State::STATUS ) : array( State::SOURCE_HASH, State::UNITS ) as $key ) {
			$row['state'][ $lang ][ $key ] = meta( $kind, $id, $key );
		}
	}
	return $row;
}

/**
 * Read a local migration input.
 *
 * @param string $path JSON data or site snapshot.
 * @return array<string,mixed>
 * @throws RuntimeException When the input cannot be read.
 */
function read_json( string $path ): array {
	$bytes = file_get_contents( $path ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- Local CLI input.
	if ( false === $bytes ) {
		throw new RuntimeException( 'Cannot read ' . esc_html( $path ) );
	}
	return json_decode( $bytes, true, 512, JSON_THROW_ON_ERROR );
}

/**
 * Reviewed SEOPress field values by source slug and language.
 *
 * @return array<string,array<string,array<string,array<string,string>>>>
 */
function search_copy(): array {
	return read_json( __DIR__ . '/batch-t5-search-copy.json' );
}

/**
 * Collect the bilingual fields and their evidence bindings before publication.
 *
 * @return array<string,mixed>
 * @throws RuntimeException When the required source product is absent.
 */
function snapshot(): array {
	$entries = array();
	foreach ( search_copy() as $type => $slugs ) {
		foreach ( $slugs as $slug => $values ) {
			$entries[ $slug ] = entry( $type, $slug, array_map( 'array_keys', $values ) );
		}
	}
	foreach ( array( 'about', 'capability', 'contact' ) as $slug ) {
		$entries[ $slug ] = entry( 'page', $slug, array_fill_keys( array( 'en', 'de' ), array( 'post_content' ) ) );
	}
	$id = wc_get_product_id_by_sku( 'DLK-GOODWE-GW12499KETRG10' );
	if ( ! $id ) {
		throw new RuntimeException( 'GW124.99K-ETR-G10 is missing.' );
	}
	$keys           = array( '_tv_legacy_acf_json', '_linker_de_acf_json', '_tv_b2b_figures', 'post_content', 'post_excerpt' );
	$entries['etr'] = entry( 'product', get_post_field( 'post_name', pll_get_post( $id, 'en' ), 'raw' ), array_fill_keys( array( 'en', 'de' ), $keys ) );
	return array(
		'site'            => get_option( 'home' ),
		'entries'         => $entries,
		'figure_bindings' => meta( 'post', $entries['etr']['ids']['en'], EvidenceBindings::META_KEY ),
	);
}

/**
 * Set intrinsic dimensions on the original capability and contact images.
 *
 * @param string $html Stored page content.
 * @param string $slug English page slug.
 * @throws RuntimeException When the expected image set is incomplete.
 */
function image_sizes( string $html, string $slug ): string {
	$sizes = array(
		'lk-about-capability-linker-team-in-barleben.webp' => array( 1920, 1080 ),
		'linker-warehouse-logistics-engineer-inventory-management-desk.webp' => array( 1492, 1054 ),
		'lk-commissioning-engineers-at-outdoor-cabinet.webp' => array( 443, 590 ),
		'linker-unit-certificate-vde-ar-n-4110.webp'       => array( 1920, 1080 ),
		'solar-equipment-freight-truck-loading-forklift-warehouse.webp' => array( 810, 1080 ),
		'lk-about-capability-customer-with-linker-at-a-utility-bess-project.webp' => array( 2400, 1350 ),
		'lk-about-capability-customer-and-linker-working-through-a-project-at-the.webp' => array( 2400, 1350 ),
		'lk-contact-linker-team-in-barleben-with-goodwe-crrc-and-pylontech.webp' => array( 2400, 1800 ),
	);
	$tags  = new \WP_HTML_Tag_Processor( $html );
	$found = array();
	while ( $tags->next_tag( array( 'tag_name' => 'IMG' ) ) ) {
		$file = basename( (string) $tags->get_attribute( 'src' ) );
		if ( ! isset( $sizes[ $file ] ) ) {
			continue;
		}
		list( $width, $height ) = $sizes[ $file ];
		$tags->set_attribute( 'width', (string) $width );
		$tags->set_attribute( 'height', (string) $height );
		if ( 'lk-about-capability-linker-team-in-barleben.webp' === $file ) {
			$tags->set_attribute( 'loading', 'eager' );
		} else {
			$tags->set_attribute( 'loading', 'lazy' );
			$tags->set_attribute( 'decoding', 'async' );
		}
		$found[] = $file;
	}
	if ( count( array_unique( $found ) ) !== ( 'contact' === $slug ? 2 : 7 ) ) {
		throw new RuntimeException( esc_html( 'Expected page images missing from ' . $slug ) );
	}
	return $tags->get_updated_html();
}

/**
 * Insert the capability link into its reviewed section and update image sizes.
 *
 * @param string $html Stored page content.
 * @param string $slug English page slug.
 * @param string $lang Page language.
 * @throws RuntimeException When the placement or translation no longer resolves.
 */
function page_copy( string $html, string $slug, string $lang ): string {
	if ( 'about' !== $slug ) {
		$html = image_sizes( $html, $slug );
	}
	if ( 'capability' === $slug ) {
		return $html;
	}
	$url = \Linker\Commerce\Presentation\PageUrls::translated( 'about/capability', $lang );
	if ( '' === $url ) {
		throw new RuntimeException( esc_html( 'Missing Capability page for ' . $lang ) );
	}
	$href = esc_url( wp_make_link_relative( $url ) );
	if ( 'about' === $slug ) {
		$text    = 'de' === $lang ? 'Mehr zu Systemprüfung, Netzzertifikaten und Logistik ab Barleben →' : 'Explore our engineering checks, grid certificates, and Barleben logistics →';
		$link    = '<p class="lk-inline-link"><a href="' . $href . '">' . esc_html( $text ) . '</a></p>';
		$pattern = '~(id="pillars">\s*<div class="wrap">\s*<div class="section-head">.*?</p>)~s';
	} else {
		$text    = 'de' === $lang ? 'Leistungsfähigkeit & Logistik ab Barleben ↗' : 'Engineering capability & Barleben logistics ↗';
		$link    = '<div><a href="' . $href . '">' . esc_html( $text ) . '</a></div>';
		$pattern = '~(id="cp-afterword-title">[^<]*</h2>\s*<p>[^<]*</p>\s*<div><a href="mailto:sales@de-linker\.com">[^<]*</a></div>)~';
	}
	if ( str_contains( $html, $link ) ) {
		return $html;
	}
	$html = preg_replace( $pattern, '$1' . $link, $html, -1, $count );
	if ( null === $html || 1 !== $count ) {
		throw new RuntimeException( esc_html( 'Missing or repeated Capability link placement on ' . $slug . '/' . $lang ) );
	}
	return $html;
}

/**
 * Apply the reviewed fields or restore the snapshot in one native transaction.
 *
 * @param array<string,mixed> $before Original snapshot for this site.
 * @param bool                $apply Whether to apply or restore the values.
 * @throws RuntimeException When a field or its owner changed, or a write failed.
 */
function migrate( array $before, bool $apply ): void {
	$current = snapshot();
	if ( $before['site'] !== $current['site'] || array_keys( $before['entries'] ) !== array_keys( $current['entries'] ) ) {
		throw new RuntimeException( 'Snapshot does not match the site or editorial inventory.' );
	}
	$copy       = array_merge( ...array_values( search_copy() ) );
	$translator = translator();
	pause_translation();
	NativeTransaction::run(
		static function () use ( $before, $current, $copy, $translator, $apply ): void {
			foreach ( $before['entries'] as $slug => $row ) {
				$live = $current['entries'][ $slug ];
				if ( $row['ids'] !== $live['ids'] ) {
					throw new RuntimeException( esc_html( 'Translated object identity changed: ' . $slug ) );
				}
				$desired = $row['values'];
				if ( isset( $copy[ $slug ] ) ) {
					$desired = $copy[ $slug ];
				} elseif ( 'etr' === $slug ) {
					require_once __DIR__ . '/batch-t5-etr-parity.php';
					$desired['en'] = array_replace( $desired['en'], batch_t5_etr_meta( $row['ids']['en'], $row['values']['en'] ) );
				} else {
					foreach ( $row['ids'] as $lang => $id ) {
						$desired[ $lang ]['post_content'] = page_copy( $row['values'][ $lang ]['post_content'], $slug, $lang );
					}
				}
				foreach ( $desired as $lang => $fields ) {
					$id = $row['ids'][ $lang ];
					foreach ( $fields as $key => $updated ) {
						$original = $row['values'][ $lang ][ $key ];
						$target   = $apply ? $updated : $original;
						$stored   = $live['values'][ $lang ][ $key ];
						if ( $target === $stored ) {
							continue;
						}
						if ( $stored !== $original && $stored !== $updated ) {
							throw new RuntimeException( esc_html( "Field changed since snapshot: $slug/$lang/$key" ) );
						}
						if ( in_array( $key, array( 'post_content', 'post_excerpt' ), true ) ) {
							$result = wp_update_post(
								wp_slash(
									array(
										'ID' => $id,
										$key => $target,
									)
								),
								true
							);
							if ( is_wp_error( $result ) || get_post_field( $key, $id, 'raw' ) !== $target ) {
								throw new RuntimeException( esc_html( "Could not write $slug/$lang/$key" ) );
							}
						} else {
							write_meta( $row['kind'], $id, $key, $target );
						}
					}
				}
				if ( 'etr' === $slug ) {
					if ( $apply ) {
						EvidenceBindings::capture( $row['ids']['en'] );
					} else {
						write_meta( 'post', $row['ids']['en'], EvidenceBindings::META_KEY, $before['figure_bindings'] );
					}
				}
				if ( $apply ) {
					$translator->adopt_current( $row['kind'], $row['ids']['en'] );
				} else {
					foreach ( $row['state'] as $lang => $fields ) {
						foreach ( $fields as $key => $original ) {
							write_meta( $row['kind'], $row['ids'][ $lang ], $key, $original );
						}
					}
				}
			}
		}
	);
}

$linker_commerce_t5_operation = $args[0] ?? '';
if ( 'snapshot' === $linker_commerce_t5_operation ) {
	echo wp_json_encode( snapshot(), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR ) . "\n";
} elseif ( isset( $args[1] ) && in_array( $linker_commerce_t5_operation, array( 'apply', 'restore' ), true ) ) {
	migrate( read_json( $args[1] ), 'apply' === $linker_commerce_t5_operation );
	WP_CLI::success( 'Editorial migration: ' . $linker_commerce_t5_operation );
} else {
	WP_CLI::error( 'Usage: snapshot | apply <snapshot> | restore <snapshot>' );
}
