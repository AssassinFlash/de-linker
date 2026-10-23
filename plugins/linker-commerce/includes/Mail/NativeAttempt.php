<?php
/** Durable exclusion of an unresolved original delivery attempt.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
namespace Linker\Commerce\Mail;

/** Fixed operational state, not another message, permission or capacity reservation. */
final class NativeAttempt {
	public const META = '_linker_mail_native_attempt';

	/**
	 * Enter before any quota reservation; retain an open witness after unknown IO.
	 *
	 * @param int     $job Original native job.
	 * @param Message $message Exact authorized immutable message.
	 * @return string Original owner token, empty when another outcome is unresolved.
	 */
	public static function begin( int $job, Message $message ): string {
		return NativeTransaction::run(
			static function () use ( $job, $message ): string {
				self::lock( $job );
				clean_post_cache( $job );
				$stored = ( new JobStore() )->load( $job );
				if ( 'private' !== get_post_status( $job ) || null === $stored || $stored['message']->to_array() !== $message->to_array() || self::unresolved( $job ) ) {
					return '';
				}
				$state = array(
					'token'   => wp_generate_uuid4(),
					'message' => hash( 'sha256', (string) wp_json_encode( $message->to_array() ) ),
					'state'   => 'open',
				);
				self::save( $job, $state );
				return $state['token'];
			}
		);
	}

	/**
	 * Only a definite no-IO/false outcome resolves this invocation's witness.
	 * Success deletes the original job; exceptions deliberately do not call this.
	 *
	 * @param int    $job Original job.
	 * @param string $token Exact server-owned attempt.
	 */
	public static function resolved( int $job, string $token ): void {
		NativeTransaction::run(
			static function () use ( $job, $token ): void {
				self::lock( $job );
				wp_cache_delete( $job, 'post_meta' );
				$state = get_post_meta( $job, self::META, true );
				if ( ! self::valid( $state ) || $state['token'] !== $token || 'open' !== $state['state'] ) {
					throw new \RuntimeException( 'mail_attempt_resolution_unconfirmed' );
				}
				$state['state'] = 'ready';
				self::save( $job, $state );
			}
		);
	}

	/**
	 * Read only under the original native job's authoritative row scope.
	 * Absence is a never-started legacy job; malformed state is unresolved.
	 *
	 * @param int $job Original job.
	 */
	public static function unresolved( int $job ): bool {
		$state = get_post_meta( $job, self::META, true );
		return '' !== $state && ( ! self::valid( $state ) || 'ready' !== $state['state'] );
	}

	/**
	 * Validate the entire constant-size native witness, never arbitrary post data.
	 *
	 * @param mixed $state Raw native metadata.
	 * @phpstan-assert-if-true array{token:string,message:string,state:'open'|'ready'} $state
	 */
	private static function valid( mixed $state ): bool {
		return is_array( $state ) && array_keys( $state ) === array( 'token', 'message', 'state' ) && is_string( $state['token'] ) && wp_is_uuid( $state['token'], 4 ) && is_string( $state['message'] ) && 1 === preg_match( '/^[0-9a-f]{64}$/', $state['message'] ) && in_array( $state['state'], array( 'open', 'ready' ), true );
	}

	/**
	 * First SQL is inside NativeTransaction's existing ConnectionFence.
	 *
	 * @param int $job Original job.
	 * @throws \RuntimeException Missing/locked native source cannot authorize IO.
	 */
	private static function lock( int $job ): void {
		global $wpdb;
		// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- Exact existing original queue row, bounded by NOWAIT.
		$row = $wpdb->get_var( $wpdb->prepare( 'SELECT ID FROM %i WHERE ID=%d FOR UPDATE NOWAIT', $wpdb->posts, $job ) );
		if ( (int) $row !== $job ) {
			throw new \RuntimeException( 'mail_attempt_original_missing' );
		}
	}

	/**
	 * The UUID, digest and fixed state are a constant-size operational witness.
	 * Existing capacity accounts complete Message bytes, not physical SQL metadata.
	 *
	 * @param int                  $job Original job.
	 * @param array<string,string> $state Fixed operational witness.
	 * @throws \RuntimeException A failed readback never permits transport.
	 */
	private static function save( int $job, array $state ): void {
		update_post_meta( $job, self::META, $state );
		wp_cache_delete( $job, 'post_meta' );
		if ( get_post_meta( $job, self::META, true ) !== $state ) {
			throw new \RuntimeException( 'mail_attempt_witness_unconfirmed' );
		}
	}
}
