<?php
/**
 * One owned planner intent, one native Woo write and durable session receipt.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Planning;

use Linker\Commerce\Account\AtomicSolutionDraft;
use Linker\Commerce\Account\DesignProof;
use Linker\Commerce\Inquiry\Assessment\Lock;
use Linker\Commerce\Mail\NativeTransaction;
use Linker\Commerce\Products\Publication;
use WC_Order;
use WP_Error;

/** Browser product arrays and copied cart metadata never authorise a transfer. */
final class DraftTransfer {
	public const LINE_META = '_linker_planning_handoff';
	public const CONTEXTS  = '_linker_planning_contexts';
	public const RECEIPTS  = '_linker_planning_receipts';

	/**
	 * Serialize writes against the same native Woo draft.
	 *
	 * @param string $customer Native Woo session identity.
	 */
	public static function session_lock( string $customer ): string {
		return 'planning-draft:' . $customer;
	}

	/**
	 * Engine ownership is already confirmed by the trusted Tools adapter.
	 *
	 * @param mixed               $previous Earlier server integration.
	 * @param array<string,mixed> $command Bounded browser intent, no lines.
	 * @param array<string,mixed> $handoff Owned immutable engine receipt.
	 * @return array<string,mixed>|WP_Error
	 */
	public function apply( mixed $previous, array $command, array $handoff ): array|WP_Error {
		unset( $previous );
		return $this->run( $command, $handoff, null );
	}

	/**
	 * Apply and send the reviewed draft in one native transaction.
	 *
	 * @param array<string,mixed>            $command Original intent.
	 * @param array<string,mixed>            $handoff Owned receipt.
	 * @param callable():(WC_Order|WP_Error) $send Admitted native order writer.
	 */
	public function submit( array $command, array $handoff, callable $send ): WC_Order|WP_Error {
		return $this->run( $command, $handoff, $send );
	}

	/**
	 * Fence the native draft across its original writer and an optional order write.
	 *
	 * @param array<string,mixed>                   $command Original intent.
	 * @param array<string,mixed>                   $handoff Owned receipt.
	 * @param (callable():(WC_Order|WP_Error))|null $send Admitted native order writer.
	 * @return ($send is null ? array<string,mixed>|WP_Error : WC_Order|WP_Error)
	 */
	private function run( array $command, array $handoff, ?callable $send ): array|WC_Order|WP_Error {
		if ( ! self::envelope_valid( $handoff, $command['project_id'], $command['report_run_id'], $command['expected_revision'] ) ) {
			return self::failure( 'planning_transfer_invalid', 502 );
		}
		wc_load_cart();
		$session = WC()->session;
		if ( ! $session instanceof \WC_Session_Handler ) {
			return self::failure( 'planning_transfer_unavailable', 503 );
		}
		$result = self::failure( 'planning_transfer_busy', 409 );
		try {
			$taken = Lock::run(
				self::session_lock( $session->get_customer_id() ),
				function () use ( $command, $handoff, $send, &$result ): void {
					$result = $this->write( $command, $handoff, $send );
				},
				guard_connection: true
			);
			return $taken ? $result : self::failure( 'planning_transfer_busy', 409 );
		} catch ( \Throwable $error ) {
			$this->stop_autosave();
			return self::failure( 'planning_transfer_unconfirmed', 503 );
		}
	}

