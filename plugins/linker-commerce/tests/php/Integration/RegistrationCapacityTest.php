<?php
/**
 * Public registration limits at the native pre-create boundary.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Protection\Allowance;
use Linker\Commerce\Protection\Identity;
use Linker\Commerce\Protection\Ledger;
use Linker\Commerce\Protection\Operation;
use Linker\Commerce\Protection\Proof;
use Linker\Commerce\Protection\RegistrationSlots;
use Linker\Commerce\Registration\Approval;
use Linker\Commerce\Registration\CustomerRole;
use Linker\Commerce\Registration\Emails\NewCustomerEmail;
use Linker\Commerce\Registration\Emails\RegistrationReceivedEmail;
use Linker\Commerce\Registration\VatProfile;
use Linker\Commerce\Registration\Website;
use Linker\Commerce\Mail\Message;
use WP_Error;

/**
 * Verified public registration uses shared site windows.
 *
 * @coversNothing
 */
final class RegistrationCapacityTest extends IntegrationTestCase {

	/** Keep all test-owned protection state in this isolated instance. */
	protected function setUp(): void {
		parent::setUp();
		$this->as_user( 0 );
		$old = get_option( Ledger::OPTION );
		delete_option( Ledger::OPTION );
		$cookie = $_COOKIE; // phpcs:ignore WordPress.Security.NonceVerification -- Exact fixture restoration.
		$slots  = get_option( RegistrationSlots::OPTION );
		delete_option( RegistrationSlots::OPTION );
		$this->later(
			static function () use ( $slots ): void {
				delete_option( RegistrationSlots::OPTION );
				if ( false !== $slots ) {
					update_option( RegistrationSlots::OPTION, $slots, false );
				}
			}
		);
		$env = array();
		foreach ( array(
			'LINKER_PUBLIC_PROTECTION_MODE' => 'enforce',
			'LINKER_TURNSTILE_SITE_KEY'     => '1x00000000000000000000AA',
			'LINKER_TURNSTILE_SECRET_KEY'   => '1x0000000000000000000000000000000AA',
			'LINKER_TURNSTILE_HOSTNAME'     => 'localhost',
		) as $key => $value ) {
			$env[ $key ] = getenv( $key );
			putenv( $key . '=' . $value ); // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.runtime_configuration_putenv -- Test process only; restored below.
		}
		$this->later(
			static function () use ( $env, $old, $cookie ): void {
				foreach ( $env as $key => $value ) {
					putenv( false === $value ? $key : $key . '=' . $value ); // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.runtime_configuration_putenv -- Restore this process.
				}
				delete_option( Ledger::OPTION );
				if ( false !== $old ) {
					update_option( Ledger::OPTION, $old, false );
				}
				$_COOKIE = $cookie;
			}
		);
	}

	/**
	 * A native verified request from a different browser and connection.
	 *
	 * @param int $number Synthetic subject number.
	 * @return array<string,string>
	 */
	private function request( int $number ): array {
		$_COOKIE[ Identity::COOKIE ] = md5( 'registration-capacity-' . $number );
		$_SERVER['REMOTE_ADDR']      = '192.0.2.' . $number;
		$identity                    = Identity::current();
		$this->assertInstanceOf( Identity::class, $identity );
		$ledger = new Ledger();
		$id     = wp_generate_uuid4();
		$fp     = hash( 'sha256', $id );
		$this->assertIsArray( $ledger->reserve( $id, $fp, array( new Allowance( 'fixture_verify', $identity->browser, 1, HOUR_IN_SECONDS ) ), 10, array(), 'verification_registration', $identity->binding() ) );
		$this->assertIsArray( $ledger->dispatch( $id, $fp ) );
		$this->assertIsArray( $ledger->complete( $id, $fp, 1 ) );
		return array(
			'linker_request_id' => wp_generate_uuid4(),
			'linker_proof'      => ( new Proof() )->issue( 'verified', 'registration', $identity, $id ),
		);
	}

	/** Changing all cheap identities must retain the site's registration window. */
	public function test_registration_has_one_shared_site_hour_and_day(): void {
		$post   = $this->request( 1 );
		$permit = Operation::begin(
			'registration',
			$post,
			array(
				'email'    => 'first@example.test',
				'username' => 'first',
			)
		);
		$this->assertIsArray( $permit );
		$summary = ( new Ledger() )->summary();
		$this->assertIsArray( $summary );
		$this->assertArrayHasKey( 'registration_site_hour', $summary['windows'], 'Subject/connection limits do not cap public account creation across cheap identities.' );
		$this->assertArrayHasKey( 'registration_site_day', $summary['windows'] );
		$this->assertSame( 15, $summary['windows']['registration_site_hour']['minimum_remaining'] );
		$this->assertSame( 31, $summary['windows']['registration_site_day']['minimum_remaining'] );
		for ( $i = 2; $i <= 16; ++$i ) {
			$this->assertIsArray(
				Operation::begin(
					'registration',
					$this->request( $i ),
					array(
						'email'    => 'customer-' . $i . '@example.test',
						'username' => 'customer-' . $i,
					)
				)
			);
		}
		$result = Operation::begin(
			'registration',
			$this->request( 17 ),
			array(
				'email'    => 'last@example.test',
				'username' => 'last',
			)
		);
		$this->assertInstanceOf( WP_Error::class, $result );
		$this->assertSame( 'linker_admission_quota', $result->get_error_code() );
		$this->assertFalse( email_exists( 'last@example.test' ) );
	}

