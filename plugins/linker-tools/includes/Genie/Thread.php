<?php
/**
 * The thread of one conversation, kept on the conversation post.
 *
 * A reload must not throw the conversation away (docs/specs/13-genie.md, the
 * message-reload row of #16): the customer opens Genie from a category page,
 * follows a link to a product and opens it again, and the thread they built
 * is still there. The store is the site's own: the `linker_conversation`
 * post the cookie or the signed-in user already identifies
 * (Conversations), and two pieces of its meta — the messages the browser
 * sent with the answered turn, and that turn's SSE stream, exactly as the
 * service wrote it. Two turns in flight at once used to each write that
 * whole snapshot, so the later write erased the earlier turn (#373). The
 * commit now keeps both: a snapshot that already contains the stored
 * history is written from that history, and a stale snapshot appends only
 * its new user turn. Assistant text is compared with whitespace folded,
 * so a client that rendered the same answer differently still lines up.
 * The stream is stored raw so the shell parses it with the same reader it
 * uses for a live turn; nothing here re-implements what an answer's text is.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Genie;

/**
 * Reads and writes the thread meta of a conversation post.
 */
class Thread {

	/**
	 * Meta key: the messages of the last answered turn.
	 */
	public const MESSAGES = 'linker_genie_thread';

	/**
	 * Meta key: the last answered turn's SSE stream.
	 */
	public const STREAM = 'linker_genie_turn';

	/**
	 * Meta key: the products each answer's cards showed, by the answer's text.
	 */
	public const PRODUCTS = 'linker_genie_products';

	/**
	 * Meta key: when the conversation last moved (opened, or a turn was
	 * answered), unix time. The history list orders by it.
	 */
	public const ACTIVITY = 'linker_genie_activity';

	/**
	 * Meta key: what the service read from the files the customer attached
	 * (#236), oldest first. The file itself is never kept: the reading is the
	 * conversation's memory of it, sent back with every turn so a later
	 * question needs no new upload, and it goes when the conversation goes
	 * (deleted with the post, by the customer or by Retention).
	 */
	public const READINGS = 'linker_genie_readings';

	/**
	 * Readings kept: the service's MAX_READINGS (services/genie schema.py).
	 */
	public const READINGS_LIMIT = 10;

	/**
	 * How many messages are kept. The thread rides in every request, so an
	 * unbounded one would grow the body without bound; a conversation this
	 * long is one nobody scrolls back through.
	 */
	public const LIMIT = 60;

	/**
	 * Seconds a commit waits for the lock when the caller is not already
	 * inside a turn.
	 *
	 * The HTTP turn does not use this ceiling. It passes the seconds left
	 * of Proxy::TURN_BUDGET (60, the same number as wp_remote_post's
	 * timeout: at most four ability calls, each capped at twenty seconds
	 * in the service, plus the model). The lock wait is that remainder, so
	 * a 60 s model call and a 60 s lock wait do not stack (#373). This
	 * constant is only the wait for a commit with no model call in front
	 * of it (tests, mail fixtures). It is the same 60 so one slow
	 * postmeta write cannot outlast the turn the customer is already
	 * waiting on. The integration fixture holds the lock for 300 ms, well
	 * under it.
	 */
	private const LOCK_WAIT = 60;

	/**
	 * The stored thread: messages and the last turn's stream.
	 *
	 * @param int $conversation Conversation post ID.
	 * @return array{messages: list<array<string, mixed>>, stream: string}
	 */
	public function read( int $conversation ): array {
		$empty = array(
			'messages' => array(),
			'stream'   => '',
		);
		if ( $conversation < 1 ) {
			return $empty;
		}
		$messages = get_post_meta( $conversation, self::MESSAGES, true );
		$stream   = get_post_meta( $conversation, self::STREAM, true );
		return array(
			'messages' => is_array( $messages ) ? array_values( $messages ) : array(),
			'stream'   => is_string( $stream ) ? $stream : '',
		);
	}

