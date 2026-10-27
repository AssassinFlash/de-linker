<?php
/**
 * One owned planner intent, one native Woo write and durable session receipt.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Planning;

use Linker\Commerce\Account\AtomicSolutionDraft;
use Linker\Commerce\Inquiry\Assessment\Lock;
use Linker\Commerce\Mail\NativeTransaction;
use Linker\Commerce\Products\Publication;
use WP_Error;

/** Browser product arrays and copied cart metadata never authorise a transfer. */
final class DraftTransfer {
	public const LINE_META = '_linker_planning_handoff';
	public const CONTEXTS  = '_linker_planning_contexts';
	public const RECEIPTS  = '_linker_planning_receipts';

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
		$snapshot = $handoff['snapshot'] ?? null;
		if ( ! is_array( $snapshot ) || 1 !== ( $handoff['schema_version'] ?? null ) || 1 !== ( $snapshot['schema_version'] ?? null ) || 'planning_products_v1' !== ( $snapshot['kind'] ?? null ) || ( $snapshot['project_id'] ?? null ) !== $command['project_id'] || ( $snapshot['revision'] ?? null ) !== $command['expected_revision'] || ( $snapshot['report_run_id'] ?? null ) !== $command['report_run_id'] || ! is_string( $handoff['id'] ?? null ) || 1 !== preg_match( '/\A[a-f0-9]{32}\z/', $handoff['id'] ) || ! is_string( $handoff['snapshot_sha256'] ?? null ) || ! hash_equals( Publication::revision( $snapshot ), $handoff['snapshot_sha256'] ) ) {
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
				'planning-draft:' . $session->get_customer_id(),
				function () use ( $command, $handoff, &$result ): void {
					$result = $this->write( $command, $handoff );
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
	 * Native session state and acknowledgement commit in the same transaction.
	 *
	 * @param array<string,mixed> $command Original intent.
	 * @param array<string,mixed> $handoff Owned receipt.
	 * @return array<string,mixed>|WP_Error
	 */
	private function write( array $command, array $handoff ): array|WP_Error {
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
			return is_array( $known ) && ( $known['intent_sha256'] ?? null ) === $intent && ( $known['handoff_id'] ?? null ) === $handoff['id'] ? array_replace( $known, array( 'draft_urls' => self::urls() ) ) : self::failure( 'planning_transfer_changed', 409 );
		}
		// Woo may have loaded this request before another transfer finished. Do
		// not overwrite that newer native draft or import arbitrary session fields.
		if ( Publication::revision( maybe_unserialize( $fresh['cart'] ?? array() ) ) !== Publication::revision( $session->get( 'cart', array() ) ) || Publication::revision( $receipts ) !== Publication::revision( $session->get( self::RECEIPTS, array() ) ) ) {
			$this->stop_autosave();
			return self::failure( 'planning_draft_changed', 409 );
		}
		if ( ! hash_equals( $command['expected_draft_sha256'], DraftPreview::fingerprint() ) ) {
			$this->stop_autosave();
			return self::failure( 'planning_draft_changed', 409 );
		}
		$snapshot = $handoff['snapshot'];
		$lines    = array_map(
			static fn ( array $item ): array => array(
				'product'  => array( 'id' => $item['product_id'] ),
				'quantity' => $item['quantity'],
			),
			$snapshot['items']
		);
		$design   = array(
			'kind'        => 'planning_products_v1',
			'publication' => $snapshot['publication'],
			'selected'    => array( 'lines' => $lines ),
		);
		$scope    = null;
		try {
			$scope = new NativeTransaction();
			$items = ( new AtomicSolutionDraft() )->add( $design, array( self::LINE_META => $handoff['id'] ), DraftPreview::replacement_keys( $snapshot['project_id'], $handoff['id'] ) );
			if ( is_wp_error( $items ) ) {
				$scope->rollback();
				$this->stop_autosave();
				return $items;
			}
			$contexts = (array) $session->get( self::CONTEXTS, array() );
			foreach ( $contexts as $old_id => $context ) {
				if ( ( $context['snapshot']['project_id'] ?? null ) === $snapshot['project_id'] ) {
					unset( $contexts[ $old_id ] );
				}
			}
			$contexts[ $handoff['id'] ] = $handoff;
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
				'draft_urls'      => self::urls(),
			);
			$receipts[ $key ]           = $result;
			$session->set( self::CONTEXTS, $contexts );
			$session->set( self::RECEIPTS, $receipts );
			$session->save_data();
			$saved  = $this->fresh();
			$stored = maybe_unserialize( $saved[ self::RECEIPTS ] ?? array() );
			if ( ! is_array( $stored ) || ( $stored[ $key ] ?? null ) !== $result ) {
				$scope->rollback();
				$this->stop_autosave();
				return self::failure( 'planning_transfer_unconfirmed', 503 );
			}
			$scope->commit();
			return $result;
		} catch ( \Throwable $error ) {
			if ( $scope instanceof NativeTransaction ) {
				try {
					$scope->rollback();
				} catch ( \Throwable $rollback_error ) { // phpcs:ignore Generic.CodeAnalysis.EmptyStatement.DetectedCatch -- The original commit can be unknown; do not compensate on another connection.
				}
			}
			$this->stop_autosave();
			return self::failure( 'planning_transfer_unconfirmed', 503 );
		}
	}

	/** Both destinations come from the native translated Woo page pairing.
	 *
	 * @return array<string,string>
	 * @throws \RuntimeException A translated native page is missing.
	 */
	public static function urls(): array {
		$page   = (int) get_option( 'woocommerce_cart_page_id' );
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
		$known['draft_urls'] = self::urls();
		return array(
			'schema_version' => 1,
			'state'          => 'applied',
			'receipt'        => $known,
		);
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