	/**
	 * Validate the engine-owned handoff envelope and its requested binding.
	 *
	 * The engine computes snapshot_sha256 with its Python canonical encoder.
	 * Recomputing it with wp_json_encode would treat a different serialization
	 * as altered content. The authenticated transport is the ownership proof;
	 * these checks bind that trusted reply to this project and report.
	 * Schema 1 and the 32/64-character identifier/SHA-256 forms come from
	 * `services/engine/src/linker_engine/planning/handoffs.py`; the positive
	 * revision floor mirrors the workspace project schema.
	 *
	 * @param mixed       $handoff Engine handoff.
	 * @param string|null $project_id Expected project.
	 * @param string|null $report_run_id Expected report run.
	 * @param int|null    $revision Expected project revision.
	 */
	public static function envelope_valid( mixed $handoff, ?string $project_id = null, ?string $report_run_id = null, ?int $revision = null ): bool {
		if ( ! is_array( $handoff ) ) {
			return false;
		}
		$snapshot = $handoff['snapshot'] ?? null;
		if ( ! is_array( $snapshot ) ) {
			return false;
		}
		if ( 1 !== ( $handoff['schema_version'] ?? null ) || 1 !== ( $snapshot['schema_version'] ?? null ) || ! in_array( $snapshot['kind'] ?? null, array( 'planning_products_v1', 'planning_report_only_v1' ), true ) ) {
			return false;
		}
		if ( ! is_string( $handoff['id'] ?? null ) || 1 !== preg_match( '/\A[a-f0-9]{32}\z/', $handoff['id'] ) ) {
			return false;
		}
		if ( ! is_string( $handoff['snapshot_sha256'] ?? null ) || 1 !== preg_match( '/\A[a-f0-9]{64}\z/', $handoff['snapshot_sha256'] ) ) {
			return false;
		}
		foreach ( array( 'project_id', 'report_run_id' ) as $field ) {
			if ( ! is_string( $snapshot[ $field ] ?? null ) || 1 !== preg_match( '/\A[a-f0-9]{32}\z/', $snapshot[ $field ] ) ) {
				return false;
			}
		}
		if ( ! is_int( $snapshot['revision'] ?? null ) || $snapshot['revision'] < 1 ) {
			return false;
		}
		if ( self::report_only( $snapshot ) && array() !== ( $snapshot['items'] ?? null ) ) {
			return false;
		}
		return ( null === $project_id || $snapshot['project_id'] === $project_id )
			&& ( null === $report_run_id || $snapshot['report_run_id'] === $report_run_id )
			&& ( null === $revision || $snapshot['revision'] === $revision );
	}

	/**
	 * Whether the frozen report contains no procurement lines.
	 *
	 * @param array<string,mixed> $snapshot Frozen report snapshot.
	 */
	public static function report_only( array $snapshot ): bool {
		return 'planning_report_only_v1' === ( $snapshot['kind'] ?? null );
	}

	/**
	 * Revalidate any actual publication dependencies retained by the report.
	 *
	 * @param array<string,mixed> $snapshot Frozen report snapshot.
	 * @phpstan-impure Reads current publication on each invocation.
	 */
	public static function publication_error( array $snapshot ): ?WP_Error {
		if ( self::report_only( $snapshot ) && array_key_exists( 'publication', $snapshot ) && null === $snapshot['publication'] ) {
			return null;
		}
		return ( new DesignProof() )->current_error( $snapshot );
	}

	/**
	 * Add a PHP-owned fingerprint before retaining the trusted engine envelope.
	 *
	 * @param array<string,mixed> $handoff Engine handoff.
	 * @return array<string,mixed>
	 */
	public static function native_context( array $handoff ): array {
		$handoff['native_sha256'] = Publication::revision( $handoff );
		return $handoff;
	}

	/**
	 * Validate a retained native context without reimplementing the engine hash.
	 *
	 * Contexts written before native_sha256 existed can only be accepted when
	 * the engine hash is the exact value PHP's historical encoder produced.
	 *
	 * @param mixed  $value Retained context.
	 * @param string $id Native line reference.
	 */
	public static function native_context_valid( mixed $value, string $id ): bool {
		if ( ! self::envelope_valid( $value ) || ( $value['id'] ?? null ) !== $id ) {
			return false;
		}
		$native = $value['native_sha256'] ?? null;
		if ( null === $native ) {
			return hash_equals( $value['snapshot_sha256'], Publication::revision( $value['snapshot'] ) );
		}
		if ( ! is_string( $native ) || 1 !== preg_match( '/\A[a-f0-9]{64}\z/', $native ) ) {
			return false;
		}
		$content = $value;
		unset( $content['native_sha256'] );
		return hash_equals( $native, Publication::revision( $content ) );
	}

