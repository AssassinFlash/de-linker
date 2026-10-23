<?php
/**
 * Engineering reference records live in Woo without becoming sale products.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products;

use WC_Product;

/** Native product fields distinguish a reference input from current supply. */
final class EngineeringReference {
	public const ROLE_META_KEY = '_linker_engineering_role';
	public const ID_META_KEY   = '_linker_engineering_id';
	public const PV_MODULE     = 'reference_pv_module';

	/** Required fields of the engine's native PvModule.from_overlay loader. */
	private const REQUIRED_NUMBERS = array( 'pmax_w', 'voc_v', 'vmpp_v', 'isc_a', 'impp_a', 'beta_voc_pct_per_c', 'max_series_fuse_a' );

	/**
	 * A reference missing a required bound input stays out of the ready feed.
	 *
	 * @param array<string,array<string,mixed>> $figures Current bound Woo fields.
	 */
	public static function ready( array $figures ): bool {
		foreach ( self::REQUIRED_NUMBERS as $key ) {
			$value = $figures[ $key ]['value'] ?? null;
			if ( ! is_scalar( $value ) || 1 !== preg_match( '/-?[0-9]+(?:[.,][0-9]+)?/', str_replace( ' ', '', (string) $value ) ) ) {
				return false;
			}
		}
		$dimensions = $figures['dimensions_mm']['value'] ?? null;
		if ( ! is_string( $dimensions ) ) {
			return false;
		}
		$sides = array_filter( explode( 'x', str_replace( '×', 'x', $dimensions ) ), static fn ( string $side ): bool => 1 === preg_match( '/^[0-9]+(?:\.[0-9]+)?$/D', trim( $side ) ) );
		return count( $sides ) >= 2;
	}

	/**
	 * The canonical Woo role; ordinary products have an empty role.
	 *
	 * @param int $id Locale or source product ID.
	 */
	public static function role( int $id ): string {
		$role = get_post_meta( Publication::canonical_id( $id ), self::ROLE_META_KEY, true );
		return is_string( $role ) ? $role : '';
	}

	/**
	 * Whether this product supplies a reference input rather than a sales line.
	 *
	 * @param int $id Locale or source product ID.
	 */
	public static function is_reference( int $id ): bool {
		return self::PV_MODULE === self::role( $id );
	}

	/** Register ordinary Woo product administration, without another data source. */
	public function register(): void {
		add_action( 'woocommerce_product_options_general_product_data', array( $this, 'fields' ) );
		add_action( 'woocommerce_admin_process_product_object', array( $this, 'save' ) );
		add_action( 'woocommerce_after_product_object_save', array( $this, 'remove_category' ) );
		// Woo's force_default_term runs at 10; its batch repair uses the same
		// default-category schedule at 10. Preserve those for ordinary products.
		add_action( 'set_object_terms', array( $this, 'assigned_categories' ), 20, 4 );
		add_action( 'wc_schedule_update_product_default_cat', array( $this, 'remove_default_categories' ), 20 );
	}

	/** Role and stable engineering identity remain editable on the Woo product. */
	public function fields(): void {
		woocommerce_wp_select(
			array(
				'id'      => self::ROLE_META_KEY,
				'label'   => __( 'Engineering role', 'linker-commerce' ),
				'options' => array(
					''              => __( 'Product', 'linker-commerce' ),
					self::PV_MODULE => __( 'Reference PV module', 'linker-commerce' ),
				),
			)
		);
		woocommerce_wp_text_input(
			array(
				'id'    => self::ID_META_KEY,
				'label' => __( 'Engineering ID', 'linker-commerce' ),
			)
		);
	}

	/**
	 * Woo has already verified product-edit capability and nonce for this hook.
	 *
	 * @param WC_Product $product Native object about to be saved.
	 */
	public function save( WC_Product $product ): void {
		// phpcs:disable WordPress.Security.NonceVerification.Missing -- Native Woo product save owns nonce and capability validation.
		if ( ! isset( $_POST[ self::ROLE_META_KEY ] ) || ! is_string( $_POST[ self::ROLE_META_KEY ] ) ) {
			return;
		}
		$role = sanitize_text_field( wp_unslash( $_POST[ self::ROLE_META_KEY ] ) );
		if ( ! in_array( $role, array( '', self::PV_MODULE ), true ) ) {
			return;
		}
		$id = isset( $_POST[ self::ID_META_KEY ] ) && is_string( $_POST[ self::ID_META_KEY ] ) ? sanitize_text_field( wp_unslash( $_POST[ self::ID_META_KEY ] ) ) : '';
		// phpcs:enable
		$product->update_meta_data( self::ROLE_META_KEY, $role );
		$product->update_meta_data( self::ID_META_KEY, $id );
		if ( self::PV_MODULE === $role ) {
			self::configure( $product );
		}
	}

	/**
	 * A reference has no selling identity, price or product classification.
	 *
	 * @param WC_Product $product Native product being created/maintained.
	 */
	public static function configure( WC_Product $product ): void {
		$product->set_catalog_visibility( 'hidden' );
		$product->set_virtual( true );
		$product->set_sku( '' );
		$product->set_regular_price( '' );
		$product->set_sale_price( '' );
		$product->set_price( '' );
		$product->set_category_ids( array() );
	}

	/**
	 * Woo supplies its default category when saving an empty category list.
	 * Keep the reference outside product classifications after that native save.
	 *
	 * @param WC_Product $product Saved reference or ordinary product.
	 */
	public function remove_category( WC_Product $product ): void {
		if ( self::is_reference( $product->get_id() ) ) {
			// A set-to-empty immediately calls WC_Post_Data::force_default_term.
			// Native unlink preserves cache/count hooks without another set event.
			wp_delete_object_term_relationships( $product->get_id(), 'product_cat' );
		}
	}

	/**
	 * Normal taxonomy writers cannot classify a reference as a sale product.
	 *
	 * @param int               $id Product ID.
	 * @param array<int|string> $terms Assigned terms.
	 * @param array<int>        $term_ids Term taxonomy identities.
	 * @param string            $taxonomy Changed taxonomy.
	 */
	public function assigned_categories( int $id, array $terms, array $term_ids, string $taxonomy ): void {
		unset( $terms, $term_ids );
		if ( 'product_cat' === $taxonomy && self::is_reference( $id ) ) {
			wp_delete_object_term_relationships( $id, 'product_cat' );
		}
	}

	/** Woo's native batch default repair uses SQL; unlink only reference records after it. */
	public function remove_default_categories(): void {
		$ids = get_posts(
			array(
				'post_type'                   => 'product',
				'post_status'                 => array( 'publish', 'draft', 'pending', 'private', 'future', 'trash' ),
				'fields'                      => 'ids',
				'posts_per_page'              => -1,
				'suppress_filters'            => true,
				'lang'                        => '',
				'linker_publication_internal' => true,
				'cache_results'               => false,
				'meta_key'                    => self::ROLE_META_KEY, // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_key -- Native scheduled repair of reference records only.
				'meta_value'                  => self::PV_MODULE, // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_value -- No public catalogue query.
			)
		);
		foreach ( $ids as $id ) {
			if ( self::is_reference( (int) $id ) ) {
				wp_delete_object_term_relationships( (int) $id, 'product_cat' );
			}
		}
	}
}
