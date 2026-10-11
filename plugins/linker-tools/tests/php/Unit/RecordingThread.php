<?php
/**
 * A Thread that keeps the conversation in memory instead of in post meta.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Genie\Thread;

/**
 * Records what a turn stored, for tests that only need the seam.
 */
final class RecordingThread extends Thread {

	/**
	 * The last recorded turn.
	 *
	 * @var array{conversation: int, messages: list<array<string, mixed>>, stream: string}|null
	 */
	public ?array $recorded = null;

	/**
	 * The thread `read()` answers with.
	 *
	 * @var array{messages: list<array<string, mixed>>, stream: string}
	 */
	public array $stored = array(
		'messages' => array(),
		'stream'   => '',
	);

	/**
	 * Keeps the turn instead of writing post meta.
	 *
	 * @param int                     $conversation Conversation post ID.
	 * @param array<array-key, mixed> $messages     The request's messages.
	 * @param string                  $stream       The service's SSE text.
	 */
	public function record( int $conversation, array $messages, string $stream ): void {
		$this->recorded = array(
			'conversation' => $conversation,
			'messages'     => array_values( $messages ),
			'stream'       => $stream,
		);
	}

	/**
	 * Answers with what the test installed.
	 *
	 * @param int $conversation Conversation post ID.
	 * @return array{messages: list<array<string, mixed>>, stream: string}
	 */
	public function read( int $conversation ): array {
		unset( $conversation );
		return $this->stored;
	}
}
