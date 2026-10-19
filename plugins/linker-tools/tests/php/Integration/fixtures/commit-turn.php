<?php
/**
 * One process committing a stale Genie turn.
 *
 * `php commit-turn.php <wp root> <conversation id> <ready file> <prior user> <prior answer> <question> <answer> [trace] [hold microseconds] [lock wait] [mode]`
 *
 * Waits until a second process has also reached the barrier, then records
 * the prior thread plus this question. `mode` is `once` (commit and print
 * `ok`) or `retry` (try-lock, which the peer is holding, then commit a
 * duplicated tail and print `refused-then-ok`). ConversationConcurrencyTest
 * starts two of these at once.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

// phpcs:disable WordPress.Security.ValidatedSanitizedInput, WordPress.Security.EscapeOutput, WordPress.WP.AlternativeFunctions -- a command-line fixture. The arguments are this test's own.
if ( ! isset( $argv ) ) {
	exit( 2 );
}
[ , $linker_tools_root, $linker_tools_id, $linker_tools_ready, $linker_tools_prior_user, $linker_tools_prior_answer, $linker_tools_question, $linker_tools_answer ] = $argv;
$linker_tools_trace     = isset( $argv[8] ) ? (string) $argv[8] : '';
$linker_tools_hold      = isset( $argv[9] ) ? (int) $argv[9] : 300000;
$linker_tools_lock_wait = isset( $argv[10] ) && '' !== $argv[10] ? (int) $argv[10] : null;
$linker_tools_mode      = isset( $argv[11] ) ? (string) $argv[11] : 'once';
define( 'WP_USE_THEMES', false ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedConstantFound -- WordPress's own constant.
$_SERVER['HTTP_HOST']   = 'localhost';
$_SERVER['REQUEST_URI'] = '/';
require_once $linker_tools_root . '/wp-load.php';

/**
 * Appends one timing line. The overlap test reads these to prove the two
 * commits actually overlapped inside the lock.
 *
 * @param string $event arrived, locked or leaving.
 */
$linker_tools_mark = static function ( string $event ) use ( $linker_tools_trace ): void {
	if ( '' === $linker_tools_trace || '-' === $linker_tools_trace ) {
		return;
	}
	$linker_tools_pid = getmypid();
	file_put_contents(
		$linker_tools_trace,
		(string) wp_json_encode(
			array(
				'event' => $event,
				'pid'   => is_int( $linker_tools_pid ) ? $linker_tools_pid : 0,
				'at'    => microtime( true ),
			)
		) . "\n",
		FILE_APPEND | LOCK_EX
	);
};

file_put_contents( $linker_tools_ready, getmypid() . "\n", FILE_APPEND | LOCK_EX );

/**
 * Pid lines in the ready file. `holding` is written later, from inside the lock.
 */
$linker_tools_pids = static function () use ( $linker_tools_ready ): int {
	$linker_tools_lines = file( $linker_tools_ready, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES );
	if ( ! is_array( $linker_tools_lines ) ) {
		return 0;
	}
	$linker_tools_count = 0;
	foreach ( $linker_tools_lines as $linker_tools_line ) {
		if ( 1 === preg_match( '/^\d+$/', $linker_tools_line ) ) {
			++$linker_tools_count;
		}
	}
	return $linker_tools_count;
};

// 20 s is the ceiling for this process to see the peer's pid line. Each
// process loads WordPress via wp-load.php before writing its pid. 20 s is
// longer than one local bootstrap plus the 10 ms poll gap, and shorter
// than Proxy::TURN_BUDGET (60 s) so a stuck peer fails the test instead
// of looking like a lock wait. The peer is booting WordPress, not waiting
// on the lock.
$linker_tools_barrier_seconds = 20;
$linker_tools_deadline        = microtime( true ) + $linker_tools_barrier_seconds;
$linker_tools_open            = false;
while ( microtime( true ) < $linker_tools_deadline ) {
	if ( $linker_tools_pids() >= 2 ) {
		$linker_tools_open = true;
		break;
	}
	// 10 ms between polls. The peer is booting WordPress, not the lock.
	usleep( 10000 );
}
if ( ! $linker_tools_open ) {
	fwrite( STDERR, "barrier timed out\n" );
	exit( 1 );
}

