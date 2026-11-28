<?php
/**
 * Published series and their model ratings in the requested language.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Storefront;

use Linker\Commerce\Presentation\PageUrls;
use Linker\Commerce\Products\CompatibilityIndex;
use Linker\Commerce\Products\Materials;
use Linker\Commerce\Products\Publication;
use Linker\Commerce\Products\SelectionFacts;

/** Shared membership and product figures for the PDP, archive and metadata. */
final class ProductGroupIndex {
	/**
	 * Localized product IDs to canonical records.
	 *
	 * @var array<int,array<string,mixed>>
	 */
	private array $records = array();
	/**
	 * Group identities.
	 *
	 * @var array<int,string>
	 */
	private array $ids = array();
	/**
	 * Group members.
	 *
	 * @var array<string,list<int>>
	 */
	private array $members = array();
	/**
	 * Group names.
	 *
	 * @var array<string,string>
	 */
	private array $names = array();
	/**
	 * Authorized ratings on this page.
	 *
	 * @var array<int,array<string,mixed>>
	 */
	private array $ratings = array();

	/**
	 * Current page's index.
	 *
	 * @param array<string,mixed>|null $manifest Published snapshot.
	 */
	public static function current( ?array $manifest = null ): self {
		static $instances = array();
		$manifest       ??= CompatibilityIndex::manifest();
		return $instances[ $manifest['source_revision'] . ':' . Materials::locale() ] ??= new self( $manifest );
	}

	/**
	 * Index the English series names under each published translation.
	 *
	 * @param array<string,mixed> $manifest Published snapshot.
	 */
	private function __construct( private readonly array $manifest ) {
		$records  = array_column( $manifest['products'], null, 'product_id' );
		$fallback = array();
		foreach ( $records as $source => $record ) {
			$id = $record['locale_product_ids'][ Materials::locale() ] ?? 0;
			if ( empty( $id ) || ! in_array( $id, $record['published_locale_ids'], true ) || ! empty( $record['engineering_role'] ) ) {
				continue;
			}
			$terms  = get_the_terms( $source, 'pa_series' );
			$series = is_array( $terms ) && $terms ? html_entity_decode( reset( $terms )->name, ENT_QUOTES | ENT_HTML5, 'UTF-8' ) : '';
			if ( '' === $series ) {
				$series = trim( (string) ( Materials::english_acf( $source )['product_series'] ?? '' ) );
			}
			if ( '' === $series || 0 === strcasecmp( $record['brand'], $series ) ) {
				if ( ! $fallback ) {
					$ids = array_keys( $records );
					foreach ( ( new ProductFamilies( $ids, 'en' ) )->rows( $ids ) as $family ) {
						$first = min( array_merge( array( $family['lead'] ), $family['ids'] ) );
						foreach ( $family['ids'] as $member ) {
							$fallback[ $member ] = $records[ $first ]['model'];
						}
					}
				}
				$series = $fallback[ $source ];
			}
			$brand                   = $record['brand'];
			$prefixed                = str_starts_with( strtolower( $series ), strtolower( $brand . ' ' ) );
			$key                     = PageUrls::root() . '#product-group-' . sanitize_title( $prefixed ? $series : $brand . '-' . $series );
			$this->ids[ $id ]        = $key;
			$this->names[ $key ]     = trim( ( $prefixed ? '' : $brand . ' ' ) . $series );
			$this->records[ $id ]    = $record;
			$this->members[ $key ][] = $id;
		}
	}

	/**
	 * Localized model record and its current, released selection data.
	 *
	 * @param int $id Localized product ID.
	 * @return array<string,mixed>
	 */
	public function rating( int $id ): array {
		if ( ! isset( $this->records[ $id ] ) ) {
			return array();
		}
		if ( ! isset( $this->ratings[ $id ] ) ) {
			$row                  = $this->records[ $id ];
			$source               = $row['product_id'];
			$figures              = Publication::figures_in_manifest( $source, $this->manifest );
			$facts                = SelectionFacts::from_figures( $source, $figures );
			$this->ratings[ $id ] = $row + $facts->to_array() + array(
				'figures' => $figures,
				'series'  => $this->names[ $this->ids[ $id ] ],
			);
		}
		return $this->ratings[ $id ];
	}

