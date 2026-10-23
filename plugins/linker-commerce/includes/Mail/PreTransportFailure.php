<?php
/** A failed preparation has not reached quota reservation or transport.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
namespace Linker\Commerce\Mail;

/** Only Outbox's initial checks and native attempt preparation create this witness. */
final class PreTransportFailure extends \RuntimeException {
	/**
	 * Preserve the typed cause across Action Scheduler's native exception wrapper.
	 *
	 * @param \Throwable $previous Original failure before quota reservation or transport.
	 */
	public function __construct( \Throwable $previous ) {
		parent::__construct( 'mail_pre_transport_unavailable', 0, $previous );
	}
}
