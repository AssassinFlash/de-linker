<?php
/**
 * Two turns committed against one conversation.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Integration;

use Linker\Tools\Genie\Conversations;
use Linker\Tools\Genie\Thread;
use PHPUnit\Framework\TestCase;

// phpcs:disable WordPress.WP.AlternativeFunctions, WordPress.PHP.DiscouragedPHPFunctions.system_calls_proc_open -- the parallel test starts PHP processes.

/**
 * A stale second snapshot must not replace the first turn (#373). The
 * sequential case fixes the order. The parallel case holds the commit
 * lock across a pause so both writers really do overlap.
 *
 * @coversNothing
 */
final class ConversationConcurrencyTest extends TestCase {

	/**
	 * The prior user message both snapshots share.
	 */
	private const PRIOR_USER = 'Which inverter?';

	/**
	 * The prior answer both snapshots share.
	 */
	private const PRIOR_ANSWER = 'The hybrid inverter is three-phase.';

	/**
	 * Conversations this test created.
	 *
	 * @var list<int>
	 */
	private array $posts = array();

	/**
	 * Skips unless the integration configuration ran the bootstrap.
	 */
	public static function setUpBeforeClass(): void {
		if ( '1' !== getenv( 'LINKER_INTEGRATION' ) ) {
			self::markTestSkipped( 'Run phpunit.integration.xml.dist against a local instance (just up); the unit suite does not load WordPress.' );
		}
	}

	/**
	 * Removes the conversations this test opened.
	 */
	protected function tearDown(): void {
		foreach ( $this->posts as $id ) {
			wp_delete_post( $id, true );
		}
		parent::tearDown();
	}

	/**
	 * Writer B's snapshot is the history from before writer A committed.
	 * Both questions and both answers stay, in commit order.
	 */
	public function test_a_stale_snapshot_appends_instead_of_replacing(): void {
		$id = $this->seed();

		$this->commit( $id, 'EV chargers', 'EV chargers in the range are these.' );
		$this->commit( $id, 'Wallboxen', 'Wallboxen in der Auswahl sind diese.' );

		$this->assertSame(
			array(
				self::PRIOR_USER,
				self::PRIOR_ANSWER,
				'EV chargers',
				'EV chargers in the range are these.',
				'Wallboxen',
				'Wallboxen in der Auswahl sind diese.',
			),
			array_column( ( new Thread() )->transcript( $id ), 'content' )
		);
	}

	/**
	 * Two processes commit overlapping stale snapshots. Neither turn is
	 * missing afterwards. The order is whichever commit acquired the lock
	 * first; both orders keep the turns whole.
	 */
	public function test_overlapping_commits_keep_both_turns(): void {
		$id    = $this->seed();
		$root  = (string) getenv( 'LINKER_WP_ROOT' );
		$ready = tempnam( sys_get_temp_dir(), 'genie-373-' );
		$this->assertIsString( $ready );
		file_put_contents( $ready, '' );
		$writers = array(
			array( 'EV chargers', 'EV chargers in the range are these.' ),
			array( 'Wallboxen', 'Wallboxen in der Auswahl sind diese.' ),
		);
		$running = array();
		$pipes   = array();
		foreach ( $writers as $index => $writer ) {
			$process = proc_open(
				array( PHP_BINARY, __DIR__ . '/fixtures/commit-turn.php', $root, (string) $id, $ready, self::PRIOR_USER, self::PRIOR_ANSWER, $writer[0], $writer[1] ),
				array(
					1 => array( 'pipe', 'w' ),
					2 => array( 'pipe', 'w' ),
				),
				$pipes[ $index ]
			);
			$this->assertIsResource( $process );
			$running[ $index ] = $process;
		}
		foreach ( $running as $index => $process ) {
			$out = (string) stream_get_contents( $pipes[ $index ][1] );
			$err = (string) stream_get_contents( $pipes[ $index ][2] );
			fclose( $pipes[ $index ][1] );
			fclose( $pipes[ $index ][2] );
			$this->assertSame( 0, proc_close( $process ), $err );
			$this->assertSame( 'ok', trim( $out ), $err );
		}
		unlink( $ready );

		$contents = array_column( ( new Thread() )->transcript( $id ), 'content' );
		$first    = array( self::PRIOR_USER, self::PRIOR_ANSWER, 'EV chargers', 'EV chargers in the range are these.', 'Wallboxen', 'Wallboxen in der Auswahl sind diese.' );
		$second   = array( self::PRIOR_USER, self::PRIOR_ANSWER, 'Wallboxen', 'Wallboxen in der Auswahl sind diese.', 'EV chargers', 'EV chargers in the range are these.' );
		$this->assertContains( $contents, array( $first, $second ) );
	}

	/**
	 * A conversation whose one stored turn is the shared prior exchange.
	 */
	private function seed(): int {
		$id = wp_insert_post(
			array(
				'post_type'   => Conversations::POST_TYPE,
				'post_status' => 'private',
				'post_title'  => 'linker-it-373',
				'post_author' => 0,
			),
			true
		);
		$this->assertIsInt( $id );
		$this->posts[] = $id;
		$stream        = 'event: block' . "\n" . 'data: ' . (string) wp_json_encode(
			array(
				'type' => 'text',
				'text' => self::PRIOR_ANSWER,
				'refs' => array(),
			)
		) . "\n\n" . 'event: done' . "\n" . 'data: {}' . "\n\n";
		$this->assertTrue(
			( new Thread() )->record(
				$id,
				array(
					array(
						'role'    => 'user',
						'content' => self::PRIOR_USER,
					),
				),
				$stream
			)
		);
		return $id;
	}

	/**
	 * Commits one stale snapshot: the prior exchange plus a new question.
	 *
	 * @param int    $id       Conversation post ID.
	 * @param string $question The new user turn.
	 * @param string $answer   That turn's answer text.
	 */
	private function commit( int $id, string $question, string $answer ): void {
		$stream = 'event: block' . "\n" . 'data: ' . (string) wp_json_encode(
			array(
				'type' => 'text',
				'text' => $answer,
				'refs' => array(),
			)
		) . "\n\n" . 'event: done' . "\n" . 'data: {}' . "\n\n";
		$this->assertTrue(
			( new Thread() )->record(
				$id,
				array(
					array(
						'role'    => 'user',
						'content' => self::PRIOR_USER,
					),
					array(
						'role'    => 'assistant',
						'content' => self::PRIOR_ANSWER,
					),
					array(
						'role'    => 'user',
						'content' => $question,
					),
				),
				$stream
			)
		);
	}
}
