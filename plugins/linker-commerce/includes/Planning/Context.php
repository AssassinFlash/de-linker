<?php
/**
 * Frozen project context follows native Woo lines into an inquiry.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Planning;

use Linker\Commerce\Account\DesignProof;
use Linker\Commerce\Products\Publication;
use WC_Order;
use WC_Order_Item_Product;
use WP_Error;

/** A copied cart field is only a reference to server-owned session context. */
final class Context {
	public const META = '_linker_planning_projects';
	/** HPOS orders_meta.meta_value is TEXT: wpdb reports a 65,535-byte limit. */
	private const MAX_META_BYTES = 65535;

	/**
	 * Resolve only contexts referenced by live native Woo lines.
	 *
	 * @return array<string,array<string,mixed>>
	 */
	public static function active(): array {
		$result = array();
		$stored = (array) WC()->session->get( DraftTransfer::CONTEXTS, array() );
		foreach ( WC()->cart->get_cart() as $line ) {
			$id = $line[ DraftTransfer::LINE_META ] ?? null;
			if ( is_string( $id ) && ! isset( $result[ $id ] ) && isset( $stored[ $id ] ) && self::valid( $stored[ $id ], $id ) ) {
				$result[ $id ] = $stored[ $id ];
			}
		}
		return $result;
	}

	/** Recheck current source permission before consuming an inquiry attempt. */
	public static function preflight(): ?WP_Error {
		$active = self::active();
		foreach ( WC()->cart->get_cart() as $line ) {
			$id = $line[ DraftTransfer::LINE_META ] ?? null;
			if ( null !== $id && ( ! is_string( $id ) || ! isset( $active[ $id ] ) ) ) {
				return new WP_Error( 'planning_context_unavailable', __( 'Your solution draft changed. Please review it and send your inquiry again.', 'linker-commerce' ), array( 'status' => 409 ) );
			}
		}
		foreach ( $active as $handoff ) {
			$error = ( new DesignProof() )->current_error(
				array(
					'kind'        => 'planning_products_v1',
					'publication' => $handoff['snapshot']['publication'],
				)
			);
			if ( $error instanceof WP_Error ) {
				return $error;
			}
		}
		return null;
	}

	/**
	 * Preserve the reference through native cart-to-order line creation.
	 *
	 * @param WC_Order_Item_Product $item Native order line.
	 * @param string                $key Native cart key.
	 * @param array<string,mixed>   $values Native cart line.
	 */
	public function line( WC_Order_Item_Product $item, string $key, array $values ): void {
		unset( $key );
		$id     = $values[ DraftTransfer::LINE_META ] ?? null;
		$active = is_string( $id ) ? self::session_context( $id ) : null;
		if ( null !== $active ) {
			$item->add_meta_data( DraftTransfer::LINE_META, $id, true );
		}
	}

	/**
	 * Persist original planning quantities alongside the inquiry's actual quantities.
	 *
	 * @param WC_Order $order Native inquiry, before assessment/mail preparation.
	 * @throws \RuntimeException Frozen native context cannot be encoded.
	 */
	public function capture( WC_Order $order ): void {
		$active = array();
		foreach ( $order->get_items() as $item ) {
			if ( ! $item instanceof WC_Order_Item_Product ) {
				continue;
			}
			$id = $item->get_meta( DraftTransfer::LINE_META );
			if ( '' === $id ) {
				continue;
			}
			$handoff = is_string( $id ) ? self::session_context( $id ) : null;
			if ( null === $handoff ) {
				throw new \RuntimeException( 'planning_inquiry_context_unavailable' );
			}
			$active[ $id ] = $handoff;
		}
		$contexts = array();
		foreach ( $active as $id => $handoff ) {
			$actual = array();
			foreach ( $order->get_items() as $item ) {
				if ( $item instanceof WC_Order_Item_Product && $item->get_meta( DraftTransfer::LINE_META ) === $id ) {
					$product            = Publication::canonical_id( $item->get_product_id() );
					$actual[ $product ] = ( $actual[ $product ] ?? 0 ) + $item->get_quantity();
				}
			}
			if ( array() === $actual ) {
				continue;
			}
			$planned = array();
			foreach ( $handoff['snapshot']['items'] as $item ) {
				$planned[ $item['product_id'] ] = ( $planned[ $item['product_id'] ] ?? 0 ) + $item['quantity'];
			}
			$contexts[ $id ] = array(
				'reference'          => self::reference( $handoff ),
				'included_items'     => $actual,
				'quantities_changed' => Publication::revision( $planned ) !== Publication::revision( $actual ),
			);
		}
		if ( array() !== $contexts ) {
			// A compact reference fits HPOS TEXT. The full report/proof remains
			// in its immutable planner record; strings also avoid CPT array slashing.
			$encoded = wp_json_encode( $contexts, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE );
			if ( ! is_string( $encoded ) || strlen( $encoded ) > self::MAX_META_BYTES ) {
				throw new \RuntimeException( 'planning_inquiry_context_unavailable' );
			}
			$order->update_meta_data( self::META, $encoded );
		}
	}

