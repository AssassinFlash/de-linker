<?php
/**
 * Sender identities through WooCommerce, Outbox and WordPress's real mailer.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Contact\Emails\TeamMessageEmail;
use Linker\Commerce\Health\Monitor;
use Linker\Commerce\Mail\EmailPolicy;
use Linker\Commerce\Mail\Outbox;
use Linker\Commerce\Mail\TeamEmail;
use Linker\Commerce\Mail\TestMode;
use Linker\Commerce\Mail\Throttle;
use Linker\Commerce\Settings\Options;
use PHPMailer\PHPMailer\PHPMailer;
use WC_Email;

/**
 * Local isolation replaces postSend with a file writer. No transport can send
 * real mail; phpmailer_init and MIME preparation still execute normally.
 *
 * @coversNothing
 */
final class EnvelopeSenderTest extends IntegrationTestCase {

	/**
	 * Every active Woo email and plain wp_mail keeps From through a queued retry.
	 *
	 * @testWith ["", "sales@sunriverinverter.com", "en_US"]
	 *           ["bounce@example.test", "bounce@example.test", "en_US"]
	 *           ["", "sales@sunriverinverter.com", "de_DE_formal"]
	 *           ["bounce@example.test", "bounce@example.test", "de_DE_formal"]
	 *
	 * @param string $saved    Saved envelope option.
	 * @param string $expected Expected PHPMailer Sender.
	 * @param string $locale   Render language.
	 */
	public function test_all_mail_types_keep_from_and_use_the_envelope_on_delivery( string $saved, string $expected, string $locale ): void {
		$this->assertDirectoryExists( (string) constant( 'LINKER_LOCAL_MAIL_DIR' ), 'Only the file-isolated local instance may run this test.' );
		$options = array(
			Options::ENVELOPE_SENDER         => $saved,
			Options::NOTIFY_FROM             => 'sales@sunriverinverter.com',
			TestMode::OPTION                 => 'tester@example.test',
			'woocommerce_email_from_name'    => 'Linker',
			'woocommerce_email_from_address' => 'sales@de-linker.com',
			Monitor::GENIE_URL_OPTION        => 'http://127.0.0.1:9',
			Monitor::ENGINE_URL_OPTION       => 'http://127.0.0.1:9',
		);
		$before  = array();
		foreach ( $options as $key => $value ) {
			$before[ $key ] = get_option( $key );
			update_option( $key, $value );
		}
		$this->later(
			static function () use ( $before ): void {
				foreach ( $before as $key => $value ) {
					false === $value ? delete_option( $key ) : update_option( $key, $value );
				}
			}
		);
		switch_to_locale( $locale );
		$this->later(
			static function (): void {
				restore_previous_locale();
			}
		);

		$delivered = array();
		$observe   = static function () use ( &$delivered ): void {
			$mailer = $GLOBALS['phpmailer'];
			if ( $mailer instanceof PHPMailer ) {
				$delivered[] = array( $mailer->From, $mailer->FromName, $mailer->Sender, $mailer->getToAddresses(), $mailer->getSentMIMEMessage() ); // phpcs:ignore WordPress.NamingConventions.ValidVariableName.UsedPropertyNotSnakeCase -- PHPMailer's public fields.
			}
		};
		add_action( 'wp_mail_succeeded', $observe );
		$this->later(
			static function () use ( $observe ): void {
				remove_action( 'wp_mail_succeeded', $observe );
			}
		);
		$mail_files = self::mail_files();
		$this->later(
			static function () use ( $mail_files ): void {
				foreach ( array_diff( self::mail_files(), $mail_files ) as $file ) {
					unlink( $file );
				}
			}
		);

		$types = array_filter(
			WC()->mailer()->get_emails(),
			static fn ( WC_Email $email ): bool => str_starts_with( get_class( $email ), 'Linker\\Commerce\\' ) || in_array( $email->id, EmailPolicy::KEEP, true )
		);
		$this->assertCount( 14, $types, 'Twelve Linker emails and the two enabled Woo emails are covered.' );
		$types['wp_mail'] = null;
		$types['health']  = null;
		foreach ( $types as $key => $email ) {
			$id       = $email instanceof WC_Email ? $email->id : $key;
			$internal = 'health' === $id || $email instanceof TeamEmail || $email instanceof TeamMessageEmail;
			$from     = $internal ? 'sales@sunriverinverter.com' : 'sales@de-linker.com';
			$subject  = 'Envelope fixture ' . $id . ' ' . self::tag();
			$marker   = self::newest_mail_job();
			update_option( Options::ENVELOPE_SENDER, 'queued@example.test' );
			update_option( Throttle::OPTION, array_fill( 0, Throttle::PER_MINUTE, time() ), false );
			if ( $email instanceof WC_Email ) {
				$email->send( 'customer@example.test', $subject, 'File-only envelope fixture.', $email->get_headers(), array() );
			} elseif ( 'health' === $id ) {
				( new Monitor( WP_PLUGIN_DIR . '/linker-commerce/linker-commerce.php', new Options() ) )->run();
			} else {
				wp_mail( 'customer@example.test', $subject, 'Plain WordPress notification.', array( 'From: Linker <sales@de-linker.com>', 'Reply-To: replies@example.test' ) );
			}
			$jobs = self::mail_jobs_after( $marker );
			// A successful retry removes its queue post, so the base fixture
			// cannot discover the original scheduled action at teardown.
			$this->later(
				static function () use ( $jobs ): void {
					foreach ( $jobs as $job_id ) {
						as_unschedule_all_actions( Outbox::HOOK, array( $job_id ), Outbox::GROUP );
						self::assertFalse( as_has_scheduled_action( Outbox::HOOK, array( $job_id ), Outbox::GROUP ), 'No pending retry survives the fixture.' );
					}
				}
			);
			$this->assertCount( 'health' === $id ? 2 : 1, $jobs, $id . ': every call queued.' );
			foreach ( $jobs as $job_id ) {
				$data = json_decode( (string) get_post_meta( $job_id, '_linker_mail_message', true ), true );
				$this->assertContains( 'From: Linker <' . $from . '>', $data['headers'], $id . ': queued From is unchanged.' );
				$this->assertSame( array( 'health' === $id ? ( new Options() )->notify_to() : 'customer@example.test' ), $data['to'], 'Queue retains original recipients.' );
				// Read the setting at delivery, even for a previously queued message.
				update_option( Options::ENVELOPE_SENDER, $saved );
				delete_option( Throttle::OPTION );
				$count = count( $delivered );
				/** This action is documented in includes/Mail/Outbox.php. */
				do_action( Outbox::HOOK, $job_id ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- the Outbox's registered retry hook.
				$this->assertCount( $count + 1, $delivered, $id . ': one successful file delivery.' );
				[ $actual_from, $name, $sender, $to, $mime ] = $delivered[ $count ];
				$this->assertSame( $from, $actual_from, $id . ': delivered From.' );
				$this->assertSame( 'Linker', $name, $id . ': delivered name.' );
				$this->assertSame( $expected, $sender, $id . ': envelope Sender.' );
				$this->assertSame( 'tester@example.test', $to[0][0] );
				$this->assertStringContainsString( 'From: Linker <' . $from . '>', $mime );
				if ( 'wp_mail' === $id ) {
					$this->assertStringContainsString( 'Reply-To: replies@example.test', $mime );
				}
			}
			$this->assertSame( array(), self::mail_jobs_after( $marker ), 'Successful retry removes its queued message.' );
		}
		delete_option( Throttle::OPTION );
		$count = count( $delivered );
		wp_mail( 'customer@example.test', 'Immediate WordPress mail', 'File-only.', array( 'From: Core <core@example.test>' ) );
		$this->assertCount( $count + 1, $delivered );
		$this->assertSame( 'core@example.test', $delivered[ $count ][0], 'Immediate wp_mail retains its own From.' );
		$this->assertSame( $expected, $delivered[ $count ][2], 'Immediate wp_mail uses the envelope setting.' );
	}

	/**
	 * Captures written by the local transport, so cleanup removes this run's files.
	 *
	 * @return list<string>
	 */
	private static function mail_files(): array {
		$files = glob( (string) constant( 'LINKER_LOCAL_MAIL_DIR' ) . '/*.eml' );
		return false === $files ? array() : $files;
	}
}
