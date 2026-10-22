<?php
/**
 * Durable native login events, replayed through Action Scheduler.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Planner;

use WP_Error;
use WP_Post;

/** One native insert contains the whole event; no split post/meta commit. */
final class ClaimOutbox {

	public const POST_TYPE = 'linker_planner_claim';
	public const HOOK      = 'linker_tools_planner_claim';
	public const SWEEP     = 'linker_tools_planner_claim_sweep';
	public const GROUP     = 'linker-planner';
	/** Bounded background discovery; event retries remain durable, spec 548 gateway. */
	private const BATCH = 32;

	/**
	 * Compose the native capture, persistence and private delivery boundary.
	 *
	 * @param Transport        $transport Private RPC.
	 * @param NativeIdentity   $identity Native cookie reader.
	 * @param TransitionTicket $ticket Bounded native recovery ticket.
	 */
	public function __construct( private readonly Transport $transport = new Transport(), private readonly NativeIdentity $identity = new NativeIdentity(), private readonly TransitionTicket $ticket = new TransitionTicket() ) {}

	/** Must run during plugin bootstrap, before Woo can migrate a session. */
	public function register(): void {
		add_action( 'init', array( $this, 'post_type' ), 0 );
		add_action( 'woocommerce_guest_session_to_user_id', array( $this, 'capture' ), 10, 2 );
		add_action( self::HOOK, array( $this, 'run' ), 10, 2 );
		add_action( self::SWEEP, array( $this, 'sweep' ) );
		add_action( 'action_scheduler_init', array( $this, 'schedule' ) );
	}

	/** Private native storage with no REST/UI/public-query surface. */
	public function post_type(): void {
		register_post_type(
			self::POST_TYPE,
			array(
				'public'       => false,
				'show_ui'      => false,
				'show_in_rest' => false,
				'rewrite'      => false,
				'query_var'    => false,
				'supports'     => array(),
				'can_export'   => false,
			)
		);
	}

	/**
	 * Native Woo has already removed the old row at this hook. Its verified
	 * presented cookie and the authenticated event user are the proof.
	 *
	 * @param string $guest Old native guest ID.
	 * @param string $user New native account ID.
	 */
	public function capture( string $guest, string $user ): void {
		$current = get_current_user_id();
		$session = $this->identity->session();
		$proof   = is_wp_error( $session ) ? null : $this->identity->guest_cookie( $session );
		if ( $current < 1 || (string) $current !== $user || null === $proof || $proof['id'] !== $guest ) {
			return;
		}
		$subject = NativeIdentity::guest_subject( $guest );
		// Bind to the native event's user before any persistence attempt. A
		// subsequent shared-browser login cannot retarget a failed insert.
		$this->ticket->issue( $subject, $proof['expires'], $current );
		$stored = $this->enqueue( $subject, $current );
		if ( ! is_wp_error( $stored ) ) {
			$this->ticket->clear( $subject, $current );
		}
	}

	/**
	 * Recover only signed native transition facts, never request JSON.
	 *
	 * @return bool False means the recovery ticket has not been durably recorded.
	 */
	public function recover(): bool {
		$recovered = true;
		foreach ( $this->ticket->read_all() as $ticket ) {
			$result = $this->enqueue( $ticket['guest'], $ticket['user'] );
			if ( is_wp_error( $result ) || ! $this->ticket->clear( $ticket['guest'], $ticket['user'] ) ) {
				$recovered = false;
			}
		}
		return $recovered && array() === $this->ticket->read_all();
	}

	/**
	 * Persist and read back the complete immutable native event.
	 *
	 * @param string $guest Verified guest subject.
	 * @param int    $user Native verified target.
	 * @return int|WP_Error Durable native record ID.
	 */
	public function enqueue( string $guest, int $user ): int|WP_Error {
		if ( ! TransitionTicket::subject( $guest ) || $user < 1 || false === get_userdata( $user ) ) {
			return Failure::make( 'claim_event', 400 );
		}
		$key     = wp_hash( 'linker-planner-claim:v1|' . $guest . '|' . $user, 'auth', 'sha256' );
		$payload = wp_json_encode(
			array(
				'schema_version' => 1,
				'guest'          => $guest,
				'user'           => $user,
				'key'            => $key,
			)
		);
		if ( ! is_string( $payload ) ) {
			return Failure::make( 'claim_event', 500 );
		}
		$existing = get_posts(
			array(
				'post_type'        => self::POST_TYPE,
				'post_status'      => 'private',
				'name'             => $key,
				'numberposts'      => 1,
				'suppress_filters' => true,
			)
		);
		$id       = isset( $existing[0] ) ? $existing[0]->ID : wp_insert_post(
			wp_slash(
				array(
					'post_type'    => self::POST_TYPE,
					'post_status'  => 'private',
					'post_author'  => $user,
					'post_name'    => $key,
					'post_title'   => $key,
					'post_content' => $payload,
				)
			),
			true
		);
		if ( is_wp_error( $id ) || $id < 1 ) {
			return Failure::make( 'claim_persistence', 503 );
		}
		$readback = get_post( $id );
		if ( ! $readback instanceof WP_Post || $readback->post_content !== $payload || (int) $readback->post_author !== $user || 'private' !== $readback->post_status || self::POST_TYPE !== $readback->post_type ) {
			return Failure::make( 'claim_persistence', 503 );
		}
		$this->queue( $id, 0 );
		return $id;
	}