	/**
	 * Records one answered turn onto the stored thread.
	 *
	 * A single writer sends a thread that already contains what is stored,
	 * and that thread is what gets kept, as before. Two writers that each
	 * snapped the same history would otherwise replace the whole meta with
	 * their own copy and drop the other turn (dossier
	 * docs/research/2026-10-19-genie-campaign-gaps/DOSSIER.md §1.16, no
	 * public competitor semantics, so this is our own rule, #373): the
	 * commit is serialized per conversation, and a stale snapshot appends
	 * its new user turn onto whatever is already stored. The order is the
	 * order the commits acquired the lock. A snapshot that forks the
	 * stored thread, or a lock that is not acquired inside the wait, is
	 * not written — the caller refuses the turn instead of erasing one.
	 * An exact re-send of the turn already stored is accepted, not refused.
	 *
	 * @param int                        $conversation Conversation post ID.
	 * @param array<array-key, mixed>    $messages The request's messages; the shape is
	 *                                             the browser's, so entries are checked.
	 * @param string                     $stream       The service's SSE text, its `reading` events taken out (split).
	 * @param list<array<string, mixed>> $readings     What the turn read from its files (split).
	 * @param int|null                   $lock_wait    Seconds to wait for the lock. Null uses LOCK_WAIT. The HTTP turn passes the remainder of Proxy::TURN_BUDGET.
	 * @return bool False when nothing was written (no conversation, the lock was not acquired, a meta write failed, or the snapshot forks the stored thread).
	 */
	public function record( int $conversation, array $messages, string $stream, array $readings = array(), ?int $lock_wait = null ): bool {
		if ( $conversation < 1 ) {
			return false;
		}
		$wait = null === $lock_wait ? self::LOCK_WAIT : max( 0, $lock_wait );
		if ( ! $this->lock( $conversation, $wait ) ) {
			return false;
		}
		try {
			$kept = $this->plan( $conversation, $messages );
			if ( null === $kept ) {
				return false;
			}
			$this->while_locked( $conversation );
			// GET_LOCK is per connection. wpdb reconnects after "server has
			// gone away" and the lock is gone, while this request would
			// otherwise keep writing. A null lookup is also what a failed
			// query returns: a second GET_LOCK would raise the counter if
			// this connection still held the name, and the one RELEASE_LOCK
			// below would leave it held. Abort. An explicit 0 means this
			// connection does not hold it, so acquiring it is safe; the gap
			// may have committed another turn, so plan again.
			$owned = $this->owns( $conversation );
			if ( true !== $owned ) {
				if ( false !== $owned || ! $this->lock( $conversation, $wait ) ) {
					return false;
				}
				$kept = $this->plan( $conversation, $messages );
				if ( null === $kept || true !== $this->owns( $conversation ) ) {
					return false;
				}
			}
			return $this->write( $conversation, $kept, $stream, $readings );
		} catch ( \Throwable $failure ) {
			// A thrown meta write must not look like success. write()
			// restores what it changed; this returns the 409 path.
			unset( $failure );
			return false;
		} finally {
			$this->unlock( $conversation );
		}
	}

	/**
	 * The messages to store, read after the postmeta cache was dropped.
	 *
	 * The first get_post_meta of this request (the readings sent with the
	 * model call) cached every key. That copy is from before a peer's
	 * commit.
	 *
	 * @param int                     $conversation Conversation post ID.
	 * @param array<array-key, mixed> $messages     The browser's snapshot.
	 * @return list<array{role: 'user'|'assistant', content: string}>|null
	 */
	private function plan( int $conversation, array $messages ): ?array {
		wp_cache_delete( $conversation, 'post_meta' );
		$stored = $this->read( $conversation );
		return self::committed( $stored['messages'], $stored['stream'], $messages );
	}

	/**
	 * Runs inside the commit lock, after the stored thread was read and
	 * before it is written. Production does nothing.
	 *
	 * The concurrency fixture subclasses Thread and pauses here, so the
	 * other process blocks in GET_LOCK and then merges (#373). A
	 * production action is not required for that pause.
	 *
	 * @param int $conversation Conversation post ID.
	 */
	protected function while_locked( int $conversation ): void {
		unset( $conversation );
	}

