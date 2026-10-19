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
 * history is written as before, and a stale snapshot appends only its new
 * user turn. The stream is stored raw so the shell parses it with the
 * same reader it uses for a live turn; nothing here re-implements what an
 * answer's text is.
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
	 * Seconds to wait for this conversation's commit lock before the turn
	 * is refused instead of written.
	 *
	 * The same 60 seconds Proxy gives one turn (Proxy::post): at most four
	 * ability calls, each capped at twenty seconds, plus the model. The
	 * lock covers only the postmeta read-modify-write, not that call, so a
	 * peer finishes well inside it. Sixty is the fail-closed ceiling, not
	 * a new wait the customer should expect.
	 */
	private const LOCK_WAIT = 60;

	/**
	 * Fires inside the commit lock, after the stored thread has been read
	 * and before it is written. Nothing in production listens. The
	 * concurrency regression holds the lock across the pause so a second
	 * writer blocks in GET_LOCK and then merges, instead of both reading
	 * the old snapshot (#373).
	 */
	public const LOCKED = 'linker_tools_genie_turn_locked';

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
	 * stored thread, or a lock that is not acquired inside LOCK_WAIT, is
	 * not written — the caller refuses the turn instead of erasing one.
	 *
	 * @param int                        $conversation Conversation post ID.
	 * @param array<array-key, mixed>    $messages The request's messages; the shape is
	 *                                             the browser's, so entries are checked.
	 * @param string                     $stream       The service's SSE text, its `reading` events taken out (split).
	 * @param list<array<string, mixed>> $readings  What the turn read from its files (split).
	 * @return bool False when nothing was written (no conversation, the lock was not acquired, or the snapshot forks the stored thread).
	 */
	public function record( int $conversation, array $messages, string $stream, array $readings = array() ): bool {
		if ( $conversation < 1 ) {
			return false;
		}
		if ( ! $this->lock( $conversation ) ) {
			return false;
		}
		try {
			// The first get_post_meta of this request (the readings sent
			// with the model call) cached every key. That copy is from
			// before a peer's commit. Drop it so this read hits the
			// database.
			wp_cache_delete( $conversation, 'post_meta' );
			$stored = $this->read( $conversation );
			$kept   = self::committed( $stored['messages'], $stored['stream'], $messages );
			if ( null === $kept ) {
				return false;
			}
			// Priority 0 is a real listener: has_action() returns the priority, and 0 is falsy.
			if ( function_exists( 'has_action' ) && false !== has_action( self::LOCKED ) ) {
				/**
				 * Fires inside the commit lock, after the stored thread was
				 * read and before it is written. Production does not listen.
				 * The concurrency regression pauses here so the other writer
				 * blocks in GET_LOCK (#373).
				 *
				 * @since 0.1.0
				 *
				 * @param int $conversation Conversation post ID.
				 */
				do_action( self::LOCKED, $conversation ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- Thread::LOCKED, whose name is linker_tools_genie_turn_locked.
			}
			if ( array() !== $readings ) {
				$kept_readings = array_merge( $this->readings( $conversation ), $readings );
				update_post_meta( $conversation, self::READINGS, array_slice( $kept_readings, -self::READINGS_LIMIT ) );
			}
			// The products each answer showed, by the answer's text: the
			// browser sends earlier answers back as text only, so the text is
			// how a later transcript finds them. Only answers still in the
			// thread keep theirs.
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
			// WordPress unslashes meta before storage. Preserve JSON escapes and
			// literal backslashes so reopening renders the original answer (#223).
			// Direct $wpdb writes are not used here: wp_slash is what keeps
			// those escapes, and the lock above is what keeps the other turn.
			update_post_meta( $conversation, self::MESSAGES, wp_slash( $kept ) );
			update_post_meta( $conversation, self::STREAM, wp_slash( $stream ) );
			update_post_meta( $conversation, self::PRODUCTS, $known );
			update_post_meta( $conversation, self::ACTIVITY, time() );
			return true;
		} finally {
			$this->unlock( $conversation );
		}
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
			if ( array() === $suffix || self::users_only( $suffix ) ) {
				return self::cap( $request );
			}
			return null;
		}
		$shared = self::prefix_length( $history, $request );
		$added  = array_slice( $request, $shared );
		$unseen = array_slice( $history, $shared );
		// The snapshot branched off an earlier prefix and its only new
		// entries are the user turn it asked. Append that turn. The
		// stored turns stay, in the order they committed.
		if ( array() !== $added && array() !== $unseen && self::users_only( $added ) ) {
			return self::cap( array_merge( $history, $added ) );
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
				if ( $request[ $start + $index ]['role'] !== $span[ $index ]['role'] || $request[ $start + $index ]['content'] !== $span[ $index ]['content'] ) {
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
		while ( $index < $width && $history[ $index ]['role'] === $request[ $index ]['role'] && $history[ $index ]['content'] === $request[ $index ]['content'] ) {
			++$index;
		}
		return $index;
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
	 * if this request dies before unlock().
	 *
	 * @param int $conversation Conversation post ID.
	 */
	private function lock( int $conversation ): bool {
		global $wpdb;
		$name = 'linker_genie_turn_' . $conversation;
		// phpcs:ignore WordPress.DB.DirectDatabaseQuery.DirectQuery, WordPress.DB.DirectDatabaseQuery.NoCaching -- a MySQL named lock, not a row to cache.
		$got = $wpdb->get_var( $wpdb->prepare( 'SELECT GET_LOCK(%s, %d)', $name, self::LOCK_WAIT ) );
		return '1' === (string) $got;
	}

	/**
	 * Releases the commit lock. A connection that already dropped it
	 * answers null; there is nothing further to do.
	 *
	 * @param int $conversation Conversation post ID.
	 */
	private function unlock( int $conversation ): void {
		global $wpdb;
		$name = 'linker_genie_turn_' . $conversation;
		// phpcs:ignore WordPress.DB.DirectDatabaseQuery.DirectQuery, WordPress.DB.DirectDatabaseQuery.NoCaching -- releases the named lock lock() acquired.
		$wpdb->get_var( $wpdb->prepare( 'SELECT RELEASE_LOCK(%s)', $name ) );
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
