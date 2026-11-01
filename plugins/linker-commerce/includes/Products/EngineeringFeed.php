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
	 * @phpstan-impure
	 */
	public static function feed( ?string $since = null ): array {
		$publication = Publication::manifest();
		$feed        = array(
			'source_revision'           => $publication['source_revision'],
			'compatibility_revision'    => $publication['compatibility_revision'],
			'schema_version'            => self::SCHEMA_VERSION,
			'figure_projection_version' => 2,
			'generated_at'              => gmdate( 'c' ),
			'compatibility_version'     => 'missing',
			'overlay'                   => self::references( $publication ),
			'products'                  => array(),
		);
		// Use the same current Woo authority read as product/document projection.
		// An invalid declaration envelope cannot fall back to a shipped contract.
		$compatibility = EngineeringData::compatibility( $publication );
		if ( null !== $compatibility ) {
			$feed['compatibility']         = $compatibility;
			$feed['compatibility_version'] = $compatibility['version'];
			$feed['compatibility_origin']  = 'woocommerce';
		}
		$ids = self::product_ids( $since );
		// One bulk load each: the items below read every product's meta and
		// taxonomy terms, not one database round-trip per item.
		update_postmeta_cache( $ids );
		update_object_term_cache( $ids, 'product' );
		foreach ( $ids as $id ) {
			$item = self::item( $id, $publication );
			if ( null !== $item ) {
				$feed['products'][] = $item;
			}
		}

		return $feed;
	}

	/**
	 * One feed item, null when the post is not a published product anymore.
	 *
	 * @param int                      $product_id Product ID.
	 * @param array<string,mixed>|null $publication Current authority snapshot.
	 * @return array<string, mixed>|null
	 */
	public static function item( int $product_id, ?array $publication = null ): ?array {
		if ( ! Publication::is_published( $product_id ) || Publication::canonical_id( $product_id ) !== $product_id || EngineeringReference::is_reference( $product_id ) ) {
			return null;
		}
		$publication ??= Publication::manifest();
		$permission    = array_column( $publication['products'], null, 'product_id' )[ $product_id ] ?? null;
		if ( null === $permission ) {
			return null;
		}
		$authorized_figures = self::figures( $product_id, $publication );
		$facts              = SelectionFacts::from_figures( $product_id, $authorized_figures )->to_array();
		$product            = wc_get_product( $product_id );
		$item               = array(
			'id'                   => $product_id,
			'canonical_product_id' => $product_id,
			'product_revision'     => $permission['product_revision'],
			'sku'                  => $product instanceof \WC_Product ? $product->get_sku() : '',
			'device_class'         => $facts['device_class'],
			'application'          => $facts['application'],
			'phase'                => $facts['phase'],
			// The five #7 facts the feed schema requires; kwh_range is null when the figures state no range.
			'ac_power_kw'          => $facts['ac_power_kw'],
			'pv_input_kw'          => $facts['pv_input_kw'],
			'usable_kwh'           => $facts['usable_kwh'],
			'nominal_kwh'          => $facts['nominal_kwh'],
			'kwh_range'            => $facts['kwh_range'] ?? null,
			'figures'              => (object) $authorized_figures,
			'documents'            => self::documents( $product_id, $publication ),
		);
		foreach ( self::NAME_TAXONOMIES as $field => $taxonomy ) {
			$item[ $field ] = self::term_name( $product_id, $taxonomy );
		}

		$contents = Publication\PackageContents::projection( $product_id, $publication );
		if ( null !== $contents ) {
			$item['package_contents'] = $contents;
		}

		$installation = Publication\InstallationFacts::projection( $product_id, $publication );
		if ( null !== $installation ) {
			$item['installation_facts'] = $installation;
		}

		return $item;
	}

	/**
	 * Reference inputs are ordinary current Woo records with bound evidence.
	 *
	 * @param array<string,mixed> $publication Current authority read.
	 * @return list<array<string,mixed>>
	 */
	private static function references( array $publication ): array {
		$references = array();
		foreach ( $publication['products'] as $product ) {
			$role = $product['engineering_role'] ?? '';
			if ( ! in_array( $role, EngineeringReference::ROLES, true ) || ! is_string( $product['engineering_id'] ?? null ) || '' === $product['engineering_id'] ) {
				continue;
			}
			$id      = $product['product_id'];
			$figures = self::figures( $id, $publication );
			$cable   = EngineeringReference::CABLE === $role ? Publication\CableFacts::projection( $id, $publication ) : null;
			if ( EngineeringReference::CABLE === $role ? null === $cable : ! EngineeringReference::ready( $figures ) ) {
				continue;
			}
			$references[] = array(
				'id'                   => $product['engineering_id'],
				'kind'                 => EngineeringReference::CABLE === $role ? 'cable' : 'pv_module',
				'brand'                => $product['brand'],
				'model'                => $product['model'],
				'canonical_product_id' => $id,
				'product_revision'     => $product['product_revision'],
				'reference_revision'   => $product['product_revision'],
				'figures'              => (object) $figures,
				'documents'            => self::documents( $id, $publication ),
				...( null === $cable ? array() : array( 'cable_facts' => $cable ) ),
			);
		}
		return $references;
	}

	/**
	 * The figure entries that carry a citation of a document we host
	 * (docs/specs/8-engineering-data.md: a value without one does not enter
	 * the feed). Everything else about the entry travels as it is stored.
	 *
	 * @param int                 $product_id Product ID.
	 * @param array<string,mixed> $publication Current authority snapshot.
	 * @return array<string, array<string, mixed>> Keyed by figure key; the item casts it so an empty set serializes as {} (feed.schema.json), never [].
	 */
	private static function figures( int $product_id, array $publication ): array {
		$cited = array();
		foreach ( Publication::figures_for( $product_id, $publication ) as $key => $entry ) {
			$cited[ $key ] = array(
				'value'    => $entry['value'] ?? null,
				'unit'     => $entry['unit'] ?? null,
				'citation' => self::feed_citation( $entry['citation'] ),
			);
			// Conditions remain part of the maintained fact. A numeric value
			// without its qualifier must never become an unconditional limit.
			foreach ( array( 'qualifier', 'evidence_refs', 'value_de', 'columns' ) as $field ) {
				if ( array_key_exists( $field, $entry ) ) {
					$cited[ $key ][ $field ] = $entry[ $field ];
				}
			}
		}

		return $cited;
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
	 * @param int                 $product_id Product ID.
	 * @param array<string,mixed> $publication Current authority snapshot.
	 * @return list<array<string, mixed>>
	 */
	private static function documents( int $product_id, array $publication ): array {
		$listed = array();
		foreach ( $publication['documents'] as $document ) {
			if ( in_array( $product_id, $document['product_ids'], true ) ) {
				$document['url']     = self::feed_url( $document['url'] );
				$document['aliases'] = array_map( array( self::class, 'feed_url' ), $document['aliases'] );
				$document['lang']    = self::document_language( $document['lang'] );
				$document['type']    = Materials::document_kind( $document['role'] ?? '', $document['type'] );
				$listed[]            = $document;
			}
		}
		return $listed;
	}

	/**
	 * Canonical language tags for the engine; unknown remains undetermined.
	 *
	 * @param string $label Stored Woo document language, left unchanged at source.
	 */
	private static function document_language( string $label ): string {
		$language = strtolower( trim( $label ) );
		if ( in_array( $language, array( 'mul', 'multi', 'en/de', 'de/en' ), true ) ) {
			return 'mul';
		}
		return 1 === preg_match( '/^[a-z]{2}$/D', $language ) ? $language : 'und';
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
			'post_type'        => 'product',
			'post_status'      => 'publish',
			'fields'           => 'ids',
			'posts_per_page'   => -1,
			'orderby'          => 'ID',
			'order'            => 'ASC',
			'suppress_filters' => true,
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
