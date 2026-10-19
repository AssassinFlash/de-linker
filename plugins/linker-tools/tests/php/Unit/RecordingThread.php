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
	 * @var array{conversation: int, messages: list<array<string, mixed>>, stream: string, readings: list<array<string, mixed>>}|null
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
	 * The readings `readings()` answers with.
	 *
	 * @var list<array<string, mixed>>
	 */
	public array $kept_readings = array();

	/**
	 * When false, `record()` refuses and writes nothing. The proxy then
	 * answers 409 instead of pretending the turn was stored (#373).
	 *
	 * @var bool
	 */
	public bool $accept = true;

	/**
	 * Answers with what the test installed.
	 *
	 * @param int $conversation Conversation post ID.
	 * @return list<array<string, mixed>>
	 */
	public function readings( int $conversation ): array {
		unset( $conversation );
		return $this->kept_readings;
	}

	/**
	 * Keeps the turn instead of writing post meta.
	 *
	 * @param int                        $conversation Conversation post ID.
	 * @param array<array-key, mixed>    $messages     The request's messages.
	 * @param string                     $stream       The service's SSE text, split.
	 * @param list<array<string, mixed>> $readings  The turn's readings, split.
	 * @return bool False when the test set `accept` to refuse the commit.
	 */
	public function record( int $conversation, array $messages, string $stream, array $readings = array() ): bool {
		if ( ! $this->accept ) {
			return false;
		}
		$this->recorded = array(
			'conversation' => $conversation,
			'messages'     => array_values( $messages ),
			'stream'       => $stream,
			'readings'     => $readings,
		);
		return true;
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
