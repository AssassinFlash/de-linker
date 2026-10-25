<?php
/** Recoverable mail budget cutover commands.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
namespace Linker\Commerce\Cli;

use Linker\Commerce\Mail\BudgetRollback;
use WP_CLI;

/** No command clears a ledger, releases an inquiry or sends an email. */
final class MailBudgetCommand {
	/** Pause sends before a complete rollback; jobs and customer submissions survive. */
	public function pause(): void {
		if ( ! ( new BudgetRollback() )->pause() ) {
			WP_CLI::error( 'Mail sending could not be paused.' );
		}
		WP_CLI::success( 'Mail sending paused; customer submissions and queued jobs remain available.' );
	}
	/** Atomically append new attempts to the old ledger; repeat safely after interruption. */
	public function rollback(): void {
		$this->transfer( false );
	}
	/** Reconcile old-code ledger additions after restoring new code, then resume. */
	public function resume(): void {
		$this->transfer( true );
	}
	/**
	 * Print a secret-free operational receipt.
	 *
	 * @param bool $resume Whether to reconcile and resume.
	 */
	private function transfer( bool $resume ): void {
		$result = ( new BudgetRollback() )->transfer( $resume );
		if ( is_wp_error( $result ) ) {
			WP_CLI::error( $result->get_error_message() );
		}
		WP_CLI::log( (string) wp_json_encode( $result ) );
	}
}
