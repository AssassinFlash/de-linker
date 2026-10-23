<?php
/**
 * The comparison of two to four products: one assembly, two entries.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products;

use Linker\Commerce\Abilities\ProductText;
use Linker\Commerce\Gating\CommerceState;
use Linker\Commerce\Storefront\ProductView;
use WC_Product;

/**
 * What a comparison of products is (docs/specs/19-tool-pages.md): the columns
 * of the products asked for, the dimension rows their device classes share,
 * and the technical rows of their own tables. Genie's
 * `linker/compare-products` ability and the standalone comparison page
 * (/compare-products/) both read this class, so the two entries cannot drift:
 * the ability returns its documented subset (columns and dimension rows), the
 * page renders the whole assembly.
 *
 * Battery energy and inverter output are different rows, never one mixed
 * "power" row (docs/specs/13-genie.md). Every value comes from the one
 * reading that owns it — the selection facts (#7) for a dimension, the
 * product's technical table for a table row — and a fact the product data
 * does not establish is `unknown`, which the page prints as an em dash.
 */
final class Comparison {
	/**
	 * Reads only currently authorized selection facts.
	 *
	 * @var callable(int):SelectionFactSet
	 */
	private $facts_reader;


	/**
	 * Most products one comparison holds; the address, the storage and the
	 * table all stop here (docs/specs/19-tool-pages.md).
	 */
	public const MAX_PRODUCTS = 4;

	/**
	 * Inverter-side dimensions, in display order.
	 */
	private const INVERTER_FIELDS = array( 'application', 'phase', 'ac_power_kw', 'pv_input_kw' );

	/**
	 * Battery-side dimensions, in display order.
	 */
	private const BATTERY_FIELDS = array( 'usable_kwh', 'nominal_kwh', 'kwh_range' );

	/**
	 * Device classes that show the inverter-side rows.
	 */
	private const INVERTER_CLASSES = array( 'inverters', 'all-in-one-systems' );

	/**
	 * Device classes that show the battery-side rows.
	 */
	private const BATTERY_CLASSES = array( 'home-storage', 'battery-systems', 'all-in-one-systems' );

	/**
	 * Row labels per language. The comparison table is built once per request
	 * language, so both are stored; the label of a fact is the same word the
	 * ability uses (docs/specs/13-genie.md).
	 */
	private const LABELS = array(
		'en' => array(
			'device_class' => 'Product category',
			'application'  => 'Application',
			'phase'        => 'Phases',
			'ac_power_kw'  => 'Rated AC power (kW)',
			'pv_input_kw'  => 'Maximum PV input (kW)',
			'usable_kwh'   => 'Usable energy (kWh)',
			'nominal_kwh'  => 'Nominal energy (kWh)',
			'kwh_range'    => 'Energy range (kWh)',
		),
		'de' => array(
			'device_class' => 'Produktkategorie',
			'application'  => 'Anwendung',
			'phase'        => 'Phasen',
			'ac_power_kw'  => 'Bemessungsleistung AC (kW)',
			'pv_input_kw'  => 'Maximale PV-Eingangsleistung (kW)',
			'usable_kwh'   => 'Nutzbare Energie (kWh)',
			'nominal_kwh'  => 'Nennenergie (kWh)',
			'kwh_range'    => 'Energiebereich (kWh)',
		),
	);

	/**
	 * The product view whose technical table the comparison carries.
	 *
	 * @var ProductView
	 */
	private readonly ProductView $view;

	/**
	 * Sets up the assembly.
	 *
	 * @param ProductView|null                    $view  Technical-table reading; the default one otherwise.
	 * @param CommerceState                       $state #11's price rule, shared with the view.
	 * @param callable(int):SelectionFactSet|null $facts_reader Current authorized facts.
	 */
	public function __construct( ?ProductView $view = null, private readonly CommerceState $state = new CommerceState(), ?callable $facts_reader = null ) {
		$this->facts_reader = $facts_reader ?? static fn( int $id ): SelectionFactSet => SelectionFacts::from_figures( Publication::canonical_id( $id ), Publication::figures_for( $id ) );
		$this->view         = $view ?? new ProductView( $state );
	}