	/** Existing unresolved accounts and interrupted native creation share capacity. */
	public function test_pending_native_accounts_and_interrupted_creation_never_expire(): void {
		$initial = RegistrationSlots::summary();
		$this->assertIsArray( $initial );
		$remaining = RegistrationSlots::MAX_PENDING - $initial['pending_users'];
		$this->assertGreaterThan( 1, $remaining );
		for ( $i = 0; $i < $remaining; ++$i ) {
			$this->assertIsArray( RegistrationSlots::reserve( wp_generate_uuid4(), 2048 ) );
		}
		$full = RegistrationSlots::reserve( wp_generate_uuid4(), 2048 );
		$this->assertInstanceOf( WP_Error::class, $full );
		$this->assertSame( 'linker_registration_capacity', $full->get_error_code() );
		$state = get_option( RegistrationSlots::OPTION );
		$this->assertIsArray( $state );
		foreach ( $state as &$entry ) {
			$entry['at'] = time() - YEAR_IN_SECONDS;
		}
		unset( $entry );
		update_option( RegistrationSlots::OPTION, $state, false );
		$this->assertInstanceOf( WP_Error::class, RegistrationSlots::reserve( wp_generate_uuid4(), 2048 ) );
		$this->assertSame( $remaining, RegistrationSlots::summary()['interrupted'] );
	}

	/** A real pending native user replaces its exact placeholder without a refund. */
	public function test_only_matching_native_user_can_replace_its_placeholder(): void {
		$before = RegistrationSlots::summary();
		$slot   = RegistrationSlots::reserve( wp_generate_uuid4(), 2048 );
		$this->assertIsArray( $slot );
		$user = $this->customer();
		update_user_meta( $user->get_id(), Approval::STATUS_META, Approval::PENDING );
		$this->assertInstanceOf( WP_Error::class, RegistrationSlots::bind( $slot['key'], $user->get_id() ) );
		update_user_meta( $user->get_id(), RegistrationSlots::META, $slot['key'] );
		$this->assertSame( array( 'user' => $user->get_id() ), RegistrationSlots::bind( $slot['key'], $user->get_id() ) );
		$bound = RegistrationSlots::summary();
		$this->assertSame( $before['pending_users'] + 1, $bound['pending_users'] );
		$this->assertSame( 0, $bound['interrupted'] );
		update_user_meta( $user->get_id(), Approval::STATUS_META, Approval::RESTRICTED );
		$this->assertSame( $bound['pending_users'], RegistrationSlots::summary()['pending_users'] );
		update_user_meta( $user->get_id(), Approval::STATUS_META, Approval::APPROVED );
		$this->assertSame( $before['pending_users'], RegistrationSlots::summary()['pending_users'] );
	}

	/** The independent byte envelope fills before the count envelope. */
	public function test_pending_business_bytes_and_unknown_reservations_are_not_refunded(): void {
		$before = RegistrationSlots::summary();
		$this->assertIsArray( $before );
		$room = RegistrationSlots::MAX_BYTES - $before['business_bytes'];
		$this->assertGreaterThan( 0, $room );
		$this->assertIsArray( RegistrationSlots::reserve( wp_generate_uuid4(), $room ) );
		$this->assertInstanceOf( WP_Error::class, RegistrationSlots::reserve( wp_generate_uuid4(), 1 ) );
		$full = RegistrationSlots::summary();
		$this->assertSame( 1, $full['interrupted'] );
		$this->assertSame( $room, $full['reserved_bytes'] );
		$this->assertSame( RegistrationSlots::MAX_BYTES, $full['business_bytes'] + $full['reserved_bytes'] );
	}

	/** Prospective native templates read full business values without side effects. */
	public function test_native_registration_preview_has_no_user_vies_or_mail_side_effect(): void {
		$emails   = WC()->mailer()->get_emails();
		$team     = $emails[ NewCustomerEmail::class ];
		$received = $emails[ RegistrationReceivedEmail::class ];
		$this->assertInstanceOf( NewCustomerEmail::class, $team );
		$this->assertInstanceOf( RegistrationReceivedEmail::class, $received );
		$values     = array(
			'billing_company'    => str_repeat( 'Company & ', 400 ),
			'billing_first_name' => 'Maria',
			'billing_last_name'  => 'Beispiel',
			'billing_country'    => 'DE',
			CustomerRole::META   => 'installer',
			VatProfile::VAT_META => '',
			Website::META        => 'example.test',
		);
		$user       = new \WP_User(
			(object) array(
				'ID'              => 0,
				'user_login'      => 'prospective-registration',
				'user_email'      => 'prospective-registration@example.test',
				'display_name'    => 'Maria Beispiel',
				'user_registered' => gmdate( 'Y-m-d H:i:s' ),
			)
		);
		$http_calls = 0;
		$block      = static function () use ( &$http_calls ): WP_Error {
			++$http_calls;
			return new WP_Error( 'fixture_network_denied' );
		};
		add_filter( 'pre_http_request', $block, 1 );
		$this->later(
			static function () use ( $block ): void {
				remove_filter( 'pre_http_request', $block, 1 );
			}
		);
		$before_users = count_users()['total_users'];
		$before_jobs  = self::mail_jobs_after( 0 );
		$preview      = $team->preview( $user, $values );
		$this->assertInstanceOf( Message::class, $preview );
		$this->assertStringContainsString( esc_html( $values['billing_company'] ), $preview->body );
		$this->assertStringContainsString( $values['billing_company'], $preview->subject );
		$this->assertInstanceOf( Message::class, $received->preview( $user, 'de_DE_formal' ) );
		$this->assertSame( $before_users, count_users()['total_users'] );
		$this->assertSame( $before_jobs, self::mail_jobs_after( 0 ) );
		$this->assertFalse( email_exists( $user->user_email ) );
		$this->assertSame( 0, $http_calls );
	}
}
