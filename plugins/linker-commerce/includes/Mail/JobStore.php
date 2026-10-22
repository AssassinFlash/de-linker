<?php
/**
 * Messages waiting for another attempt.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Mail;

/**
 * Keeps each message that could not be sent at once as a private post, so the
 * message survives until a later attempt (Action Scheduler passes only the
 * post id: its arguments are limited to 8000 characters, too short for an HTML
 * email, mail-root-cause.md §5 M2). A message that was sent is deleted; one
 * that failed every attempt stays, marked as failed.
 */
final class JobStore {
	/**
	 * The default is always the shared production envelope, including cron calls.
	 *
	 * @param JobCapacity $capacity Native queue admission and transaction boundary.
	 */
	public function __construct( private readonly JobCapacity $capacity = new NativeJobCapacity() ) {}

	/** An outer native writer has not committed its own job/source yet. */
	public function transaction_active(): bool {
		return $this->capacity->transaction_active();
	}


	/**
	 * Native retries retain the same durable job; the memory port only drives units.
	 *
	 * @param int $id Original job.
	 * @param int $time Next attempt.
	 */
	public function reschedule( int $id, int $time ): void {
		$this->capacity->reschedule( $id, $time );
	}

	/**
	 * Post type of the queued messages.
	 */
	public const POST_TYPE = 'linker_mail_job';

	/**
	 * Post meta: the message, its attempts so far, the last error.
	 */
	public const INQUIRY_META = '_linker_mail_inquiry';

	private const MESSAGE_META  = '_linker_mail_message';
	private const ATTEMPTS_META = '_linker_mail_attempts';
	private const ERROR_META    = '_linker_mail_error';

	/**
	 * Post status of a message that failed every attempt.
	 */
	public const FAILED_STATUS = 'draft';

	/**
	 * Private priority, written only by an authenticated staff release.
	 */
	public const PRIORITY_META = '_linker_mail_critical_release';

	/**
	 * Promote an original job explicitly restored by staff.
	 *
	 * @param int $id Original job explicitly restored by staff.
	 * @throws \RuntimeException When the priority cannot be persisted.
	 */
	public function promote( int $id ): void {
		$this->capacity->promote(
			$id,
			function () use ( $id ): void {
				update_post_meta( $id, self::PRIORITY_META, 'yes' );
				if ( ! $this->critical( $id ) ) {
					throw new \RuntimeException( esc_html( 'notification_priority_write_failed' ) );
				}
			}
		);
	}

	/**
	 * Read a private staff-release priority.
	 *
	 * @param int $id Original job.
	 */
	public function critical( int $id ): bool {
		wp_cache_delete( $id, 'post_meta' );
		return 'yes' === get_post_meta( $id, self::PRIORITY_META, true );
	}

	/**
	 * Registers the post type; runs on init.
	 */
	public function register_post_type(): void {
		register_post_type(
			self::POST_TYPE,
			array(
				'label'           => __( 'Queued emails', 'linker-commerce' ),
				'public'          => false,
				'show_ui'         => false,
				'rewrite'         => false,
				'query_var'       => false,
				'supports'        => array( 'title' ),
				'capability_type' => 'post',
			)
		);
	}

	/**
	 * Stores a message.
	 *
	 * @param  Message       $message Message.
	 * @param  int           $inquiry Native inquiry owning this original notification.
	 * @param callable|null $accepted Durable native-source acknowledgement in this transaction.
	 * @return int Job id, 0 when the post could not be written.
	 */
	public function create( Message $message, int $inquiry = 0, ?callable $accepted = null ): int {
		return $this->capacity->create( $message, fn (): int => $this->write( $message, $inquiry, $accepted ) );
	}