	/**
	 * The messages to store for this commit, or null when storing them
	 * would drop or fork a turn.
	 *
	 * The stored history includes the previous turn's answer text. That
	 * answer lives only in the stream until the next commit copies it
	 * into the messages (transcript()).
	 *
	 * @param list<array<string, mixed>> $stored_messages Messages already stored.
	 * @param string                     $stored_stream   The previous turn's stream.
	 * @param array<array-key, mixed>    $request_messages The browser's snapshot, including its new user turn.
	 * @return list<array{role: 'user'|'assistant', content: string}>|null
	 */
	private static function committed( array $stored_messages, string $stored_stream, array $request_messages ): ?array {
		$history = self::history( $stored_messages, $stored_stream );
		$request = self::normalize( $request_messages );
		if ( array() === $history ) {
			return self::cap( $request );
		}
		$at = self::find_span( $request, $history );
		if ( null !== $at ) {
			$suffix = array_slice( $request, $at + count( $history ) );
			if ( array() === $suffix ) {
				// The request already is the stored thread. Keep the
				// canonical text; the caller may replace the stream.
				return self::cap( $history );
			}
			if ( self::users_only( $suffix ) ) {
				return self::cap( array_merge( $history, self::collapse_users( $suffix ) ) );
			}
			return null;
		}
		$shared = self::prefix_length( $history, $request );
		$added  = array_slice( $request, $shared );
		$unseen = array_slice( $history, $shared );
		// The response to this turn was lost. The retry sends the stored
		// messages without the answer. Accept it: do not append the
		// question again, and do not answer 409 (#373).
		if ( array() === $added && self::answer_only( $unseen ) ) {
			return self::cap( array_slice( $history, 0, $shared ) );
		}
		// The snapshot branched off an earlier prefix and its only new
		// entries are the user turn it asked. Append that turn. The
		// stored turns stay, in the order they committed. A tail that
		// only repeats the user message already stored (the browser kept
		// a refused question and sent it again) is the same turn.
		if ( array() !== $added && array() !== $unseen && self::users_only( $added ) ) {
			$collapsed = self::collapse_users( $added );
			if ( self::answer_only( $unseen ) && self::repeats_stored_user( $history, $shared, $collapsed ) ) {
				return self::cap( array_slice( $history, 0, $shared ) );
			}
			return self::cap( array_merge( $history, $collapsed ) );
		}
		// The other tab's turns were merged into the middle. This
		// client's own answer is already stored, so the next question is
		// a user tail on top of that, not a fork.
		$tail = self::merged_tail( $history, $request );
		if ( null !== $tail ) {
			return self::cap( array_merge( $history, $tail ) );
		}
		return null;
	}

	/**
	 * Stored messages plus the previous answer, which the stream still holds.
	 *
	 * @param array<array-key, mixed> $stored_messages Stored messages.
	 * @param string                  $stored_stream   Stored stream.
	 * @return list<array{role: 'user'|'assistant', content: string}>
	 */
	private static function history( array $stored_messages, string $stored_stream ): array {
		$history = self::normalize( $stored_messages );
		$text    = self::answer( $stored_stream )['text'];
		if ( '' === $text ) {
			return $history;
		}
		if ( array() !== $history ) {
			$last = $history[ array_key_last( $history ) ];
			if ( 'assistant' === $last['role'] && $last['content'] === $text ) {
				return $history;
			}
		}
		$history[] = array(
			'role'    => 'assistant',
			'content' => $text,
		);
		return $history;
	}

	/**
	 * Message entries the thread keeps: a role and a non-empty content.
	 *
	 * @param array<array-key, mixed> $messages Entries as sent, or as stored.
	 * @return list<array{role: 'user'|'assistant', content: string}>
	 */
	private static function normalize( array $messages ): array {
		$kept = array();
		foreach ( $messages as $message ) {
			if ( ! is_array( $message ) ) {
				continue;
			}
			$content = isset( $message['content'] ) ? (string) $message['content'] : '';
			if ( '' === $content ) {
				continue;
			}
			$kept[] = array(
				'role'    => self::role( $message['role'] ?? '' ),
				'content' => $content,
			);
		}
		return $kept;
	}

