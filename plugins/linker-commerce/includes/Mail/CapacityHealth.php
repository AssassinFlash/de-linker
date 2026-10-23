<?php
/**
 * One fixed-size failure record; a capacity failure never sends an alert email.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Mail;

/** Post-write native producers without a rebuild source remain explicit failures. */
final class CapacityHealth {
	public const OPTION = 'linker_mail_capacity_health';

	/** Store only the latest fixed diagnostic, with no addresses or message content. */
	public static function failed(): void {
		update_option(
			self::OPTION,
			array(
				'at'     => time(),
				'reason' => 'notification_not_accepted',
			),
			false
		);
	}
}