	/**
	 * Native orders retain an immutable pointer and commercial quantities, not
	 * another report/product registry. Private reads resolve and match it again.
	 *
	 * @param array<string,mixed> $handoff Verified full planner handoff.
	 * @return array<string,mixed>
	 */
	public static function reference( array $handoff ): array {
		$snapshot  = $handoff['snapshot'];
		$reference = array(
			'schema_version'  => 1,
			'kind'            => 'planning_inquiry_reference_v1',
			'handoff_id'      => $handoff['id'],
			'snapshot_sha256' => $handoff['snapshot_sha256'],
		);
		foreach ( array( 'project_id', 'title', 'revision', 'input_sha256', 'report_run_id', 'report_source_sha256', 'report_sha256', 'pdf', 'items' ) as $field ) {
			$reference[ $field ] = $snapshot[ $field ];
		}
		$reference['reference_sha256'] = Publication::revision( $reference );
		return $reference;
	}

	/**
	 * Historical inquiry context is independent of subsequent publication changes.
	 *
	 * @param WC_Order $order Authorised native inquiry.
	 * @return array<string,array<string,mixed>>
	 */
	public static function stored( WC_Order $order ): array {
		$raw    = $order->get_meta( self::META );
		$raw    = is_string( $raw ) ? json_decode( $raw, true ) : $raw;
		$result = array();
		if ( is_array( $raw ) ) {
			foreach ( $raw as $id => $entry ) {
				if ( is_string( $id ) && is_array( $entry ) && self::valid_reference( $entry['reference'] ?? null, $id ) ) {
					$result[ $id ] = $entry;
				}
			}
		}
		return $result;
	}

	/**
	 * Show the reference in the existing native draft item-data surface.
	 *
	 * @param array<array<string,mixed>> $data Native item descriptions.
	 * @param array<string,mixed>        $line Native cart line.
	 * @return array<array<string,mixed>>
	 */
	public function item_data( array $data, array $line ): array {
		$id     = $line[ DraftTransfer::LINE_META ] ?? null;
		$active = is_string( $id ) ? self::session_context( $id ) : null;
		if ( null !== $active ) {
			$snapshot = $active['snapshot'];
			$data[]   = array(
				'key'   => __( 'Planning project', 'linker-commerce' ),
				'value' => self::label( $snapshot ),
			);
		}
		return $data;
	}

	/**
	 * Semantic data fragments inherit the native Woo/LC surface and tokens.
	 *
	 * @param WC_Order $order Authorised native inquiry.
	 */
	public function render( WC_Order $order ): void {
		$this->output( $order, false );
	}

	/**
	 * Keep HTML and plain inquiry emails faithful to the same frozen context.
	 *
	 * @param WC_Order $order Native inquiry.
	 * @param bool     $admin Team copy.
	 * @param bool     $plain Plain-text template.
	 */
	public function email( WC_Order $order, bool $admin, bool $plain ): void {
		unset( $admin );
		$this->output( $order, $plain );
	}

	/** Retain receipts for uncertain retries; release full contexts when Woo empties. */
	public function emptied(): void {
		WC()->session->set( DraftTransfer::CONTEXTS, array() );
	}

	/**
	 * Private download follows the native inquiry's own access checks.
	 *
	 * @param WC_Order $order Native inquiry.
	 * @param string   $id Frozen handoff identity.
	 */
	public static function report_url( WC_Order $order, string $id ): string {
		return add_query_arg( 'key', $order->get_order_key(), rest_url( 'linker/v1/inquiries/' . $order->get_id() . '/planning-report/' . $id ) );
	}

	/**
	 * Format the saved project reference through the native locale.
	 *
	 * @param array<string,mixed> $snapshot Frozen report context.
	 */
	private static function label( array $snapshot ): string {
		/* translators: 1: project title, 2: saved input revision. */
		return sprintf( __( '%1$s · input revision %2$d', 'linker-commerce' ), $snapshot['title'], $snapshot['revision'] );
	}