	/**
	 * Sorted same-language members, including the displayed model.
	 *
	 * @param int $id Localized product ID.
	 * @return list<int>
	 */
	public function members_for( int $id ): array {
		$ids = $this->members[ $this->ids[ $id ] ?? '' ] ?? array();
		usort(
			$ids,
			function ( int $a, int $b ): int {
				$left       = $this->rating( $a );
				$right      = $this->rating( $b );
				$comparison = self::size( $left ) <=> self::size( $right );
				return 0 !== $comparison ? $comparison : strnatcasecmp( $left['model'], $right['model'] );
			}
		);
		return $ids;
	}

	/**
	 * Power or capacity used to sort within the series.
	 *
	 * @param array<string,mixed> $rating Model rating.
	 */
	private static function size( array $rating ): float {
		foreach ( array( 'ac_power_kw', 'usable_kwh', 'nominal_kwh' ) as $key ) {
			if ( is_numeric( $rating[ $key ] ) ) {
				return (float) $rating[ $key ];
			}
		}
		return INF;
	}

	/**
	 * Stable series identifier shared by all translations.
	 *
	 * @param int $id Localized product ID.
	 */
	public function identity( int $id ): string {
		return $this->ids[ $id ] ?? '';
	}

	/**
	 * Public ProductGroup JSON-LD.
	 *
	 * @param int $id Localized product ID.
	 * @return array<string,mixed>
	 */
	public function schema( int $id ): array {
		$key = $this->identity( $id );
		if ( '' === $key ) {
			return array();
		}
		$de   = Materials::is_de();
		$node = array(
			'@context'       => 'https://schema.org',
			'@type'          => 'ProductGroup',
			'@id'            => $key,
			'productGroupID' => $key,
			'inLanguage'     => Materials::locale(),
			'name'           => $this->names[ $key ] . ( $de ? '-Serie' : ' Series' ),
			'brand'          => array(
				'@type' => 'Brand',
				'name'  => $this->records[ $id ]['brand'],
			),
			'hasVariant'     => array(),
		);
		foreach ( $this->members_for( $id ) as $member ) {
			$url                  = (string) get_permalink( $member );
			$node['hasVariant'][] = array(
				'@id'  => $url . '#product',
				'url'  => $url,
				'name' => html_entity_decode( get_the_title( $member ), ENT_QUOTES | ENT_HTML5, 'UTF-8' ),
				'sku'  => (string) get_post_meta( $this->records[ $member ]['product_id'], '_sku', true ),
			);
		}
		if ( count( $node['hasVariant'] ) > 1 ) {
			$node['variesBy'] = array( 'https://schema.org/size' );
		}
		return $node;
	}

	/**
	 * Representative IDs of multi-model series on an unfiltered term archive.
	 *
	 * @return list<int>
	 */
	public static function archive_groups(): array {
		if ( ! is_tax( array( 'product_cat', 'product_brand' ) ) || is_paged() ) {
			return array();
		}
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended -- This public archive only reads the facet and page keys.
		$query   = array_keys( $_GET );
		$filters = new ProductFilters();
		if ( $filters->requested() || 'recommended' !== $filters->requested_sort() || in_array( 'product-page', $query, true ) || preg_grep( '/^(?:filter_|query_type_)/', $query ) ) {
			return array();
		}
		$groups = array();
		$index  = self::current();
		foreach ( $filters->archive_product_ids() as $id ) {
			$key = $index->identity( $id );
			if ( count( $index->members[ $key ] ?? array() ) > 1 ) {
				$groups[ $key ] ??= $id;
			}
		}
		return array_values( $groups );
	}
}