	/**
	 * Where `$span` sits in `$request`, preferring the rightmost match so
	 * the stored tail lines up with the end of the snapshot.
	 *
	 * @param list<array{role: 'user'|'assistant', content: string}> $request Snapshot.
	 * @param list<array{role: 'user'|'assistant', content: string}> $span    Stored history.
	 */
	private static function find_span( array $request, array $span ): ?int {
		$width = count( $span );
		$total = count( $request );
		if ( $width < 1 || $width > $total ) {
			return null;
		}
		for ( $start = $total - $width; $start >= 0; --$start ) {
			$matches = true;
			for ( $index = 0; $index < $width; ++$index ) {
				if ( ! self::same_message( $request[ $start + $index ], $span[ $index ] ) ) {
					$matches = false;
					break;
				}
			}
			if ( $matches ) {
				return $start;
			}
		}
		return null;
	}

	/**
	 * How far the two lists are the same from the start.
	 *
	 * @param list<array{role: 'user'|'assistant', content: string}> $history Stored history.
	 * @param list<array{role: 'user'|'assistant', content: string}> $request Snapshot.
	 */
	private static function prefix_length( array $history, array $request ): int {
		$width = min( count( $history ), count( $request ) );
		$index = 0;
		while ( $index < $width && self::same_message( $history[ $index ], $request[ $index ] ) ) {
			++$index;
		}
		return $index;
	}

	/**
	 * The same turn: equal role, and text that differs only by whitespace.
	 *
	 * The shell joins a turn's text blocks with a space
	 * (`assistantMessage`). A client that folded newlines or repeated
	 * spaces still means that answer. Byte equality made any such gap a
	 * permanent 409 until reload (#373).
	 *
	 * @param array{role: 'user'|'assistant', content: string} $left  One message.
	 * @param array{role: 'user'|'assistant', content: string} $right The other.
	 */
	private static function same_message( array $left, array $right ): bool {
		return $left['role'] === $right['role'] && self::flat( $left['content'] ) === self::flat( $right['content'] );
	}

	/**
	 * Whitespace folded to single spaces, ends trimmed.
	 *
	 * @param string $text Message text.
	 */
	private static function flat( string $text ): string {
		$flat = preg_replace( '/\s+/u', ' ', trim( $text ) );
		return is_string( $flat ) ? $flat : trim( $text );
	}

	/**
	 * True when the only unseen stored entry is the answer in the stream.
	 *
	 * @param list<array{role: 'user'|'assistant', content: string}> $messages Entries.
	 */
	private static function answer_only( array $messages ): bool {
		return 1 === count( $messages ) && 'assistant' === $messages[0]['role'];
	}

	/**
	 * Consecutive user messages with the same text become one.
	 *
	 * A refused turn leaves the question in the browser. The retry appends
	 * it again, so the tail is the question twice and neither was
	 * answered. One of them is the turn (#373).
	 *
	 * @param list<array{role: 'user'|'assistant', content: string}> $messages Entries.
	 * @return list<array{role: 'user'|'assistant', content: string}>
	 */
	private static function collapse_users( array $messages ): array {
		$out = array();
		foreach ( $messages as $message ) {
			$previous = array() === $out ? null : $out[ array_key_last( $out ) ];
			if ( null !== $previous && self::same_message( $previous, $message ) ) {
				continue;
			}
			$out[] = $message;
		}
		return $out;
	}

	/**
	 * True when every new entry repeats the user message the matched
	 * prefix already ends with.
	 *
	 * @param list<array{role: 'user'|'assistant', content: string}> $history   Stored history.
	 * @param int                                                    $shared    How far the prefix matched.
	 * @param list<array{role: 'user'|'assistant', content: string}> $collapsed The request's new entries.
	 */
	private static function repeats_stored_user( array $history, int $shared, array $collapsed ): bool {
		if ( $shared < 1 || array() === $collapsed ) {
			return false;
		}
		$last = $history[ $shared - 1 ];
		if ( 'user' !== $last['role'] ) {
			return false;
		}
		foreach ( $collapsed as $message ) {
			if ( ! self::same_message( $last, $message ) ) {
				return false;
			}
		}
		return true;
	}