	/**
	 * Write and read back the complete native job inside the capacity transaction.
	 *
	 * @param Message       $message Frozen native notification.
	 * @param int           $inquiry Owning native inquiry.
	 * @param callable|null $accepted Durable native-source acknowledgement.
	 * @throws \RuntimeException The full job cannot be read back.
	 */
	private function write( Message $message, int $inquiry, ?callable $accepted ): int {
		$id = wp_insert_post(
			array(
				'post_type'   => self::POST_TYPE,
				'post_status' => 'private',
				'post_title'  => wp_strip_all_tags( $message->subject ),
			),
			true
		);
		if ( is_wp_error( $id ) ) {
			return 0;
		}
		// The body lives in meta, which no content filter rewrites.
		update_post_meta( $id, self::MESSAGE_META, wp_slash( (string) wp_json_encode( $message->to_array() ) ) );
		update_post_meta( $id, self::ATTEMPTS_META, 0 );
		if ( $inquiry > 0 ) {
			update_post_meta( $id, self::INQUIRY_META, $inquiry );
		}
		clean_post_cache( $id );
		$read = $this->load( $id );
		if ( 'private' !== get_post_status( $id ) || null === $read || $message->to_array() !== $read['message']->to_array() || ( $inquiry > 0 && (int) get_post_meta( $id, self::INQUIRY_META, true ) !== $inquiry ) ) {
			throw new \RuntimeException( 'notification_job_readback_failed' );
		}
		if ( null !== $accepted ) {
			$accepted( $id );
		}
		return $id;
	}

	/**
	 * A stored message and its attempts so far.
	 *
	 * @param  int $id Job id.
	 * @return array{message: Message, attempts: int}|null Null when there is no such job.
	 */
	public function load( int $id ): ?array {
		if ( self::POST_TYPE !== get_post_type( $id ) ) {
			return null;
		}
		$data = json_decode( (string) get_post_meta( $id, self::MESSAGE_META, true ), true );
		if ( ! is_array( $data ) ) {
			return null;
		}
		return array(
			'message'  => Message::from_array( $data ),
			'attempts' => (int) get_post_meta( $id, self::ATTEMPTS_META, true ),
		);
	}

	/**
	 * Records a failed attempt.
	 *
	 * @param int    $id       Job id.
	 * @param int    $attempts Attempts so far.
	 * @param string $error    Error of the last attempt.
	 */
	public function record_failure( int $id, int $attempts, string $error ): void {
		update_post_meta( $id, self::ATTEMPTS_META, $attempts );
		update_post_meta( $id, self::ERROR_META, $error );
	}

	/**
	 * Marks a message that failed its last attempt.
	 *
	 * @param int    $id       Job id.
	 * @param int    $attempts Attempts made.
	 * @param string $error    Error of the last attempt.
	 */
	public function fail( int $id, int $attempts, string $error ): void {
		$this->record_failure( $id, $attempts, $error );
		wp_update_post(
			array(
				'ID'          => $id,
				'post_status' => self::FAILED_STATUS,
			)
		);
	}

	/**
	 * The messages whose last retry failed: the staff's "not delivered" number
	 * (mail-root-cause.md §9, the administrator's visibility).
	 */
	public function failed_count(): int {
		$counts = wp_count_posts( self::POST_TYPE );
		return (int) ( $counts->{ self::FAILED_STATUS } ?? 0 );
	}

	/**
	 * The failed messages themselves, for the daily digest's fourth block
	 * (docs/specs/74-daily-digest.md): recipient, subject and last error of
	 * each message whose retries ran out, oldest first. One whose stored
	 * message is unreadable stays out of the list; it still counts in
	 * failed_count().
	 *
	 * @return list<array{id: int, to: list<string>, subject: string, error: string}>
	 */
	public function failed(): array {
		$posts  = get_posts(
			array(
				'post_type'   => self::POST_TYPE,
				'post_status' => self::FAILED_STATUS,
				'numberposts' => -1,
				'orderby'     => 'date',
				'order'       => 'ASC',
			)
		);
		$failed = array();
		foreach ( $posts as $post ) {
			$data = json_decode( (string) get_post_meta( (int) $post->ID, self::MESSAGE_META, true ), true );
			if ( ! is_array( $data ) ) {
				continue;
			}
			$message  = Message::from_array( $data );
			$failed[] = array(
				'id'      => (int) $post->ID,
				'to'      => array_values( $message->to ),
				'subject' => $message->subject,
				'error'   => (string) get_post_meta( (int) $post->ID, self::ERROR_META, true ),
			);
		}
		return $failed;
	}

	/**
	 * Deletes a message that was sent.
	 *
	 * @param int $id Job id.
	 */
	public function delete( int $id ): void {
		wp_delete_post( $id, true );
		$this->capacity->deleted( $id );
	}
}
