<?php
/**
 * Coordinate project deletion with native inquiry submission.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Planner;

use Linker\Commerce\Planning\ProjectReferences;
use WP_Error;

/** Coordinate every admitted delete, including projects without a report. */
final class ProjectDelete {
	/**
	 * Pin the generation before reading Woo. Inquiry submission advances it under
	 * the same native lock, fencing delayed HTTP commands after a lost reply.
	 *
	 * @param Principal           $principal Verified owner from the original command.
	 * @param array<string,mixed> $command Original validated delete intent.
	 * @param Transport           $transport Private planner RPC.
	 * @return array{status:int,type:string,body:string}|WP_Error
	 */
	public static function checked( Principal $principal, array $command, Transport $transport ): array|WP_Error {
		$project = $command['project_id'] ?? null;
		if ( ! is_string( $project ) || ! class_exists( ProjectReferences::class ) ) {
			return Failure::make( 'inquiry_unavailable', 503 );
		}
		$reply = null;
		try {
			$taken = ProjectReferences::with_lock(
				$project,
				static function () use ( $project, $command, $principal, $transport, &$reply ): void {
					$state = $transport->object(
						$principal,
						'projects/prepared-handoffs',
						array(
							'schema_version' => 1,
							'project_id'     => $project,
						)
					);
					if ( is_wp_error( $state ) ) {
						// A concurrent identical delete may have already committed. The original
						// owner/key can recover its receipt even after the project disappeared.
						$reply = $state;
						if ( 404 === ( $state->get_error_data()['status'] ?? null ) ) {
							$receipt = $transport->object( $principal, 'operations/replay/projects/delete', $command );
							if ( is_wp_error( $receipt ) ) {
								$reply = $receipt;
							} elseif ( 'replayed' === ( $receipt['status'] ?? null ) ) {
								$reply = array(
									'status' => 200,
									'type'   => 'application/json',
									'body'   => (string) wp_json_encode( $receipt['result'] ?? null ),
								);
							}
						}
						return;
					}
					if ( ! is_int( $state['inquiry_generation'] ?? null ) || $state['inquiry_generation'] < 0 ) {
						$reply = Failure::make( 'invalid_reply', 502 );
						return;
					}
					if ( ProjectReferences::contains( $project ) ) {
						$reply = array(
							'status' => 409,
							'type'   => 'application/json',
							'body'   => '{"error":{"code":"inquiry_linked"}}',
						);
						return;
					}
					$command['inquiry_generation'] = $state['inquiry_generation'];
					$reply                         = $transport->call( $principal, 'projects/delete-after-inquiry-check', (string) wp_json_encode( $command ) );
				}
			);
		} catch ( \Throwable ) {
			return Failure::make( 'inquiry_unavailable', 503 );
		}
		if ( ! $taken || null === $reply ) {
			return Failure::make( 'inquiry_unavailable', 503 );
		}
		if ( is_wp_error( $reply ) || 400 <= $reply['status'] ) {
			return $reply;
		}
		$result = json_decode( $reply['body'], true );
		if ( 200 !== $reply['status'] || ! str_starts_with( $reply['type'], 'application/json' ) || true !== ( $result['deleted'] ?? null ) || ( $result['project_id'] ?? null ) !== $command['project_id'] || ( $result['revision'] ?? null ) !== $command['expected_revision'] ) {
			return Failure::make( 'invalid_reply', 502 );
		}
		return $reply;
	}
}