	/**
	 * The selected products' columns and rows, in the order they were asked
	 * for. IDs that are not published products drop out; the rest keep their
	 * order and stop at MAX_PRODUCTS.
	 *
	 * @param int[]     $ids  Product IDs, in selection order.
	 * @param 'en'|'de' $lang Language of the labels and the product links.
	 * @return array{
	 *     products: list<array{product_id: int, title: string, url: string, facts: array<string, mixed>, sku: string, image: string, price: string, price_visible: bool, availability: string}>,
	 *     rows: list<array{field: string, label: string, values: array<int, mixed>}>,
	 *     specs: list<array{label: string, values: array<int, string>}>
	 * }
	 */
	public function of( array $ids, string $lang = 'en' ): array {
		$lang     = ProductText::lang( $lang );
		$products = array();
		$classes  = array();
		foreach ( self::published( $ids ) as $id ) {
			$facts      = ( $this->facts_reader )( $id );
			$classes[]  = $facts->device_class;
			$products[] = $this->column( $id, $lang, $facts );
		}

		return array(
			'products' => $products,
			'rows'     => array_values(
				array_map(
					fn( string $field ): array => $this->row( $field, $products, $lang ),
					$this->fields( $classes )
				)
			),
			'specs'    => $this->specs( $products ),
		);
	}

	/**
	 * The ordered selection an address asks for: product IDs, duplicates and
	 * non-numbers dropped, at most MAX_PRODUCTS of them.
	 *
	 * @param string $raw The `ids` query value, comma-separated.
	 * @return array{ids: list<int>, capped: bool} The selection, and whether
	 *         the address asked for more products than a comparison holds.
	 */
	public static function parse_ids( string $raw ): array {
		$ids  = array();
		$seen = array();
		foreach ( explode( ',', $raw ) as $token ) {
			$token = trim( $token );
			if ( '' === $token || 1 !== preg_match( '/^[0-9]+$/', $token ) ) {
				continue;
			}
			$id = (int) $token;
			if ( $id <= 0 || isset( $seen[ $id ] ) ) {
				continue;
			}
			$seen[ $id ] = true;
			$ids[]       = $id;
		}
		$capped = count( $ids ) > self::MAX_PRODUCTS;

		return array(
			'ids'    => array_slice( $ids, 0, self::MAX_PRODUCTS ),
			'capped' => $capped,
		);
	}

	/**
	 * The published products among the IDs, in the order given.
	 *
	 * @param int[] $ids Product IDs.
	 * @return list<int>
	 */
	private static function published( array $ids ): array {
		$out = array();
		foreach ( $ids as $id ) {
			$id = (int) $id;
			if ( $id > 0 && ! in_array( $id, $out, true ) && Publication::is_published( $id ) ) {
				$out[] = $id;
			}
		}

		return array_slice( $out, 0, self::MAX_PRODUCTS );
	}

	/**
	 * The product's image URL, '' without one.
	 *
	 * @param int $id Product ID.
	 */
	private static function image( int $id ): string {
		$url = get_the_post_thumbnail_url( $id, 'woocommerce_thumbnail' );

		return is_string( $url ) ? $url : '';
	}

