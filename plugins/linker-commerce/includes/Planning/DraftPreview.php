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
		if ( ! DraftTransfer::envelope_valid( $handoff ) ) {
			return DesignProof::unavailable();
		}
		$snapshot    = $handoff['snapshot'];
		$error       = DraftTransfer::publication_error( $snapshot );
		$report_only = DraftTransfer::report_only( $snapshot );
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
		if ( $report_only && array() === $replace ) {
			$present = isset( Context::report_only_contexts()[ $handoff['id'] ] );
		}
		$phase_conflicts = Context::phase_conflicts( $snapshot );
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
			'draft_urls'      => DraftTransfer::urls( $report_only ),
			...( $report_only ? array( 'report_only' => true ) : array() ),
			...( array() !== $phase_conflicts ? array( 'phase_conflicts' => $phase_conflicts ) : array() ),
		);
	}

	/**
	 * Preview the complete inquiry, keeping manual and other project lines distinct.
	 *
	 * @param mixed               $previous Earlier integration.
	 * @param array<string,mixed> $command Owned preview with a validated language.
	 * @param array<string,mixed> $handoff Server-frozen report.
	 * @return array<string,mixed>|WP_Error
	 */
	public function inquiry( mixed $previous, array $command, array $handoff ): array|WP_Error {
		$preview = $this->read( $previous, $command, $handoff );
		if ( is_wp_error( $preview ) ) {
			return $preview;
		}
		$lines = self::cart_lines( self::replacement_keys( $preview['project_id'], $handoff['id'] ) );
		foreach ( $preview['changes'] as $row ) {
			if ( $row['after'] > 0 ) {
				$lines[] = array(
					'product_id'    => $row['product_id'],
					'label'         => $row['label'],
					'quantity'      => $row['after'],
					'project_id'    => $preview['project_id'],
					'project_title' => $handoff['snapshot']['title'],
				);
			}
		}
		$preview['inquiry_lines']     = $lines;
		$preview['inquiry_form_html'] = ( new \Linker\Commerce\Inquiry\Form() )->planning( $handoff, $command['lang'] );
		return $preview;
	}

	/**
	 * Native lines included in the inquiry, preserving each project's quantities.
	 *
	 * @param string[] $exclude Cart keys replaced by a proposed handoff.
	 * @return list<array<string,mixed>>
	 */
	public static function cart_lines( array $exclude = array() ): array {
		$active = Context::active();
		$lines  = array();
		foreach ( WC()->cart->get_cart() as $key => $line ) {
			if ( in_array( $key, $exclude, true ) ) {
				continue;
			}
			$source  = $line[ DraftTransfer::LINE_META ] ?? '';
			$lines[] = array(
				'product_id'    => (int) $line['product_id'],
				'label'         => $line['data']->get_name(),
				'quantity'      => $line['quantity'],
				'project_id'    => $active[ $source ]['snapshot']['project_id'] ?? null,
				'project_title' => $active[ $source ]['snapshot']['title'] ?? null,
			);
		}
		return $lines;
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
		foreach ( Context::active() + Context::report_only_contexts() as $id => $context ) {
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
