<?php
/**
 * An in-flight service job links one owned conversation and its existing retry receipt.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Genie;

use Linker\Commerce\Inquiry\Assessment\Lock;
use Linker\Tools\Protection\Replies;

/** Keep only the question, its publication basis and the service job until finalization. */
final class PendingTurns {
	public const PENDING = '_linker_genie_pending';
	public const STAGE   = '_linker_genie_stage';
	private const PREFIX = '_linker_genie_job_';

	/** Store the operation's checked input without copying attachment bytes or service credentials.
	 *
	 * @param array<string,mixed> $turn Native operation context.
	 */
	public static function save( array $turn ): bool {
		$id      = $turn['conversation_id'];
		$receipt = $turn['receipt'];
		$key     = self::PREFIX . $turn['job_id'];
		if ( ( $turn['partner'] && ! add_post_meta( $receipt, '_linker_genie_priced', 1, true ) ) || ! add_post_meta( $receipt, $key, $id, true ) ) {
			return false;
		}
		if ( ! add_post_meta( $id, self::PENDING, wp_slash( $turn ), true ) ) {
			delete_post_meta( $receipt, $key );
			return false;
		}
		wp_schedule_single_event( (int) ceil( $turn['started_at'] + Proxy::TURN_BUDGET ), 'linker_tools_expire_genie_turn', array( $id, $turn['job_id'] ) );
		return true;
	}

	/** Indexed unique meta key on the operation receipt survives finalization for idempotent reads.
	 *
	 * @param string $job Service-issued job ID.
	 */
	public static function receipt( string $job ): int {
		$ids = get_posts(
			array(
				'post_type'      => Replies::TYPE,
				'post_status'    => 'private',
				'meta_key'       => self::PREFIX . $job, // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_key -- Each job has its own indexed meta key.
				'fields'         => 'ids',
				'posts_per_page' => 1,
				'no_found_rows'  => true,
			)
		);
		return (int) ( $ids[0] ?? 0 );
	}

	/** Read the immutable conversation binding for this job.
	 *
	 * @param int    $receipt Receipt.
	 * @param string $job Job.
	 */
	public static function conversation( int $receipt, string $job ): int {
		return (int) get_post_meta( $receipt, self::PREFIX . $job, true );
	}

	/** Current pending context or an empty array.
	 *
	 * @param int $conversation Conversation.
	 * @return array<string,mixed>
	 */
	public static function current( int $conversation ): array {
		$value = $conversation > 0 ? get_post_meta( $conversation, self::PENDING, true ) : null;
		return is_array( $value ) ? $value : array();
	}

	/** Public progress only.
	 *
	 * @param array<string,mixed> $turn Pending context.
	 * @return array<string,mixed>
	 */
	public static function progress( array $turn ): array {
		$stage = get_post_meta( $turn['receipt'], self::STAGE, true );
		return array(
			'job_id'          => $turn['job_id'],
			'conversation_id' => $turn['conversation_id'],
			'status'          => 'running',
			'stage'           => '' !== $stage ? $stage : $turn['stage'],
			'started_at'      => $turn['started_at'],
		);
	}

	/** Forget the heavy staging data while keeping the terminal operation receipt.
	 *
	 * @param array<string,mixed> $turn Pending context held under its operation lock.
	 */
	public static function clear( array $turn ): void {
		delete_post_meta( $turn['conversation_id'], self::PENDING, wp_slash( $turn ) );
		delete_post_meta( $turn['receipt'], self::STAGE );
		wp_clear_scheduled_hook( 'linker_tools_expire_genie_turn', array( $turn['conversation_id'], $turn['job_id'] ) );
	}

	/** An abandoned browser does not leave its provisional guest post or an unusable operation.
	 *
	 * @param int    $conversation Pending conversation ID.
	 * @param string $job Original job.
	 */
	public static function expire( int $conversation, string $job ): void {
		$turn = self::current( $conversation );
		if ( ( $turn['job_id'] ?? null ) !== $job || microtime( true ) - $turn['started_at'] < Proxy::TURN_BUDGET ) {
			return;
		}
		Lock::run(
			'genie-operation-' . $turn['operation_id'],
			static function () use ( $conversation, $job ): void {
				wp_cache_delete( $conversation, 'post_meta' );
				$current = self::current( $conversation );
				if ( ( $current['job_id'] ?? null ) === $job ) {
					self::fail( $current );
				}
			}
		);
	}

	/** Called with the operation lock held for a known unrecorded outcome.
	 *
	 * @param array<string,mixed> $turn Pending context.
	 */
	public static function fail( array $turn ): void {
		self::clear( $turn );
		if ( 'auto-draft' === get_post_status( $turn['conversation_id'] ) ) {
			wp_delete_post( $turn['conversation_id'], true );
		}
		wp_delete_post( $turn['receipt'], true );
	}
}