	/**
	 * Native session state and acknowledgement commit in the same transaction.
	 *
	 * @param array<string,mixed>                   $command Original intent.
	 * @param array<string,mixed>                   $handoff Owned receipt.
	 * @param (callable():(WC_Order|WP_Error))|null $send Admitted native order writer.
	 * @return array<string,mixed>|WC_Order|WP_Error
	 * @throws \RuntimeException If the reviewed cart cannot be updated.
	 */
	private function write( array $command, array $handoff, ?callable $send ): array|WC_Order|WP_Error {
		$session  = $this->native_session();
		$fresh    = $this->fresh();
		$receipts = maybe_unserialize( $fresh[ self::RECEIPTS ] ?? array() );
		if ( ! is_array( $receipts ) ) {
			return self::failure( 'planning_transfer_invalid', 503 );
		}
		$intent = Publication::revision( $command );
		$key    = $command['key'];
		if ( isset( $receipts[ $key ] ) ) {
			$known = $receipts[ $key ];
			$this->stop_autosave();
			if ( ! is_array( $known ) || ( $known['intent_sha256'] ?? null ) !== $intent || ( $known['handoff_id'] ?? null ) !== $handoff['id'] ) {
				return self::failure( 'planning_transfer_changed', 409 );
			}
			if ( null !== $send ) {
				return self::failure( 'planning_draft_changed', 409 );
			}
			return array_replace( $known, self::destinations( self::report_only( $handoff['snapshot'] ) ), array( 'active' => self::has_active_handoff( $fresh, $handoff ) ) );
		}
		// Woo may have loaded this request before another transfer finished. Do
		// not overwrite that newer native draft or import arbitrary session fields.
		if ( Publication::revision( maybe_unserialize( $fresh['cart'] ?? array() ) ) !== Publication::revision( $session->get( 'cart', array() ) ) || Publication::revision( $receipts ) !== Publication::revision( $session->get( self::RECEIPTS, array() ) ) || Publication::revision( maybe_unserialize( $fresh[ self::CONTEXTS ] ?? array() ) ) !== Publication::revision( $session->get( self::CONTEXTS, array() ) ) ) {
			$this->stop_autosave();
			return self::failure( 'planning_draft_changed', 409 );
		}
		if ( ! hash_equals( $command['expected_draft_sha256'], DraftPreview::fingerprint() ) ) {
			return self::failure( 'planning_draft_changed', 409 );
		}
		$snapshot    = $handoff['snapshot'];
		$report_only = self::report_only( $snapshot );
		$lines       = array_map(
			static fn ( array $item ): array => array(
				'product'  => array( 'id' => $item['product_id'] ),
				'quantity' => $item['quantity'],
			),
			$snapshot['items']
		);
		$design      = array(
			'kind'        => 'planning_products_v1',
			'publication' => $snapshot['publication'],
			'selected'    => array( 'lines' => $lines ),
		);
		$scope       = null;
		$restore     = $this->restore_cart_state( $session );
		try {
			$scope   = new NativeTransaction();
			$replace = DraftPreview::replacement_keys( $snapshot['project_id'], $handoff['id'] );
			if ( $report_only ) {
				$items = self::publication_error( $snapshot ) ?? array();
				if ( is_array( $items ) && array() !== $replace ) {
					foreach ( $replace as $cart_key ) {
						if ( ! WC()->cart->remove_cart_item( $cart_key ) ) {
							throw new \RuntimeException( 'planning_draft_changed' );
						}
					}
					WC()->cart->calculate_totals();
					$items = self::publication_error( $snapshot ) ?? array();
				}
			} else {
				$items = ( new AtomicSolutionDraft() )->add( $design, array( self::LINE_META => $handoff['id'] ), $replace );
			}
			if ( is_wp_error( $items ) ) {
				$scope->rollback();
				$restore();
				$this->evict_cart_cache();
				return $items;
			}
			$contexts = (array) $session->get( self::CONTEXTS, array() );
			foreach ( $contexts as $old_id => $context ) {
				if ( ( $context['snapshot']['project_id'] ?? null ) === $snapshot['project_id'] ) {
					unset( $contexts[ $old_id ] );
				}
			}
			$contexts[ $handoff['id'] ] = self::native_context( $handoff );
			$result                     = array(
				'schema_version'  => 1,
				'handoff_id'      => $handoff['id'],
				'snapshot_sha256' => $handoff['snapshot_sha256'],
				'intent_sha256'   => $intent,
				'project_id'      => $snapshot['project_id'],
				'report_run_id'   => $snapshot['report_run_id'],
				'revision'        => $snapshot['revision'],
				'items'           => $items,
				'command'         => $command,
				...self::destinations( $report_only ),
			);
			if ( $report_only ) {
				$result['report_only'] = true;
			}
			$receipts[ $key ] = $result;
			$session->set( self::CONTEXTS, $contexts );
			$session->set( self::RECEIPTS, $receipts );
			$order = null;
			if ( null !== $send ) {
				$order = $send();
				if ( $order instanceof WP_Error ) {
					$scope->rollback();
					$restore();
					$this->evict_cart_cache();
					if ( 'checkout-error' === $order->get_error_code() ) {
						return new WP_Error( 'linker_guided_checkout_refused', __( 'Please try sending your inquiry again.', 'linker-commerce' ) );
					}
					return $order;
				}
				Context::consume_captured_notes( $order );
				WC()->cart->empty_cart();
			}
			if ( $report_only ) {
				$session->set_customer_session_cookie( true );
			}
			$session->save_data();
			$saved  = $this->fresh();
			$stored = maybe_unserialize( $saved[ self::RECEIPTS ] ?? array() );
			if ( ! is_array( $stored ) || ( $stored[ $key ] ?? null ) !== $result ) {
				$scope->rollback();
				$restore();
				$this->stop_autosave();
				return self::failure( 'planning_transfer_unconfirmed', 503 );
			}
			$scope->commit();
			return $order ?? $result;
		} catch ( \Throwable $error ) {
			if ( $scope instanceof NativeTransaction ) {
				try {
					$scope->rollback();
					$restore();
				} catch ( \Throwable $rollback_error ) { // phpcs:ignore Generic.CodeAnalysis.EmptyStatement.DetectedCatch -- The original commit can be unknown; do not compensate on another connection.
				}
			}
			$this->stop_autosave();
			return self::failure( 'planning_transfer_unconfirmed', 503 );
		}
	}