	/**
	 * The new user messages at the end of a request whose earlier entries
	 * are this client's own turns, already stored among the peer's.
	 *
	 * Null when an assistant entry is not in the stored history, or when
	 * nothing new was asked. The caller appends the list it returns.
	 *
	 * @param list<array{role: 'user'|'assistant', content: string}> $history Stored history.
	 * @param list<array{role: 'user'|'assistant', content: string}> $request Snapshot.
	 * @return list<array{role: 'user'|'assistant', content: string}>|null
	 */
	private static function merged_tail( array $history, array $request ): ?array {
		$cursor  = 0;
		$count   = count( $history );
		$pending = array();
		foreach ( $request as $message ) {
			$found = null;
			for ( $index = $cursor; $index < $count; ++$index ) {
				if ( self::same_message( $history[ $index ], $message ) ) {
					$found = $index;
					break;
				}
			}
			if ( null !== $found ) {
				if ( array() !== $pending ) {
					return null;
				}
				$cursor = $found + 1;
				continue;
			}
			if ( 'user' !== $message['role'] ) {
				return null;
			}
			$pending[] = $message;
		}
		if ( array() === $pending ) {
			return null;
		}
		return self::collapse_users( $pending );
	}

	/**
	 * True when every entry is a user message. An assistant entry means
	 * the snapshot carries an answer the store does not have in that place.
	 *
	 * @param list<array{role: 'user'|'assistant', content: string}> $messages Entries.
	 */
	private static function users_only( array $messages ): bool {
		foreach ( $messages as $message ) {
			if ( 'user' !== $message['role'] ) {
				return false;
			}
		}
		return true;
	}

	/**
	 * The newest messages, within LIMIT.
	 *
	 * @param list<array{role: 'user'|'assistant', content: string}> $messages Entries.
	 * @return list<array{role: 'user'|'assistant', content: string}>
	 */
	private static function cap( array $messages ): array {
		if ( count( $messages ) > self::LIMIT ) {
			return array_slice( $messages, -self::LIMIT );
		}
		return $messages;
	}

	/**
	 * Acquires the conversation's commit lock.
	 *
	 * GET_LOCK is per database connection, so two PHP requests each have
	 * their own and the second waits. The connection closing releases it
	 * if this request dies before unlock(). A same-connection GET_LOCK
	 * increments a counter, so this is called again only when owns() says
	 * the lock is already gone; one RELEASE_LOCK then drops it.
	 *
	 * @param int $conversation Conversation post ID.
	 * @param int $wait         Seconds to wait. Zero tries once.
	 */
	private function lock( int $conversation, int $wait ): bool {
		global $wpdb;
		$name = $this->lock_name( $conversation );
		// phpcs:ignore WordPress.DB.DirectDatabaseQuery.DirectQuery, WordPress.DB.DirectDatabaseQuery.NoCaching -- a MySQL named lock, not a row to cache.
		$got = $wpdb->get_var( $wpdb->prepare( 'SELECT GET_LOCK(%s, %d)', $name, $wait ) );
		return '1' === (string) $got;
	}

	/**
	 * Whether this connection still holds the commit lock.
	 *
	 * IS_USED_LOCK returns the connection id that holds the name. Compared
	 * with CONNECTION_ID(), that is 1 when this connection holds it, 0 when
	 * another connection does, and null when nobody does or the query
	 * failed. Null is not "explicitly not held": record() aborts rather
	 * than taking the lock a second time (#373).
	 *
	 * @param int $conversation Conversation post ID.
	 * @return bool|null True when this connection holds it, false when the comparison is 0, null when the lookup did not answer.
	 */
	private function owns( int $conversation ): ?bool {
		global $wpdb;
		$name = $this->lock_name( $conversation );
		// phpcs:ignore WordPress.DB.DirectDatabaseQuery.DirectQuery, WordPress.DB.DirectDatabaseQuery.NoCaching -- the named lock's owner, not a row to cache.
		$owned = $wpdb->get_var( $wpdb->prepare( 'SELECT IS_USED_LOCK(%s) = CONNECTION_ID()', $name ) );
		if ( null === $owned ) {
			return null;
		}
		$owned = (string) $owned;
		if ( '1' === $owned ) {
			return true;
		}
		if ( '0' === $owned ) {
			return false;
		}
		return null;
	}

