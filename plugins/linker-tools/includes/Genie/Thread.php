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
 * service wrote it. The stream is stored raw so the shell parses it with the
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
	 * Records one answered turn: the thread the browser sent, and the answer.
	 *
	 * @param int                        $conversation Conversation post ID.
	 * @param array<array-key, mixed>    $messages The request's messages; the shape is
	 *                                             the browser's, so entries are checked.
	 * @param string                     $stream       The service's SSE text, its `reading` events taken out (split).
	 * @param list<array<string, mixed>> $readings  What the turn read from its files (split).
	 */
	public function record( int $conversation, array $messages, string $stream, array $readings = array() ): void {
		if ( $conversation < 1 ) {
			return;
		}
		if ( array() !== $readings ) {
			$kept = array_merge( $this->readings( $conversation ), $readings );
			update_post_meta( $conversation, self::READINGS, array_slice( $kept, -self::READINGS_LIMIT ) );
		}
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
		if ( count( $kept ) > self::LIMIT ) {
			$kept = array_slice( $kept, -self::LIMIT );
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
		update_post_meta( $conversation, self::MESSAGES, wp_slash( $kept ) );
		update_post_meta( $conversation, self::STREAM, wp_slash( $stream ) );
		update_post_meta( $conversation, self::PRODUCTS, $known );
		update_post_meta( $conversation, self::ACTIVITY, time() );
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