	/**
	 * Keep Woo's request state consistent with its rolled-back native draft.
	 *
	 * @param \WC_Session_Handler $session Native session.
	 * @return callable():void
	 */
	private function restore_cart_state( \WC_Session_Handler $session ): callable {
		$cart           = WC()->cart;
		$lines          = $cart->get_cart();
		$removed        = $cart->get_removed_cart_contents();
		$totals         = $cart->get_totals();
		$coupons        = $cart->get_applied_coupons();
		$discounts      = $cart->get_coupon_discount_totals();
		$discount_taxes = $cart->get_coupon_discount_tax_totals();
		$fields         = array();
		foreach ( array( 'cart', 'removed_cart_contents', 'cart_totals', 'applied_coupons', 'coupon_discount_totals', 'coupon_discount_tax_totals', 'shipping_method_counts', 'previous_shipping_methods', 'chosen_shipping_methods', 'store_api_draft_order', 'order_awaiting_payment', 'wc_notices', self::CONTEXTS, self::RECEIPTS ) as $key ) {
			$fields[ $key ] = $session->get( $key );
		}
		return static function () use ( $cart, $lines, $removed, $totals, $coupons, $discounts, $discount_taxes, $session, $fields ): void {
			$cart->set_cart_contents( $lines );
			$cart->set_removed_cart_contents( $removed );
			$cart->set_totals( $totals );
			$cart->set_applied_coupons( $coupons );
			$cart->set_coupon_discount_totals( $discounts );
			$cart->set_coupon_discount_tax_totals( $discount_taxes );
			foreach ( $fields as $key => $value ) {
				$session->set( $key, $value );
			}
		};
	}

	/**
	 * Links returned to the planner for this native Woo transfer.
	 *
	 * @param bool $report_only Whether the report adds no products.
	 * @return array{draft_urls: array<string,string>, inquiry_urls: array<string,string>}
	 */
	public static function destinations( bool $report_only ): array {
		$inquiry = self::urls( true );
		return array(
			'draft_urls'   => $report_only ? $inquiry : self::urls(),
			'inquiry_urls' => $inquiry,
		);
	}

	/** Both destinations come from the native translated Woo page pairing.
	 *
	 * @param bool $report_only Whether the destination is the inquiry form.
	 * @return array<string,string>
	 * @throws \RuntimeException A translated native page is missing.
	 */
	public static function urls( bool $report_only = false ): array {
		$page   = (int) get_option( $report_only ? 'woocommerce_checkout_page_id' : 'woocommerce_cart_page_id' );
		$result = array();
		foreach ( array( 'en', 'de' ) as $language ) {
			$twin = \Linker\Commerce\Presentation\PageUrls::twin( $page, $language );
			if ( $twin < 1 ) {
				throw new \RuntimeException( 'planning_translated_draft_page_missing' );
			}
			$result[ $language ] = (string) get_permalink( $twin );
		}
		return $result;
	}