	/**
	 * Releases the commit lock. A connection that already dropped it
	 * answers null; there is nothing further to do.
	 *
	 * @param int $conversation Conversation post ID.
	 */
	private function unlock( int $conversation ): void {
		global $wpdb;
		$name = $this->lock_name( $conversation );
		// phpcs:ignore WordPress.DB.DirectDatabaseQuery.DirectQuery, WordPress.DB.DirectDatabaseQuery.NoCaching -- releases the named lock lock() acquired.
		$wpdb->get_var( $wpdb->prepare( 'SELECT RELEASE_LOCK(%s)', $name ) );
	}

	/**
	 * The MySQL name of this conversation's commit lock.
	 *
	 * GET_LOCK names are server-wide and at most 64 characters (MySQL 8.0
	 * reference manual, GET_LOCK). Reference, staging and live on one
	 * server share conversation post ids, so the name includes the
	 * database and the table prefix. A longer name is the sha256 of that
	 * string, which is 64 hex characters (#373).
	 *
	 * @param int $conversation Conversation post ID.
	 */
	private function lock_name( int $conversation ): string {
		global $wpdb;
		$database = '';
		if ( isset( $wpdb->dbname ) && is_string( $wpdb->dbname ) && '' !== $wpdb->dbname ) {
			$database = $wpdb->dbname;
		} elseif ( defined( 'DB_NAME' ) ) {
			$database = (string) constant( 'DB_NAME' );
		}
		$prefix = isset( $wpdb->prefix ) && is_string( $wpdb->prefix ) ? $wpdb->prefix : '';
		$name   = $database . '/' . $prefix . 'linker_genie_turn_' . $conversation;
		if ( strlen( $name ) <= 64 ) {
			return $name;
		}
		return hash( 'sha256', $name );
	}

	/**
	 * Writes the commit, or restores the previous meta if a write does not
	 * land.
	 *
	 * One update_post_meta call is one key at a time. A stream that fails after
	 * the messages were replaced leaves the old answer on the new user
	 * turn (#373). The previous values are captured first and written
	 * back; record() then returns false. WordPress has no transaction
	 * around post meta, so a crash between the writes can still leave a
	 * gap. A returned success means every key was checked.
	 *
	 * @param int                                                    $conversation Conversation post ID.
	 * @param list<array{role: 'user'|'assistant', content: string}> $kept         Messages to store.
	 * @param string                                                 $stream       The turn's stream.
	 * @param list<array<string, mixed>>                             $readings     Readings to append.
	 */
	private function write( int $conversation, array $kept, string $stream, array $readings ): bool {
		$answer   = self::answer( $stream );
		$products = $this->products( $conversation );
		$known    = array();
		foreach ( $kept as $message ) {
			if ( 'assistant' === $message['role'] && isset( $products[ self::key( $message['content'] ) ] ) ) {
				$known[ self::key( $message['content'] ) ] = $products[ self::key( $message['content'] ) ];
			}
		}
		if ( '' !== $answer['text'] && array() !== $answer['products'] ) {
			$known[ self::key( $answer['text'] ) ] = $answer['products'];
		}
		$writes = array(
			self::MESSAGES => $kept,
			self::STREAM   => $stream,
			self::PRODUCTS => $known,
			self::ACTIVITY => time(),
		);
		if ( array() !== $readings ) {
			$kept_readings            = array_merge( $this->readings( $conversation ), $readings );
			$writes[ self::READINGS ] = array_slice( $kept_readings, -self::READINGS_LIMIT );
		}
		$previous = array();
		foreach ( array_keys( $writes ) as $key ) {
			$previous[ $key ] = get_post_meta( $conversation, $key, true );
		}
		$done = array();
		try {
			foreach ( $writes as $key => $value ) {
				if ( ! $this->put_meta( $conversation, $key, $value ) ) {
					$this->restore_meta( $conversation, $previous, $done, $key );
					return false;
				}
				$done[] = $key;
			}
		} catch ( \Throwable $failure ) {
			unset( $failure );
			$this->restore_meta( $conversation, $previous, $done, null );
			return false;
		}
		return true;
	}

