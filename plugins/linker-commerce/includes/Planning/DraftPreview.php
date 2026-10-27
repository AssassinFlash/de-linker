<?php
/**
 * Native cart change preview for one frozen planning project.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Planning;

use Linker\Commerce\Account\DesignProof;
use Linker\Commerce\Products\Publication;
use WP_Error;

/** A draft fingerprint is a concurrency condition, never product authority. */
final class DraftPreview {
	/**
	 * Show exactly the project group to be replaced, before any Woo product write.
	 *
	 * @param mixed               $previous Earlier integration.
	 * @param array<string,mixed> $command Owned intent.
	 * @param array<string,mixed> $handoff Server-frozen report.
	 * @return array<string,mixed>|WP_Error
	 */
	public function read( mixed $previous, array $command, array $handoff ): array|WP_Error {
		unset( $previous, $command );
		wc_load_cart();
		$snapshot = $handoff['snapshot'];
		$error    = ( new DesignProof() )->current_error(
			array(
				'kind'        => 'planning_products_v1',
				'publication' => $snapshot['publication'],
			)
		);
		if ( $error instanceof WP_Error ) {
			return $error;
		}
		$before  = array();
		$labels  = array();
		$replace = self::replacement_keys( $snapshot['project_id'], $handoff['id'] );
		foreach ( WC()->cart->get_cart() as $key => $line ) {
			if ( in_array( $key, $replace, true ) ) {
				$id            = (int) $line['product_id'];
				$before[ $id ] = ( $before[ $id ] ?? 0 ) + $line['quantity'];
				$context_id    = $line[ DraftTransfer::LINE_META ];
				$contexts      = Context::active();
				$labels[ $id ] = $line['data']->get_sku();
				foreach ( ( $contexts[ $context_id ]['snapshot']['items'] ?? $handoff['snapshot']['items'] ) as $planned ) {
					if ( $planned['product_id'] === $id ) {
						$labels[ $id ] = $planned['label'];
					}
				}
			}
		}
		$after = array();
		foreach ( $snapshot['items'] as $item ) {
			$id           = $item['product_id'];
			$after[ $id ] = ( $after[ $id ] ?? 0 ) + $item['quantity'];
			$product      = wc_get_product( $id );
			if ( ! $product instanceof \WC_Product || ! Publication::is_published( $id ) ) {
				return DesignProof::unavailable();
			}
			$labels[ $id ] = $item['label'];
		}
		$rows = array();
		$ids  = array_unique( array_merge( array_keys( $after ), array_keys( $before ) ) );
		foreach ( $ids as $id ) {
			$rows[] = array(
				'product_id' => $id,
				'label'      => $labels[ $id ],
				'before'     => $before[ $id ] ?? 0,
				'after'      => $after[ $id ] ?? 0,
			);
		}
		$active = Context::active();
		$same   = count( $active ) > 0;
		foreach ( $replace as $key ) {
			$line = WC()->cart->get_cart()[ $key ];
			$id   = $line[ DraftTransfer::LINE_META ];
			if ( ( $active[ $id ]['snapshot_sha256'] ?? null ) !== $handoff['snapshot_sha256'] ) {
				$same = false;
			}
		}
		$present = array() !== $replace && $same && Publication::revision( $before ) === Publication::revision( $after );
		return array(
			'schema_version'  => 1,
			'project_id'      => $snapshot['project_id'],
			'report_run_id'   => $snapshot['report_run_id'],
			'revision'        => $snapshot['revision'],
			'handoff_id'      => $handoff['id'],
			'snapshot_sha256' => $handoff['snapshot_sha256'],
			'draft_sha256'    => self::fingerprint(),
			'changes'         => $rows,
			'already_present' => $present,
			'draft_urls'      => DraftTransfer::urls(),
		);
	}

	/**
	 * Unrelated/manual lines remain in the draft.
	 *
	 * @param string      $project_id Frozen project identity.
	 * @param string|null $handoff_id Currently owned handoff, which can restore a lost native context.
	 * @return string[]
	 */
	public static function replacement_keys( string $project_id, ?string $handoff_id = null ): array {
		$contexts = Context::active();
		$keys     = array();
		foreach ( WC()->cart->get_cart() as $key => $line ) {
			$id = $line[ DraftTransfer::LINE_META ] ?? null;
			if ( is_string( $id ) && ( $id === $handoff_id || ( $contexts[ $id ]['snapshot']['project_id'] ?? null ) === $project_id ) ) {
				$keys[] = $key;
			}
		}
		return $keys;
	}

	/** Native serialisable cart lines already exclude PHP product objects. */
	public static function fingerprint(): string {
		$native   = new \WC_Cart_Session( WC()->cart );
		$contexts = array();
		foreach ( Context::active() as $id => $context ) {
			$contexts[ $id ] = $context['snapshot_sha256'];
		}
		return Publication::revision(
			array(
				'cart'     => $native->get_cart_for_session(),
				'contexts' => $contexts,
			)
		);
	}
}
