<?php
/**
 * The daily health check on the real instance, through the mail queue.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Health\Monitor;
use Linker\Commerce\Mail\Throttle;
use Linker\Commerce\Settings\Options;

/**
 * With the daily cron event's hook fired (as WP-Cron fires it), a service
 * that does not answer produces exactly one team message out of the Outbox —
 * to the contact person, with the blind copies — and a healthy pair of
 * services produces none (issue #67, GAP-16).
 *
 * @coversNothing
 */
final class HealthMonitorTest extends IntegrationTestCase {

	/**
	 * The instance's captured mail.
	 *
	 * @return list<string> Absolute paths of the .eml files.
	 */
	private static function captured_mail(): array {
		$directory = (string) constant( 'LINKER_LOCAL_MAIL_DIR' );
		$files     = glob( $directory . '/*.eml' );
		return false === $files ? array() : $files;
	}

	/**
	 * The one captured message addressed to the given contact.
	 *
	 * @param string[] $before  Files captured before the check ran.
	 * @param string   $contact The contact address to look for.
	 */
	private static function new_mail_to( array $before, string $contact ): ?string {
		foreach ( array_diff( self::captured_mail(), $before ) as $file ) {
			$content = (string) file_get_contents( $file ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_file_get_contents -- a local file outside WP_Filesystem's scope.
			if ( str_contains( $content, "To: {$contact}" ) ) {
				return $content;
			}
		}
		return null;
	}

	/**
	 * A service that answers nothing sends the team one message through the
	 * Outbox; the healthy services send none.
	 */
	public function test_a_failed_check_reaches_the_team_and_a_healthy_one_sends_nothing(): void {
		$tag     = self::tag();
		$contact = "linker-it-{$tag}@example.test";
		$bcc     = "linker-it-bcc-{$tag}@example.test";
		$saved   = array(
			Options::CONTACT_EMAIL     => get_option( Options::CONTACT_EMAIL, '' ),
			Options::TEAM_BCC          => get_option( Options::TEAM_BCC, '' ),
			Monitor::GENIE_URL_OPTION  => get_option( Monitor::GENIE_URL_OPTION, '' ),
			Monitor::ENGINE_URL_OPTION => get_option( Monitor::ENGINE_URL_OPTION, '' ),
		);
		$this->later(
			static function () use ( $saved ): void {
				foreach ( $saved as $name => $value ) {
					update_option( $name, $value );
				}
			}
		);

		// The team addresses of this test, and a Genie that answers nothing:
		// a port on this machine with no listener refuses at once.
		update_option( Options::CONTACT_EMAIL, $contact );
		update_option( Options::TEAM_BCC, $bcc );
		update_option( Monitor::GENIE_URL_OPTION, 'http://127.0.0.1:9' );
		delete_option( Throttle::OPTION );

		$captured = self::captured_mail();
		/** This hook is the monitor's own daily event (Monitor::HOOK), delivered by WP-Cron.
		 *
		 * @since 0.2.0
		 */
		do_action( Monitor::HOOK ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- the monitor's own hook constant.

		$alert = self::new_mail_to( $captured, $contact );
		$this->assertNotNull( $alert, 'The failed check sends one message to the contact person.' );
		$this->assertStringContainsString( 'Subject: The Genie service failed its health check', $alert );
		$this->assertStringContainsString( "Bcc: {$bcc}", $alert, 'The blind copies of the settings ride along.' );
		$this->assertStringContainsString( 'Address: http://127.0.0.1:9', $alert );
		$this->assertStringContainsString( 'Genie uses this service.', $alert );
		$this->assertStringNotContainsString( 'The engine service failed its health check', $alert, 'The healthy engine sends nothing.' );

		// The healthy pair: with the instance's own service addresses, the
		// same run sends nothing.
		update_option( Monitor::GENIE_URL_OPTION, $saved[ Monitor::GENIE_URL_OPTION ] );
		update_option( Monitor::ENGINE_URL_OPTION, $saved[ Monitor::ENGINE_URL_OPTION ] );
		delete_option( Throttle::OPTION );

		$captured = self::captured_mail();
		/** This hook is the monitor's own daily event (Monitor::HOOK), delivered by WP-Cron.
		 *
		 * @since 0.2.0
		 */
		do_action( Monitor::HOOK ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- the monitor's own hook constant.

		$this->assertNull( self::new_mail_to( $captured, $contact ), 'A healthy pair of services sends nothing.' );
		$this->assertNotFalse( wp_next_scheduled( Monitor::HOOK ), 'The daily event is on the schedule.' );
	}
}