	/**
	 * Writes one meta key back to the value it had before this commit.
	 *
	 * @param int                  $conversation Conversation post ID.
	 * @param array<string, mixed> $previous     Values captured before the writes.
	 * @param string[]             $done         Keys whose new value landed.
	 * @param string|null          $failed       The key that failed, when the failure was a false return.
	 */
	private function restore_meta( int $conversation, array $previous, array $done, ?string $failed ): void {
		$keys = $done;
		if ( null !== $failed ) {
			$keys[] = $failed;
		}
		foreach ( $keys as $key ) {
			$this->put_meta( $conversation, $key, $previous[ $key ] ?? '' );
		}
	}

	/**
	 * Writes one meta value and checks that the store holds it.
	 *
	 * The update_post_meta return is false both when the write fails and when
	 * the value is unchanged. The read-back is the difference: unchanged
	 * is success. Messages and the stream are passed through wp_slash so
	 * JSON escapes survive WordPress unslashing them (#223).
	 *
	 * @param int    $conversation Conversation post ID.
	 * @param string $key          Meta key.
	 * @param mixed  $value        Value as record() wants it stored.
	 */
	private function put_meta( int $conversation, string $key, mixed $value ): bool {
		$slashed = ( self::MESSAGES === $key || self::STREAM === $key ) ? wp_slash( $value ) : $value;
		$written = update_post_meta( $conversation, $key, $slashed );
		if ( false !== $written ) {
			return true;
		}
		wp_cache_delete( $conversation, 'post_meta' );
		$current = get_post_meta( $conversation, $key, true );
		$stored  = $value;
		if ( function_exists( 'wp_unslash' ) && ( self::MESSAGES === $key || self::STREAM === $key ) ) {
			$stored = wp_unslash( $slashed );
		}
		return $current == $stored; // phpcs:ignore Universal.Operators.StrictComparisons.LooseEqual -- post meta scalars come back as strings.
	}

	/**
	 * What the service read from this conversation's files, oldest first.
	 *
	 * @param int $conversation Conversation post ID.
	 * @return list<array<string, mixed>>
	 */
	public function readings( int $conversation ): array {
		if ( $conversation < 1 ) {
			return array();
		}
		$stored = get_post_meta( $conversation, self::READINGS, true );
		$out    = array();
		foreach ( is_array( $stored ) ? $stored : array() as $reading ) {
			if ( is_array( $reading ) && is_string( $reading['id'] ?? null ) ) {
				$out[] = $reading;
			}
		}
		return $out;
	}

	/**
	 * A turn's stream without its `reading` events, and those readings.
	 *
	 * The service sends what it read from the turn's files as `reading`
	 * events, for this store only: the browser gets the `attachment` events
	 * (what each file is and how it matched), never the whole text again.
	 *
	 * @param string $stream SSE text.
	 * @return array{stream: string, readings: list<array<string, mixed>>}
	 */
	public static function split( string $stream ): array {
		$kept     = array();
		$readings = array();
		foreach ( explode( "\n\n", $stream ) as $event ) {
			if ( 1 === preg_match( '/^event: reading$/m', $event ) ) {
				if ( 1 === preg_match( '/^data: (.+)$/m', $event, $data ) ) {
					$reading = json_decode( $data[1], true );
					if ( is_array( $reading ) && is_string( $reading['id'] ?? null ) ) {
						$readings[] = $reading;
					}
				}
				continue;
			}
			$kept[] = $event;
		}
		return array(
			'stream'   => implode( "\n\n", $kept ),
			'readings' => $readings,
		);
	}

