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
 * the product's documents — plus the engineering overlay, the compatibility
 * contract itself and its version. The contract travels with the feed so the
 * engine's nightly sync can refresh LINKER_ENGINE_COMPATIBILITY from the same
 * fetch; the Solution Configurator's engine reads nothing else.
 */
final class EngineeringFeed {

	/**
	 * The feed's schema version, the contract with the engine (#14).
	 */
	private const SCHEMA_VERSION = 1;

	/**
	 * Hosts a production citation may name. Not widened: an instance address
	 * is hosted only when it is this site, after pull load's search-replace.
	 *
	 * @var list<string>
	 */
	private const PRODUCTION_HOSTS = array( 'de-linker.com', 'www.de-linker.com' );

	/**
	 * The origin the engine's feed schema accepts
	 * (services/engine/schemas/feed.schema.json hostedUrl).
	 */
	private const CANONICAL_ORIGIN = 'https://de-linker.com';

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
		// The contract itself, so the engine's sync refreshes its copy from the
		// same fetch; a broken file stays out of the feed (it reads as null),
		// and the engine keeps the contract it already has.
		$compatibility = EngineeringData::json( EngineeringData::COMPATIBILITY_FILE );
		if ( null !== $compatibility ) {
			$feed['compatibility'] = $compatibility;
		}
		$ids = self::product_ids( $since );
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
				'citation' => self::feed_citation( $entry['citation'] ),
			);
		}

		return $cited;
	}

	/**
	 * Whether a citation names a document we host.
	 *
	 * On production that is a URL on de-linker.com or www.de-linker.com.
	 * Pull load rewrites every live address to the instance
	 * (tools/pull/src/linker_pull/load.py replacements()) and then requires
	 * none of those addresses left, so a local citation cannot keep the
	 * production host. The same path on this site is the same document.
	 *
	 * @param mixed $citation The citation of a figure entry.
	 */
	private static function is_hosted_citation( mixed $citation ): bool {
		$url = self::citation_url( $citation );

		return null !== $url && ( self::is_production_url( $url ) || self::is_this_site( $url ) );
	}

	/**
	 * The citation URL, or null when the entry does not name one.
	 *
	 * @param mixed $citation The citation of a figure entry.
	 */
	private static function citation_url( mixed $citation ): ?string {
		if ( ! is_array( $citation ) || ! is_string( $citation['url'] ?? null ) || '' === $citation['url'] ) {
			return null;
		}

		return $citation['url'];
	}

	/**
	 * The citation as the feed names it. An instance address is the same path
	 * on the canonical origin: the engine schema refuses any other host, and
	 * the stored value is not changed.
	 *
	 * @param mixed $citation The stored citation.
	 * @return array<string, mixed>
	 */
	private static function feed_citation( mixed $citation ): array {
		if ( ! is_array( $citation ) ) {
			return array();
		}
		if ( is_string( $citation['url'] ?? null ) ) {
			$citation['url'] = self::feed_url( $citation['url'] );
		}

		return $citation;
	}

	/**
	 * A document or citation URL as the feed names it. Production URLs are
	 * already the form the engine accepts and are returned unchanged.
	 *
	 * @param string $url The stored URL.
	 */
	private static function feed_url( string $url ): string {
		if ( ! self::is_this_site( $url ) || self::is_production_url( $url ) ) {
			return $url;
		}
		$path = self::url_part( $url, PHP_URL_PATH );
		if ( ! str_starts_with( $path, '/' ) ) {
			return $url;
		}
		$named = self::CANONICAL_ORIGIN . $path;
		$query = self::url_part( $url, PHP_URL_QUERY );
		if ( '' !== $query ) {
			$named .= '?' . $query;
		}
		$fragment = self::url_part( $url, PHP_URL_FRAGMENT );
		if ( '' !== $fragment ) {
			$named .= '#' . $fragment;
		}

		return $named;
	}

	/**
	 * Whether the URL is on a production host. The list is closed: a local
	 * address does not pass here, including when this site is production.
	 *
	 * @param string $url The URL.
	 */
	private static function is_production_url( string $url ): bool {
		return in_array( self::host_of( $url ), self::PRODUCTION_HOSTS, true );
	}

	/**
	 * Whether the URL is this site's own origin. Pull load writes that origin
	 * into every former live address; home_url() is the same value.
	 *
	 * @param string $url The URL.
	 */
	private static function is_this_site( string $url ): bool {
		$home = self::site_origin();

		return '' !== $home && self::origin_of( $url ) === self::origin_of( $home );
	}

	/**
	 * This site's origin, empty when WordPress is not loaded (the unit tests).
	 */
	private static function site_origin(): string {
		if ( ! function_exists( 'home_url' ) ) {
			return '';
		}
		return home_url();
	}

	/**
	 * Scheme, host and port, lowercased. An empty string is not an origin.
	 *
	 * @param string $url The URL.
	 */
	private static function origin_of( string $url ): string {
		$parts = self::url_parts( $url );
		if ( ! isset( $parts['host'], $parts['scheme'] ) || ! is_string( $parts['host'] ) || ! is_string( $parts['scheme'] ) ) {
			return '';
		}
		$origin = strtolower( $parts['scheme'] ) . '://' . strtolower( $parts['host'] );
		if ( isset( $parts['port'] ) ) {
			$origin .= ':' . (int) $parts['port'];
		}

		return $origin;
	}

	/**
	 * The URL's host, lowercased, or an empty string.
	 *
	 * @param string $url The URL.
	 */
	private static function host_of( string $url ): string {
		$parts = self::url_parts( $url );
		$host  = $parts['host'] ?? null;

		return is_string( $host ) ? strtolower( $host ) : '';
	}

	/**
	 * One parse_url component as a string, empty when absent.
	 *
	 * @param string $url       The URL.
	 * @param int    $component A PHP_URL_* component.
	 */
	private static function url_part( string $url, int $component ): string {
		$parts = self::url_parts( $url );
		$key   = array(
			PHP_URL_PATH     => 'path',
			PHP_URL_QUERY    => 'query',
			PHP_URL_FRAGMENT => 'fragment',
		)[ $component ] ?? '';
		$value = '' === $key ? null : ( $parts[ $key ] ?? null );

		return is_string( $value ) ? $value : '';
	}

	/**
	 * The URL split into components. The native function is what the check
	 * needs, and it works without WordPress loaded.
	 *
	 * @param string $url The URL.
	 * @return array<string, mixed>
	 */
	private static function url_parts( string $url ): array {
		// phpcs:ignore WordPress.WP.AlternativeFunctions.parse_url_parse_url -- see the method docblock.
		$parts = parse_url( $url );

		return is_array( $parts ) ? $parts : array();
	}

	/**
	 * The product's documents, as the migration wrote them. An instance
	 * address is named on the canonical origin, the same way a figure is.
	 *
	 * @param int $product_id Product ID.
	 * @return list<array<string, mixed>>
	 */
	private static function documents( int $product_id ): array {
		$documents = get_post_meta( $product_id, EngineeringData::DOCUMENTS_META_KEY, true );
		if ( is_string( $documents ) ) {
			$documents = json_decode( $documents, true );
		}
		if ( ! is_array( $documents ) ) {
			return array();
		}
		$listed = array();
		foreach ( array_values( $documents ) as $document ) {
			if ( is_array( $document ) && is_string( $document['url'] ?? null ) ) {
				$document['url'] = self::feed_url( $document['url'] );
			}
			$listed[] = $document;
		}

		return $listed;
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
