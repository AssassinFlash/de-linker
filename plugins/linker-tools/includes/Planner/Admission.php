<?php
/**
 * Dispatch owned Planner commands, coordinating project deletion with Woo.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Planner;

use WP_Error;

/** The Planner stores each command receipt with the project mutation. */
final class Admission {
	/**
	 * Forward the command with its original owner and idempotency key.
	 *
	 * @param Principal           $principal Verified project owner.
	 * @param string              $path Allowlisted private operation.
	 * @param array<string,mixed> $command Parsed browser command.
	 * @param string              $body Original bounded JSON bytes.
	 * @param Transport           $transport Private transport.
	 * @return array{status:int,type:string,body:string}|WP_Error
	 */
	public function send( Principal $principal, string $path, array $command, string $body, Transport $transport ): array|WP_Error {
		if ( 'projects/delete' === $path ) {
			if ( array_diff( array_keys( $command ), array( 'schema_version', 'key', 'project_id', 'expected_revision' ) ) ) {
				return Failure::make( 'input', 422 );
			}
			return ProjectDelete::checked( $principal, $command, $transport );
		}
		return $transport->call( $principal, $path, $body );
	}
}