	/**
	 * The whole conversation as the customer read it: the stored messages,
	 * then the last answer's text, each answer with the products its cards
	 * showed.
	 *
	 * The last answer lives only in its stream. Its text is the stream's
	 * text blocks joined by a space, which is what the shell's
	 * `assistantMessage()` (src/genie/api/turn.ts) shows; its products are
	 * the stream's cards block. A stream without its `done` event is no
	 * answer, as in the shell's `parseStream()`.
	 *
	 * @param int $conversation Conversation post ID.
	 * @return list<array{role: 'user'|'assistant', content: string, products: list<int>}>
	 */
	public function transcript( int $conversation ): array {
		$stored   = $this->read( $conversation );
		$products = $this->products( $conversation );
		$messages = array();
		foreach ( $stored['messages'] as $message ) {
			$role       = self::role( $message['role'] ?? '' );
			$content    = (string) ( $message['content'] ?? '' );
			$messages[] = array(
				'role'     => $role,
				'content'  => $content,
				'products' => 'assistant' === $role ? ( $products[ self::key( $content ) ] ?? array() ) : array(),
			);
		}
		$answer = self::answer( $stored['stream'] );
		if ( '' !== $answer['text'] && array() !== $messages ) {
			$messages[] = array(
				'role'     => 'assistant',
				'content'  => $answer['text'],
				'products' => $answer['products'],
			);
		}
		return $messages;
	}

	/**
	 * A message's role: `assistant`, or `user` for anything else. The one
	 * place the thread decides it.
	 *
	 * @param mixed $role The role as sent.
	 * @return 'user'|'assistant'
	 */
	public static function role( mixed $role ): string {
		return 'assistant' === $role ? 'assistant' : 'user';
	}

	/**
	 * The stored products by answer.
	 *
	 * @param int $conversation Conversation post ID.
	 * @return array<string, list<int>>
	 */
	private function products( int $conversation ): array {
		$stored = get_post_meta( $conversation, self::PRODUCTS, true );
		$out    = array();
		foreach ( is_array( $stored ) ? $stored : array() as $key => $ids ) {
			if ( is_string( $key ) && is_array( $ids ) ) {
				$out[ $key ] = array_values( array_map( 'intval', $ids ) );
			}
		}
		return $out;
	}

	/**
	 * The key an answer's products are kept under.
	 *
	 * @param string $text The answer's text.
	 */
	private static function key( string $text ): string {
		return sha1( $text );
	}

	/**
	 * The text and the card products of one finished turn's stream; both
	 * empty when it did not finish.
	 *
	 * @param string $stream SSE text.
	 * @return array{text: string, products: list<int>}
	 */
	private static function answer( string $stream ): array {
		$texts    = array();
		$products = array();
		$done     = false;
		foreach ( explode( "\n\n", $stream ) as $event ) {
			if ( 1 !== preg_match( '/^event: (.+)$/m', $event, $name ) || 1 !== preg_match( '/^data: (.+)$/m', $event, $data ) ) {
				continue;
			}
			if ( 'done' === $name[1] ) {
				$done = true;
				continue;
			}
			$block = json_decode( $data[1], true );
			if ( 'block' !== $name[1] || ! is_array( $block ) ) {
				continue;
			}
			if ( 'text' === ( $block['type'] ?? '' ) && is_string( $block['text'] ?? null ) ) {
				$texts[] = $block['text'];
			}
			if ( 'cards' === ( $block['type'] ?? '' ) && is_array( $block['product_ids'] ?? null ) ) {
				foreach ( $block['product_ids'] as $id ) {
					$products[] = (int) $id;
				}
			}
		}
		return $done ? array(
			'text'     => implode( ' ', $texts ),
			'products' => array_values( array_unique( array_filter( $products ) ) ),
		) : array(
			'text'     => '',
			'products' => array(),
		);
	}
}
