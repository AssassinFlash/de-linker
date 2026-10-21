<?php
/**
 * Native scheduler alternative when shared hosting exposes no CLI cron control.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry\Assessment;

/** An independent service timer drives native wp-cron; page visits are irrelevant. */
final class RecoverySchedule {
	public const HOOK     = 'linker_inquiry_assessment_recover';
	public const INTERVAL = 'linker_inquiry_assessment_minute';

	/** Register only; activation explicitly installs the recurring native event. */
	public function register(): void {
		// phpcs:ignore WordPress.WP.CronInterval.CronSchedulesInterval -- Owner-approved minute recovery (#511/#522), driven independently of page visits.
		add_filter( 'cron_schedules', array( $this, 'schedules' ) );
		add_action( self::HOOK, array( $this, 'recover' ) );
	}

	/** Native action callbacks return no recovery count. */
	public function recover(): void {
		( new Queue() )->recover();
	}

	/**
	 * The approved independent recovery interval is one minute (#511/#522).
	 *
	 * @param array<string, array{interval:int,display:string}> $schedules Native schedules.
	 * @return array<string, array{interval:int,display:string}>
	 */
	public function schedules( array $schedules ): array {
		$schedules[ self::INTERVAL ] = array(
			'interval' => MINUTE_IN_SECONDS,
			'display'  => 'Inquiry assessment recovery',
		);
		return $schedules;
	}
}
