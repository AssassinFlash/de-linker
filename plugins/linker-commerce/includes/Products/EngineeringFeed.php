<?php
/**
 * Building the engineering feed.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products;

/**
 * The engineering feed of docs/specs/8-engineering-data.md (target shape 5,
 * services/engine/schemas/feed.schema.json): every published product with the
 * model, brand and series the product data states, the five selection facts
 * of #7, the figure entries that carry a citation of a document we host, and
 * the product's documents — plus the engineering overlay and the version of
 * the compatibility contract. The Solution Configurator's engine reads
 * nothing else.
 */
final class EngineeringFeed {

	/**
	 * The feed's schema version, the contract with the engine (#14).
	 */
	private const SCHEMA_VERSION = 1;

	/**
	 * The taxonomies the feed names an item by: one term each, by name.
	 */
	private const NAME_TAXONOMIES = array(
		'model'  => 'pa_model',
		'brand'  => 'pa_brand',
		'series' => 'pa_series',
	);

	/**
	 * The feed: the envelope with every published product, or only those
	 * changed after a moment.
	 *
	 * @param string|null $since GMT moment (anything strtotime() reads); only
	 *                             products modified after it, all when null.
	 * @return array<string, mixed>
	 */
	public static function feed( ?string $since = null ): array {
		$feed = array(
			'schema_version'        => self::SCHEMA_VERSION,
			'generated_at'          => gmdate( 'c' ),
			'compatibility_version' => EngineeringData::compatibility_version(),
			'overlay'               => EngineeringData::json( EngineeringData::OVERLAY_FILE )['overlay'] ?? array(),
			'products'              => array(),
		);
		$ids  = self::product_ids( $since );
		// One bulk load each: the items below read every product's meta and
		// taxonomy terms, not one database round-trip per item.
		update_postmeta_cache( $ids );
		update_object_term_cache( $ids, 'product' );
		foreach ( $ids as $id ) {
			$item = self::item( $id );
			if ( null !== $item ) {
				$feed['products'][] = $item;
			}
		}

		return $feed;
	}

	/**
	 * One feed item, null when the post is not a published product anymore.
	 *
	 * @param int $product_id Product ID.
	 * @return array<string, mixed>|null
	 */
	public static function item( int $product_id ): ?array {
		if ( 'product' !== get_post_type( $product_id ) || 'publish' !== get_post_status( $product_id ) ) {
			return null;
		}
		$facts   = SelectionFacts::for_product( $product_id )->to_array();
		$product = wc_get_product( $product_id );
		$item    = array(
			'id'           => $product_id,
			'sku'          => $product instanceof \WC_Product ? $product->get_sku() : '',
			'device_class' => $facts['device_class'],
			'application'  => $facts['application'],
			'phase'        => $facts['phase'],
			// The five #7 facts the feed schema requires; kwh_range is null when the figures state no range.
			'ac_power_kw'  => $facts['ac_power_kw'],
			'pv_input_kw'  => $facts['pv_input_kw'],
			'usable_kwh'   => $facts['usable_kwh'],
			'nominal_kwh'  => $facts['nominal_kwh'],
			'kwh_range'    => $facts['kwh_range'] ?? null,
			'figures'      => (object) self::figures( $product_id ),
			'documents'    => self::documents( $product_id ),
		);
		foreach ( self::NAME_TAXONOMIES as $field => $taxonomy ) {
			$item[ $field ] = self::term_name( $product_id, $taxonomy );
		}

		return $item;
	}

	/**
	 * The figure entries that carry a citation of a document we host
	 * (docs/specs/8-engineering-data.md: a value without one does not enter
	 * the feed). Everything else about the entry travels as it is stored.
	 *
	 * @param int $product_id Product ID.
	 * @return array<string, array<string, mixed>> Keyed by figure key; the item casts it so an empty set serializes as {} (feed.schema.json), never [].
	 */
	private static function figures( int $product_id ): array {
		$figures = get_post_meta( $product_id, SelectionFacts::FIGURES_META_KEY, true );
		if ( is_string( $figures ) ) {
			$figures = json_decode( $figures, true );
		}
		if ( ! is_array( $figures ) ) {
			return array();
		}
		$cited = array();
		foreach ( $figures as $key => $entry ) {
			if ( ! is_array( $entry ) || ! self::is_hosted_citation( $entry['citation'] ?? null ) ) {
				continue;
			}
			// The feed names the value, its unit and its citation; the storage's own fields stay storage-side.
			$cited[ (string) $key ] = array(
				'value'    => $entry['value'] ?? null,
				'unit'     => $entry['unit'] ?? null,
				'citation' => $entry['citation'],
			);
		}

		return $cited;
	}

	/**
	 * Whether a citation names a document we host: a URL on our own site.
	 *
	 * @param mixed $citation The citation of a figure entry.
	 */
	private static function is_hosted_citation( mixed $citation ): bool {
		if ( ! is_array( $citation ) || ! is_string( $citation['url'] ?? null ) ) {
			return false;
		}
		// phpcs:ignore WordPress.WP.AlternativeFunctions.parse_url_parse_url -- the host the native function answers is all the check needs, and it works without WordPress loaded.
		$host = parse_url( (string) $citation['url'], PHP_URL_HOST );

		return is_string( $host ) && in_array( strtolower( $host ), array( 'de-linker.com', 'www.de-linker.com' ), true );
	}

	/**
	 * The product's documents, as the migration wrote them.
	 *
	 * @param int $product_id Product ID.
	 * @return list<array<string, mixed>>
	 */
	private static function documents( int $product_id ): array {
		$documents = get_post_meta( $product_id, EngineeringData::DOCUMENTS_META_KEY, true );
		if ( is_string( $documents ) ) {
			$documents = json_decode( $documents, true );
		}

		return is_array( $documents ) ? array_values( $documents ) : array();
	}

	/**
	 * The name of the product's single term in a taxonomy, null without one.
	 *
	 * @param int    $product_id Product ID.
	 * @param string $taxonomy   Taxonomy.
	 */
	private static function term_name( int $product_id, string $taxonomy ): ?string {
		$terms = get_the_terms( $product_id, $taxonomy );
		if ( ! is_array( $terms ) || 1 !== count( $terms ) ) {
			return null;
		}
		$name = reset( $terms )->name;

		return '' === $name ? null : $name;
	}

	/**
	 * A moment as a plain GMT string. strtotime() reads the moment with its
	 * own offset; gmdate() answers it in GMT, which is what the query's GMT
	 * column is compared against.
	 *
	 * @param string $since The validated moment.
	 */
	private static function gmt( string $since ): string {
		$moment = strtotime( $since );

		return false === $moment ? '' : gmdate( 'Y-m-d H:i:s', $moment );
	}

	/**
	 * The published products, oldest first; with $since only those modified
	 * after it.
	 *
	 * @param string|null $since GMT moment, or null for all.
	 * @return list<int>
	 */
	private static function product_ids( ?string $since ): array {
		$args = array(
			'post_type'      => 'product',
			'post_status'    => 'publish',
			'fields'         => 'ids',
			'posts_per_page' => -1,
			'orderby'        => 'ID',
			'order'          => 'ASC',
		);
		if ( null !== $since ) {
			$args['date_query'] = array(
				array(
					'column'    => 'post_modified_gmt',
					// A plain GMT string: WordPress would otherwise read an
					// offset-bearing moment in the site's timezone and shift it
					// twice when comparing against the GMT column.
					'after'     => self::gmt( $since ),
					'inclusive' => false,
				),
			);
		}
		return array_values( array_map( 'intval', get_posts( $args ) ) );
	}
}