	/**
	 * One column: the product's identity and what the visitor may see of it.
	 *
	 * @param int              $id    Product ID.
	 * @param 'en'|'de'        $lang  Language of the title and the link.
	 * @param SelectionFactSet $facts The product's selection facts.
	 * @return array{product_id: int, title: string, url: string, facts: array<string, mixed>, sku: string, image: string, price: string, price_visible: bool, availability: string}
	 */
	private function column( int $id, string $lang, SelectionFactSet $facts ): array {
		$product = wc_get_product( $id );
		$visible = $product instanceof WC_Product && $this->state->shows_price( $product );

		return array(
			'product_id'    => $id,
			'title'         => ProductText::title( $id, $lang ),
			'url'           => ProductText::url( $id, $lang ),
			'facts'         => $facts->to_array(),
			'sku'           => $product instanceof WC_Product ? (string) $product->get_sku() : '',
			'image'         => self::image( $id ),
			// The product page's own price line (ProductView::price_html): an
			// approved account on a product quoted per project reads "Quoted
			// per project", an account awaiting approval its own state (#242).
			'price'         => $product instanceof WC_Product
				? $this->view->price_html( $product )
				: __( 'Net price after partner sign-in', 'linker-commerce' ),
			'price_visible' => $visible,
			'availability'  => $product instanceof WC_Product && $product->is_in_stock()
				? __( 'In stock', 'linker-commerce' )
				: __( 'Currently unavailable', 'linker-commerce' ),
		);
	}

	/**
	 * Dimension keys for the classes on the table: inverter rows, then battery
	 * rows, never a shared "power" row.
	 *
	 * @param string[] $classes Device classes of the columns.
	 * @return string[]
	 */
	private function fields( array $classes ): array {
		$fields = array();
		if ( array() !== array_intersect( $classes, self::INVERTER_CLASSES ) ) {
			$fields = array_merge( $fields, self::INVERTER_FIELDS );
		}
		if ( array() !== array_intersect( $classes, self::BATTERY_CLASSES ) ) {
			$fields = array_merge( $fields, self::BATTERY_FIELDS );
		}
		if ( array() === $fields ) {
			$fields = array( 'device_class', 'application' );
		}

		return $fields;
	}

	/**
	 * One dimension row: field, label, values keyed by product ID.
	 *
	 * @param string                     $field    Fact key.
	 * @param list<array<string, mixed>> $products Columns.
	 * @param 'en'|'de'                  $lang     Language of the label.
	 * @return array{field: string, label: string, values: array<int, mixed>}
	 */
	private function row( string $field, array $products, string $lang ): array {
		$values = array();
		foreach ( $products as $product ) {
			$values[ (int) $product['product_id'] ] = ( $product['facts'][ $field ] ?? SelectionFactSet::UNKNOWN );
		}

		return array(
			'field'  => $field,
			'label'  => self::LABELS[ $lang ][ $field ] ?? $field,
			'values' => $values,
		);
	}

	/**
	 * The technical rows of the selected products' own tables, in the order
	 * the first product that states them gives: one row per label, an em dash
	 * where a product's table does not state it. The tables come from the one
	 * reading of the product page (ProductView), linker_specs once #8 writes
	 * it and the legacy data until then.
	 *
	 * @param list<array<string, mixed>> $products Columns.
	 * @return list<array{label: string, values: array<int, string>}>
	 */
	private function specs( array $products ): array {
		$out = array();
		foreach ( $products as $product ) {
			foreach ( $this->view->spec_groups( (int) $product['product_id'] ) as $group ) {
				foreach ( $group['rows'] as $row ) {
					if ( '' === trim( $row['label'] ) ) {
						continue;
					}
					if ( ! isset( $out[ $row['label'] ] ) ) {
						$out[ $row['label'] ] = array(
							'label'  => $row['label'],
							'values' => array(),
						);
					}
					$out[ $row['label'] ]['values'][ (int) $product['product_id'] ] = self::cell( $row );
				}
			}
		}

		return array_values( $out );
	}

	/**
	 * One technical cell: value and unit as the table stores them, the note
	 * beside them.
	 *
	 * @param array{label: string, value: string, unit: string, note: string, highlight: bool} $row Spec row.
	 */
	private static function cell( array $row ): string {
		$value = trim( $row['value'] . ' ' . $row['unit'] );
		$note  = trim( $row['note'] );

		return '' === $note ? $value : $value . ' (' . $note . ')';
	}
}
