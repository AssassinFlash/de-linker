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
	 * @param int                     $conversation Conversation post ID.
	 * @param array<array-key, mixed> $messages The request's messages; the shape is
	 *                                          the browser's, so entries are checked.
	 * @param string                  $stream       The service's SSE text.
	 */
	public function record( int $conversation, array $messages, string $stream ): void {
		if ( $conversation < 1 ) {
			return;
		}
		$kept = array();
		foreach ( $messages as $message ) {
			if ( ! is_array( $message ) ) {
				continue;
			}
			$role    = isset( $message['role'] ) && 'assistant' === $message['role'] ? 'assistant' : 'user';
			$content = isset( $message['content'] ) ? (string) $message['content'] : '';
			if ( '' === $content ) {
				continue;
			}
			$kept[] = array(
				'role'    => $role,
				'content' => $content,
			);
		}
		if ( count( $kept ) > self::LIMIT ) {
			$kept = array_slice( $kept, -self::LIMIT );
		}
		update_post_meta( $conversation, self::MESSAGES, $kept );
		update_post_meta( $conversation, self::STREAM, $stream );
	}
}
