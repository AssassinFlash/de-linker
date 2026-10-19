<?php
/**
 * One process committing a stale Genie turn.
 *
 * `php commit-turn.php <wp root> <conversation id> <ready file> <prior user> <prior answer> <question> <answer>`
 *
 * Waits until a second process has also reached the barrier, then records
 * the prior thread plus this question. ConversationConcurrencyTest starts
 * two of these at once. Prints `ok` when the commit was stored.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

// phpcs:disable WordPress.Security.ValidatedSanitizedInput, WordPress.Security.EscapeOutput, WordPress.WP.AlternativeFunctions -- a command-line fixture. The arguments are this test's own.
if ( ! isset( $argv ) ) {
	exit( 2 );
}
[ , $linker_tools_root, $linker_tools_id, $linker_tools_ready, $linker_tools_prior_user, $linker_tools_prior_answer, $linker_tools_question, $linker_tools_answer ] = $argv;
define( 'WP_USE_THEMES', false ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedConstantFound -- WordPress's own constant.
$_SERVER['HTTP_HOST']   = 'localhost';
$_SERVER['REQUEST_URI'] = '/';
require_once $linker_tools_root . '/wp-load.php';

file_put_contents( $linker_tools_ready, getmypid() . "\n", FILE_APPEND | LOCK_EX );
$linker_tools_deadline = microtime( true ) + 20;
while ( microtime( true ) < $linker_tools_deadline ) {
	$linker_tools_arrived = file( $linker_tools_ready, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES );
	if ( is_array( $linker_tools_arrived ) && count( $linker_tools_arrived ) >= 2 ) {
		break;
	}
	// 10 ms between polls. The peer is booting WordPress, not the lock.
	usleep( 10000 );
}

// 300 ms inside the commit lock: long enough for the peer to block in
// GET_LOCK (Thread::LOCK_WAIT is the 60 s turn budget), short enough that
// the waiter is not the one who gets refused.
add_action(
	Linker\Tools\Genie\Thread::LOCKED,
	static function (): void {
		usleep( 300000 );
	}
);

$linker_tools_stream = 'event: block' . "\n" . 'data: ' . (string) wp_json_encode(
	array(
		'type' => 'text',
		'text' => $linker_tools_answer,
		'refs' => array(),
	)
) . "\n\n" . 'event: done' . "\n" . 'data: {}' . "\n\n";
$linker_tools_ok     = ( new Linker\Tools\Genie\Thread() )->record(
	(int) $linker_tools_id,
	array(
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
	),
	$linker_tools_stream
);
echo $linker_tools_ok ? 'ok' : 'refused';
