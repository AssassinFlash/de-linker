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
use WP_Error;
use WP_REST_Response;

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
		wp_schedule_single_event( (int) ceil( self::deadline( $turn ) ), 'linker_tools_expire_genie_turn', array( $id, $turn['job_id'] ) );
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

	/**
	 * Only the live service subject and progress fields are needed on a running poll.
	 * A cache miss reads the pending operation, including jobs accepted by an older shell.
	 *
	 * @param int    $id Owned conversation.
	 * @param string $job Service job ID.
	 * @return array<string,mixed>
	 */
	public static function polling( int $id, string $job ): array {
		$header = wp_cache_get( $job, 'linker_genie_poll' );
		if ( is_array( $header ) && $header['conversation_id'] === $id ) {
			return $header;
		}
		$turn = self::current( $id );
		if ( ( $turn['job_id'] ?? null ) !== $job ) {
			return array();
		}
		$header = array_intersect_key( $turn, array_flip( array( 'job_id', 'conversation_id', 'receipt', 'started_at', 'stage', 'subject_hash', 'operation_id' ) ) );
		wp_cache_set( $job, $header, 'linker_genie_poll', Proxy::TURN_BUDGET );
		return $header;
	}

	/** Public progress only.
	 *
	 * @param array<string,mixed> $turn Pending context.
	 * @param array<string,mixed> $service Latest service state when available.
	 * @return array<string,mixed>
	 */
	public static function progress( array $turn, array $service = array() ): array {
		$stage = wp_cache_get( $turn['job_id'], 'linker_genie_stage' );
		if ( false === $stage ) {
			$stage = get_post_meta( $turn['receipt'], self::STAGE, true );
		}
		if ( isset( $service['stage'] ) && $stage !== $service['stage'] ) {
			$stage = $service['stage'];
			wp_cache_set( $turn['job_id'], $stage, 'linker_genie_stage', Proxy::TURN_BUDGET );
		}
		$progress = array(
			'job_id'          => $turn['job_id'],
			'conversation_id' => $turn['conversation_id'],
			'status'          => 'running',
			'stage'           => '' !== $stage ? $stage : $turn['stage'],
			'started_at'      => $turn['started_at'],
		);
		if ( 'waiting' === $turn['stage'] ) {
			$cached = wp_cache_get( $turn['job_id'], 'linker_genie_queue_seconds' );
			$wait   = $service['queued_seconds'] ?? ( false === $cached ? 0 : $cached );
			if ( isset( $service['queued_seconds'] ) && $wait !== $cached ) {
				wp_cache_set( $turn['job_id'], $wait, 'linker_genie_queue_seconds', Proxy::TURN_BUDGET );
			}
			$progress['queued_seconds'] = $wait;
		}
		return $progress;
	}

	/** Forget the heavy staging data while keeping the terminal operation receipt.
	 *
	 * @param array<string,mixed> $turn Pending context held under its operation lock.
	 */
	public static function clear( array $turn ): void {
		wp_cache_delete( $turn['job_id'], 'linker_genie_poll' );
		wp_cache_delete( $turn['job_id'], 'linker_genie_stage' );
		wp_cache_delete( $turn['job_id'], 'linker_genie_queue_seconds' );
		delete_post_meta( $turn['conversation_id'], self::PENDING, wp_slash( $turn ) );
		delete_post_meta( $turn['receipt'], self::STAGE );
		wp_clear_scheduled_hook( 'linker_tools_expire_genie_turn', array( $turn['conversation_id'], $turn['job_id'] ) );
	}

	/** The original execution budget starts after the service's measured queue wait.
	 *
	 * @param array<string,mixed> $turn Native operation context.
	 * @param array<string,mixed> $state Service progress or final result.
	 */
	public static function deadline( array $turn, array $state = array() ): float {
		return $turn['started_at'] + ( $state['queued_seconds'] ?? 0 ) + Proxy::TURN_BUDGET;
	}

	/** Recover a committed answer or release the expired operation under its lock.
	 *
	 * @param array<string,mixed> $turn Expired pending context.
	 */
	public static function abandon( array $turn ): void {
		$conversation = $turn['conversation_id'];
		$job          = $turn['job_id'];
		Lock::run(
			'genie-operation-' . $turn['operation_id'],
			static function () use ( $conversation, $job ): void {
				wp_cache_delete( $conversation, 'post_meta' );
				$current = self::current( $conversation );
				if ( ( $current['job_id'] ?? null ) === $job && null === self::recover( $current ) ) {
					self::fail( $current );
				}
			}
		);
	}

	/** Recover an interrupted receipt write from the checked, already committed conversation.
	 * Cron keeps an unsigned receipt. Only its authenticated reader may release actions.
	 *
	 * @param array<string,mixed> $turn Pending context under the native operation lock.
	 * @return true|WP_Error|null Null when the turn has not committed.
	 */
	public static function recover( array $turn ): true|WP_Error|null {
		$id     = $turn['conversation_id'];
		$marker = get_post_meta( $id, Thread::COMPLETION, true );
		if ( ( $marker['operation_id'] ?? null ) !== $turn['operation_id'] ) {
			return null;
		}
		$saved = ( new Thread() )->read( $id );
		if ( ( $saved['operation_id'] ?? null ) !== $turn['operation_id'] || ( $saved['operation_fingerprint'] ?? null ) !== $turn['fingerprint'] ) {
			return new WP_Error( 'linker_resource_result', 'The saved turn could not be confirmed.', array( 'status' => 503 ) );
		}
		$reply = new WP_REST_Response(
			array(
				'job_id'          => $turn['job_id'],
				'conversation_id' => $id,
				'status'          => 'completed',
				'stream'          => $saved['stream'],
			)
		);
		( new PublicationGuard() )->remember( $reply, $turn['publication'] );
		$conversations = new Conversations();
		$conversations->resume_pending_guest( $id );
		if ( ! $conversations->publish_answer( $id ) || ( new Replies() )->finish( $turn['receipt'], $reply, $turn['locale'] ) !== $turn['receipt'] ) {
			return new WP_Error( 'linker_resource_result', 'The saved turn could not be confirmed.', array( 'status' => 503 ) );
		}
		self::clear( $turn );
		return true;
	}

	/** Called with the operation lock held for a known unrecorded outcome.
	 *
	 * @param array<string,mixed> $turn Pending context.
	 */
	public static function fail( array $turn ): void {
		if ( 'auto-draft' === get_post_status( $turn['conversation_id'] ) ) {
			wp_delete_post( $turn['conversation_id'], true );
		}
		self::clear( $turn );
		wp_delete_post( $turn['receipt'], true );
	}
}