	/** Repair missed scheduling without losing the immutable event. */
	public function schedule(): void {
		if ( ! wp_next_scheduled( self::SWEEP ) ) {
			wp_schedule_event( time() + HOUR_IN_SECONDS, 'hourly', self::SWEEP );
			$this->sweep();
		}
	}

	/**
	 * Cursor-based native discovery gives failed records fair retry without
	 * allowing an old unresolved event to block the rest of the outbox.
	 */
	public function sweep(): void {
		$cursor = (int) get_option( 'linker_planner_claim_cursor', 0 );
		global $wpdb;
		// phpcs:ignore WordPress.DB.DirectDatabaseQuery.DirectQuery, WordPress.DB.DirectDatabaseQuery.NoCaching -- a bounded private scheduling cursor, no cached ownership decision.
		$ids = $wpdb->get_col( $wpdb->prepare( 'SELECT ID FROM %i WHERE post_type = %s AND post_status = %s AND ID > %d ORDER BY ID ASC LIMIT %d', $wpdb->posts, self::POST_TYPE, 'private', $cursor, self::BATCH ) );
		foreach ( $ids as $id ) {
			$this->queue( (int) $id, 0 );
		}
		update_option( 'linker_planner_claim_cursor', count( $ids ) < self::BATCH ? 0 : (int) end( $ids ), false );
	}

	/**
	 * Deliver one event and schedule its bounded retry.
	 *
	 * @param int $id Native outbox post.
	 * @param int $attempt Scheduler retry number, never part of event identity.
	 */
	public function run( int $id, int $attempt = 0 ): void {
		if ( ! $this->deliver( $id ) ) {
			$this->queue( $id, $attempt + 1 );
		}
	}

	/**
	 * Check whether the current account has unresolved native events.
	 *
	 * @param int $user Current native account.
	 */
	public function pending( int $user ): bool {
		return $this->next_event( $user ) > 0;
	}

	/**
	 * One bounded foreground recovery on account bootstrap. Remaining work is
	 * still visible as pending and continues through the native scheduler.
	 *
	 * @param int $user Current native account.
	 */
	public function settle( int $user ): void {
		$id = $this->next_event( $user );
		if ( $id > 0 ) {
			$this->run( $id );
		}
	}

	/**
	 * Find one unresolved native event for an account.
	 *
	 * @param int $user Current native account.
	 */
	private function next_event( int $user ): int {
		if ( $user < 1 ) {
			return 0;
		}
		$ids = get_posts(
			array(
				'post_type'        => self::POST_TYPE,
				'post_status'      => 'private',
				'author'           => $user,
				'numberposts'      => 1,
				'fields'           => 'ids',
				'suppress_filters' => true,
			)
		);
		return isset( $ids[0] ) ? (int) $ids[0] : 0;
	}

	/**
	 * Confirm the complete private claim receipt before deleting an event.
	 *
	 * @param int $id Immutable native event.
	 */
	private function deliver( int $id ): bool {
		$post = get_post( $id );
		if ( ! $post instanceof WP_Post || self::POST_TYPE !== $post->post_type || 'private' !== $post->post_status ) {
			return true;
		}
		$event = json_decode( $post->post_content, true, 8 );
		if ( ! is_array( $event ) || array_keys( $event ) !== array( 'schema_version', 'guest', 'user', 'key' ) || 1 !== $event['schema_version'] || ! is_string( $event['guest'] ) || ! TransitionTicket::subject( $event['guest'] ) || ! is_int( $event['user'] ) || $event['user'] < 1 || (int) $post->post_author !== $event['user'] || ! is_string( $event['key'] ) || 1 !== preg_match( '/\A[a-f0-9]{64}\z/', $event['key'] ) || false === get_userdata( $event['user'] ) ) {
			return false;
		}
		$reply = $this->transport->object(
			new Principal( 'user', NativeIdentity::user_subject( $event['user'] ) ),
			'identity/claim-session',
			array(
				'schema_version' => 1,
				'key'            => $event['key'],
			),
			$event['guest']
		);
		if ( is_wp_error( $reply ) || 1 !== ( $reply['schema_version'] ?? null ) || 'claimed' !== ( $reply['status'] ?? null ) || true !== ( $reply['guest_retired'] ?? null ) || ! is_int( $reply['transferred_count'] ?? null ) || $reply['transferred_count'] < 0 ) {
			return false;
		}
		// A failed delete retains the event. Replaying the same key is safe.
		return wp_delete_post( $id, true ) instanceof WP_Post;
	}

	/**
	 * Schedule an idempotent background delivery.
	 *
	 * @param int $id Native event ID.
	 * @param int $attempt Retry counter, independent of the event key.
	 */
	private function queue( int $id, int $attempt ): void {
		if ( ! did_action( 'action_scheduler_init' ) ) {
			return;
		}
		$args = array( $id, $attempt );
		if ( as_has_scheduled_action( self::HOOK, $args, self::GROUP ) ) {
			return;
		}
		// Operational retry policy: 1, 2, 4, 8 then 15 minutes. No event expiry.
		$delay = 0 === $attempt ? 0 : min( 15 * MINUTE_IN_SECONDS, MINUTE_IN_SECONDS * ( 2 ** min( $attempt - 1, 4 ) ) );
		as_schedule_single_action( time() + $delay, self::HOOK, $args, self::GROUP, true );
	}
}