// 300 ms inside the commit lock, unless the caller passes another hold:
// long enough for the peer to block in GET_LOCK (the HTTP path waits only
// the remainder of Proxy::TURN_BUDGET, 60 s), short enough that the waiter
// is not the one who gets refused. The refusal test passes 1 s: the peer
// is already booted and only has to see the holding line.
$linker_tools_thread = new class( $linker_tools_ready, $linker_tools_hold, $linker_tools_mark ) extends Linker\Tools\Genie\Thread {
	/**
	 * Keeps the pause, the ready file and the trace writer.
	 *
	 * @param string   $ready Ready file. `holding` is written once the lock is held.
	 * @param int      $hold  Microseconds to stay inside the lock. 0 does not pause.
	 * @param \Closure $mark  Writes one timing line.
	 */
	public function __construct(
		private string $ready,
		private int $hold,
		private \Closure $mark
	) {
	}

	/**
	 * Pauses inside the lock so the other process blocks in GET_LOCK.
	 *
	 * @param int $conversation Conversation post ID.
	 */
	protected function while_locked( int $conversation ): void {
		unset( $conversation );
		( $this->mark )( 'locked' );
		file_put_contents( $this->ready, "holding\n", FILE_APPEND | LOCK_EX );
		if ( $this->hold > 0 ) {
			// usleep past 1_000_000 is capped on some platforms. Split it.
			$seconds = intdiv( $this->hold, 1000000 );
			$rest    = $this->hold % 1000000;
			if ( $seconds > 0 ) {
				sleep( $seconds );
			}
			if ( $rest > 0 ) {
				usleep( $rest );
			}
		}
		( $this->mark )( 'leaving' );
	}
};

$linker_tools_stream = 'event: block' . "\n" . 'data: ' . (string) wp_json_encode(
	array(
		'type' => 'text',
		'text' => $linker_tools_answer,
		'refs' => array(),
	)
) . "\n\n" . 'event: done' . "\n" . 'data: {}' . "\n\n";
$linker_tools_once   = array(
	array(
		'role'    => 'user',
		'content' => $linker_tools_prior_user,
	),
	array(
		'role'    => 'assistant',
		'content' => $linker_tools_prior_answer,
	),
	array(
		'role'    => 'user',
		'content' => $linker_tools_question,
	),
);

if ( 'retry' === $linker_tools_mode ) {
	$linker_tools_held     = false;
	$linker_tools_deadline = microtime( true ) + $linker_tools_barrier_seconds;
	while ( microtime( true ) < $linker_tools_deadline ) {
		$linker_tools_lines = file( $linker_tools_ready, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES );
		if ( is_array( $linker_tools_lines ) && in_array( 'holding', $linker_tools_lines, true ) ) {
			$linker_tools_held = true;
			break;
		}
		usleep( 10000 );
	}
	if ( ! $linker_tools_held ) {
		fwrite( STDERR, "holding line timed out\n" );
		exit( 1 );
	}
	$linker_tools_mark( 'arrived' );
	// Wait 0: the peer is inside the lock. This must refuse.
	if ( $linker_tools_thread->record( (int) $linker_tools_id, $linker_tools_once, $linker_tools_stream, array(), 0 ) ) {
		echo 'acquired';
		exit( 1 );
	}
	$linker_tools_duplicated   = $linker_tools_once;
	$linker_tools_duplicated[] = array(
		'role'    => 'user',
		'content' => $linker_tools_question,
	);
	$linker_tools_ok           = $linker_tools_thread->record( (int) $linker_tools_id, $linker_tools_duplicated, $linker_tools_stream );
	echo $linker_tools_ok ? 'refused-then-ok' : 'refused-then-refused';
	exit( $linker_tools_ok ? 0 : 1 );
}

$linker_tools_mark( 'arrived' );
$linker_tools_ok = $linker_tools_thread->record(
	(int) $linker_tools_id,
	$linker_tools_once,
	$linker_tools_stream,
	array(),
	$linker_tools_lock_wait
);
echo $linker_tools_ok ? 'ok' : 'refused';
