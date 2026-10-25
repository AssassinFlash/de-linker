<?php
/**
 * Service-side file reader for a Commerce-authorised frozen inquiry report.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Planner;

use WP_Error;

/** Browser identity headers and arbitrary asset IDs never reach this reader. */
final class ReportAccess {
	/**
	 * Use the existing bounded service transport.
	 *
	 * @param Transport $transport Bounded private service transport.
	 */
	public function __construct( private readonly Transport $transport = new Transport() ) {}

	/** Register the server-only Commerce seam. */
	public function register(): void {
		add_filter( 'linker_tools_planning_report_content', array( $this, 'read' ), 10, 3 );
	}

	/**
	 * Only a context already attached to an authorised inquiry can use team read.
	 *
	 * @param mixed               $previous Earlier service adapter.
	 * @param array<string,mixed> $reference Server-stored compact context.
	 * @param int                 $order_id Authorised inquiry.
	 */
	public function read( mixed $previous, array $reference, int $order_id ): string|WP_Error {
		unset( $previous );
		$order = wc_get_order( $order_id );
		if ( ! $order instanceof \WC_Order || ! class_exists( \Linker\Commerce\Planning\Context::class ) ) {
			return Failure::make( 'unavailable', 503 );
		}
		$stored = \Linker\Commerce\Planning\Context::stored( $order );
		$id     = $reference['handoff_id'] ?? null;
		if ( ! is_string( $id ) || ( $stored[ $id ]['reference'] ?? null ) !== $reference ) {
			return Failure::make( 'identity', 403 );
		}
		$principal = new Principal( 'team', 'wp:' . get_current_blog_id() . ':inquiry:' . $order_id );
		$handoff   = $this->transport->object(
			$principal,
			'handoffs/read',
			array(
				'schema_version' => 1,
				'handoff_id'     => $id,
			)
		);
		if ( is_wp_error( $handoff ) ) {
			return $handoff;
		}
		if ( ! is_array( $handoff['snapshot'] ?? null ) || ! is_string( $handoff['snapshot_sha256'] ?? null ) || \Linker\Commerce\Planning\Context::reference( $handoff ) !== $reference ) {
			return Failure::make( 'invalid_reply', 502 );
		}
		$snapshot = $handoff['snapshot'];
		$body     = wp_json_encode(
			array(
				'schema_version' => 1,
				'project_id'     => $snapshot['project_id'],
				'asset_id'       => $snapshot['pdf']['asset_id'],
			)
		);
		if ( ! is_string( $body ) ) {
			return Failure::make( 'input', 422 );
		}
		$reply = $this->transport->call( $principal, 'assets/content', $body );
		if ( is_wp_error( $reply ) ) {
			return $reply;
		}
		if ( 200 !== $reply['status'] || ! str_starts_with( $reply['type'], 'application/octet-stream' ) || ! str_starts_with( $reply['body'], '%PDF-' ) || ! hash_equals( $snapshot['pdf']['sha256'], hash( 'sha256', $reply['body'] ) ) ) {
			return Failure::make( 'unavailable', 503 );
		}
		return $reply['body'];
	}
}