	/**
	 * Render only the native data attached to this authorised inquiry.
	 *
	 * @param WC_Order $order Native inquiry.
	 * @param bool     $plain Plain output.
	 */
	private function output( WC_Order $order, bool $plain ): void {
		foreach ( self::stored( $order ) as $id => $entry ) {
			$label   = self::label( $entry['reference'] );
			$url     = self::report_url( $order, $id );
			$changed = ! empty( $entry['quantities_changed'] ) ? __( 'Quantities differ from the planning report.', 'linker-commerce' ) : '';
			if ( $plain ) {
				echo esc_html( __( 'Planning project', 'linker-commerce' ) . ': ' . $label . "\n" . $changed . "\n" . __( 'Planning report', 'linker-commerce' ) . ': ' . $url . "\n" );
			} else {
				echo '<dl><dt>' . esc_html__( 'Planning project', 'linker-commerce' ) . '</dt><dd>' . esc_html( $label ) . '</dd>';
				if ( '' !== $changed ) {
					echo '<dd>' . esc_html( $changed ) . '</dd>';
				}
				echo '<dt>' . esc_html__( 'Planning report', 'linker-commerce' ) . '</dt><dd><a href="' . esc_url( $url ) . '">' . esc_html__( 'Download PDF', 'linker-commerce' ) . '</a></dd></dl>';
			}
		}
	}

	/**
	 * Resolve one line without re-scanning every native cart line.
	 *
	 * @param string $id Native handoff reference.
	 * @return array<string,mixed>|null
	 */
	private static function session_context( string $id ): ?array {
		$stored = (array) WC()->session->get( DraftTransfer::CONTEXTS, array() );
		return isset( $stored[ $id ] ) && self::valid( $stored[ $id ], $id ) ? $stored[ $id ] : null;
	}

	/**
	 * Only the immutable server-created envelope can be copied into native records.
	 *
	 * @param mixed  $value Stored context.
	 * @param string $id Native line reference.
	 */
	private static function valid( mixed $value, string $id ): bool {
		return DraftTransfer::native_context_valid( $value, $id );
	}

	/**
	 * Check the compact native reference before displaying or resolving it.
	 *
	 * @param mixed  $value Native order metadata.
	 * @param string $id Referenced handoff identity.
	 */
	private static function valid_reference( mixed $value, string $id ): bool {
		if ( ! is_array( $value ) || 1 !== ( $value['schema_version'] ?? null ) || 'planning_inquiry_reference_v1' !== ( $value['kind'] ?? null ) || ( $value['handoff_id'] ?? null ) !== $id || ! is_string( $value['title'] ?? null ) || ! is_int( $value['revision'] ?? null ) || $value['revision'] < 1 || ! is_array( $value['items'] ?? null ) || ! is_array( $value['pdf'] ?? null ) ) {
			return false;
		}
		foreach ( array( 'handoff_id', 'project_id', 'report_run_id' ) as $field ) {
			if ( ! is_string( $value[ $field ] ?? null ) || 1 !== preg_match( '/\A[a-f0-9]{32}\z/', $value[ $field ] ) ) {
				return false;
			}
		}
		foreach ( array( 'snapshot_sha256', 'input_sha256', 'report_source_sha256', 'report_sha256', 'reference_sha256' ) as $field ) {
			if ( ! is_string( $value[ $field ] ?? null ) || 1 !== preg_match( '/\A[a-f0-9]{64}\z/', $value[ $field ] ) ) {
				return false;
			}
		}
		$pdf = $value['pdf'];
		if ( ! is_string( $pdf['asset_id'] ?? null ) || 1 !== preg_match( '/\A[a-f0-9]{32}\z/', $pdf['asset_id'] ) || ! is_string( $pdf['sha256'] ?? null ) || 1 !== preg_match( '/\A[a-f0-9]{64}\z/', $pdf['sha256'] ) || 'application/pdf' !== ( $pdf['media_type'] ?? null ) || ! array_is_list( $value['items'] ) || array() === $value['items'] ) {
			return false;
		}
		foreach ( $value['items'] as $item ) {
			if ( ! is_array( $item ) || ! is_int( $item['product_id'] ?? null ) || $item['product_id'] < 1 || ! is_int( $item['quantity'] ?? null ) || $item['quantity'] < 1 || ! is_string( $item['label'] ?? null ) || '' === $item['label'] ) {
				return false;
			}
		}
		$sha = $value['reference_sha256'];
		unset( $value['reference_sha256'] );
		return hash_equals( $sha, Publication::revision( $value ) );
	}
}