	/** Read a receipt without adding any product or reissuing an intent.
	 *
	 * @param mixed               $previous Earlier native integration.
	 * @param array<string,mixed> $command Original intent.
	 * @param array<string,mixed> $handoff Currently owned engine receipt.
	 * @return array<string,mixed>|WP_Error
	 */
	public function receipt( mixed $previous, array $command, array $handoff ): array|WP_Error {
		unset( $previous );
		WC()->initialize_session();
		if ( ! WC()->session instanceof \WC_Session_Handler ) {
			return self::failure( 'planning_transfer_unavailable', 503 );
		}
		$fresh    = $this->fresh();
		$receipts = maybe_unserialize( $fresh[ self::RECEIPTS ] ?? array() );
		$known    = is_array( $receipts ) ? ( $receipts[ $command['key'] ] ?? null ) : null;
		if ( null === $known ) {
			return array(
				'schema_version' => 1,
				'state'          => 'not_applied',
			);
		}
		if ( ! is_array( $known ) || ( $known['intent_sha256'] ?? null ) !== Publication::revision( $command ) || ( $known['handoff_id'] ?? null ) !== ( $handoff['id'] ?? null ) ) {
			return self::failure( 'planning_transfer_changed', 409 );
		}
		$known = array_replace( $known, self::destinations( self::report_only( $handoff['snapshot'] ) ) );
		return array(
			'schema_version' => 1,
			'state'          => 'applied',
			'receipt'        => $known,
			'active'         => self::has_active_handoff( $fresh, $handoff ),
		);
	}

	/**
	 * A committed handoff remains available only while the native draft refers to it.
	 *
	 * @param array<string,mixed> $fresh Persisted Woo session data.
	 * @param array<string,mixed> $handoff Owned immutable engine receipt.
	 */
	private static function has_active_handoff( array $fresh, array $handoff ): bool {
		$id       = $handoff['id'];
		$contexts = maybe_unserialize( $fresh[ self::CONTEXTS ] ?? array() );
		$context  = is_array( $contexts ) ? ( $contexts[ $id ] ?? null ) : null;
		if ( ! self::native_context_valid( $context, $id ) || $context['snapshot_sha256'] !== $handoff['snapshot_sha256'] ) {
			return false;
		}
		if ( self::report_only( $handoff['snapshot'] ) ) {
			return true;
		}
		foreach ( (array) maybe_unserialize( $fresh['cart'] ?? array() ) as $line ) {
			if ( ( $line[ self::LINE_META ] ?? null ) === $id ) {
				return true;
			}
		}
		return false;
	}

	/** Fresh native storage read, not a cached copy of an uncommitted receipt.
	 *
	 * @return array<string,mixed>
	 * @throws \RuntimeException Native session metadata is unavailable.
	 */
	private function fresh(): array {
		$session = $this->native_session();
		$group   = constant( 'WC_SESSION_CACHE_GROUP' );
		if ( ! is_string( $group ) ) {
			throw new \RuntimeException( 'planning_native_session_group_unavailable' );
		}
		wp_cache_delete( \WC_Cache_Helper::get_cache_prefix( $group ) . $session->get_customer_id(), $group );
		return (array) $session->get_session_data();
	}

	/**
	 * Select the actual native persistence API, rather than assuming an abstract session.
	 *
	 * @return \WC_Session_Handler Native session persistence.
	 * @throws \RuntimeException Unsupported native persistence adapter.
	 */
	private function native_session(): \WC_Session_Handler {
		$session = WC()->session;
		if ( ! $session instanceof \WC_Session_Handler ) {
			throw new \RuntimeException( 'planning_native_session_unavailable' );
		}
		return $session;
	}

	/** An uncertain write must be resolved by readback, never shutdown compensation. */
	private function stop_autosave(): void {
		remove_action( 'shutdown', array( WC()->session, 'save_data' ), 20 );
		$this->evict_cart_cache();
	}

	/** A reverted native cart must not survive in Woo's object caches. */
	private function evict_cart_cache(): void {
		$this->fresh();
		if ( get_current_user_id() > 0 ) {
			clean_user_cache( get_current_user_id() );
		}
	}

	/** Shared opaque protocol failure; the tool provides reviewed localised copy.
	 *
	 * @param string $code Stable error code.
	 * @param int    $status HTTP status.
	 */
	private static function failure( string $code, int $status ): WP_Error {
		return new WP_Error( $code, '', array( 'status' => $status ) );
	}
}
