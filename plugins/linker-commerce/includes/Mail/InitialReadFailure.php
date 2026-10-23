<?php
/** A failed consumer has not reached quota reservation or transport.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
namespace Linker\Commerce\Mail;

/** Only Outbox's initial authoritative reads create this server-side witness. */
final class InitialReadFailure extends \RuntimeException {
	/**
	 * Preserve the typed cause across Action Scheduler's native exception wrapper.
	 *
	 * @param \Throwable $previous Original initial-read failure.
	 */
	public function __construct( \Throwable $previous ) {
		parent::__construct( 'mail_initial_read_unavailable', 0, $previous );
	}
}
