<?php
/**
 * Transfer intent for an inquiry that includes a frozen project report.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Planning;

use WC_Order;
use WP_Error;

/** The native form nonce covers the exact intent shown at review. */
final class InquiryTransfer {
	public const FIELD = 'linker_report_transfer';

	/** Identifiers and fingerprint from the owned handoff and native draft preview.
	 *
	 * @param string $report Exact report run.
	 * @param string $handoff Immutable owned handoff.
	 * @param string $key Native transfer idempotence key.
	 * @param string $draft Reviewed cart fingerprint.
	 */
	public function __construct(
		public readonly string $report,
		public readonly string $handoff,
		public readonly string $key,
		public readonly string $draft
	) {}

	/** Parse the bounded scalar before using it in any native request.
	 *
	 * @param mixed $value Potential submitted transfer.
	 */
	public static function read( mixed $value ): ?self {
		if ( ! is_string( $value ) || ! preg_match( '/\A([a-f0-9]{32}):([a-f0-9]{32}):([a-f0-9-]{36}):([a-f0-9]{64})\z/', $value, $parts ) || ! wp_is_uuid( $parts[3], 4 ) ) {
			return null;
		}
		return new self( $parts[1], $parts[2], $parts[3], $parts[4] );
	}

	/** Form field and semantic replay fingerprint. */
	public function value(): string {
		return implode( ':', array( $this->report, $this->handoff, $this->key, $this->draft ) );
	}

	/** Reject changes before the business journal claims a new submission. */
	public function current(): bool {
		return hash_equals( $this->draft, DraftPreview::fingerprint() );
	}

	/**
	 * Resolve the authenticated, immutable handoff before consuming admission.
	 *
	 * @param string $project Nonce-bound project identity.
	 * @param int    $revision Nonce-bound revision.
	 * @return array<string,mixed>|WP_Error
	 */
	public function owned( string $project, int $revision ): array|WP_Error {
		/**
		 * Read this handoff using the current native submitter's identity.
		 *
		 * @since 0.3.0
		 * @param array|WP_Error $handoff Source response.
		 * @param string         $id      Exact handoff the customer reviewed.
		 */
		$handoff = apply_filters( 'linker_tools_planning_inquiry_handoff', Context::admission_unavailable(), $this->handoff ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- Existing Tools owns the planning identity.
		if ( $handoff instanceof WP_Error ) {
			return $handoff;
		}
		if ( ! DraftTransfer::envelope_valid( $handoff, $project, $this->report, $revision ) || ( $handoff['id'] ?? null ) !== $this->handoff ) {
			return Context::admission_unavailable();
		}
		return DraftTransfer::publication_error( $handoff['snapshot'] ) ?? $handoff;
	}

	/**
	 * Send the order inside the exact reviewed native draft write.
	 *
	 * @param array<string,mixed>            $handoff Already owned and bound to the request.
	 * @param callable():(WC_Order|WP_Error) $send Native order writer.
	 */
	public function send( array $handoff, callable $send ): WC_Order|WP_Error {
		$command = array(
			'schema_version'        => 1,
			'project_id'            => $handoff['snapshot']['project_id'],
			'report_run_id'         => $this->report,
			'expected_revision'     => $handoff['snapshot']['revision'],
			'key'                   => $this->key,
			'expected_draft_sha256' => $this->draft,
		);
		return ( new DraftTransfer() )->submit( $command, $handoff, $send );
	}
}
