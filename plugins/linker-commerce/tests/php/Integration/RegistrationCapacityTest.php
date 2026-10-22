<?php
/**
 * Public registration limits at the native pre-create boundary.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

// phpcs:disable WordPress.DB.RestrictedFunctions, WordPress.Security.NonceVerification, WordPress.Security.ValidatedSanitizedInput, WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound, WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound, WooCommerce.Commenting.CommentHooks, WordPress.PHP.DiscouragedPHPFunctions, WordPress.WP.AlternativeFunctions -- Test-only native request/process harness uses real pipes and temporary process witnesses; real validation hooks remain under test.

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Protection\Allowance;
use Linker\Commerce\Protection\Identity;
use Linker\Commerce\Protection\IntakeStore;
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
use Linker\Commerce\Mail\Capacity;
use Linker\Commerce\Registration\RegistrationMessage;
use Linker\Commerce\Registration\RegistrationNotices;
use Linker\Commerce\Registration\RegistrationPrivacy;
use WP_Error;

/**
 * Verified public registration uses shared site windows.
 *
 * @coversNothing
 */
final class RegistrationCapacityTest extends IntegrationTestCase {

	/**
	 * Baseline includes the preserved historical held jobs.
	 *
	 * @var int
	 */
	private int $mail_marker = 0;

	/**
	 * Keep all test-owned protection state in this isolated instance.
	 */
	protected function setUp(): void {
		parent::setUp();
		$this->mail_marker = self::newest_mail_job();
		$this->as_user( 0 );
		$intake = get_option( IntakeStore::OPTION );
		delete_option( IntakeStore::OPTION );
		$this->later(
			static function () use ( $intake ): void {
				delete_option( IntakeStore::OPTION );
				if ( false !== $intake ) {
					update_option( IntakeStore::OPTION, $intake, false );
				}
			}
		);
		$post_before = $_POST;
		$this->later(
			static function () use ( $post_before ): void {
				$_POST = $post_before;
			}
		);
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
	 * Require a confirmed native capacity read.
	 *
	 * @return array<string,mixed> Confirmed native capacity, never a failed read treated as zero.
	 */
	private function summary(): array {
		$value = RegistrationSlots::summary();
		$this->assertIsArray( $value );
		return $value;
	}

	/**
	 * Require this account's durable native notice state.
	 *
	 * @param  int $id Native account.
	 * @return array<string,mixed> Confirmed source state.
	 */
	private function notices( int $id ): array {
		$value = RegistrationNotices::read( $id );
		$this->assertIsArray( $value );
		return $value;
	}

	/**
	 * Require an actual native user.
	 *
	 * @param  int $id Native user.
	 * @return \WP_User Confirmed native user.
	 */
	private function native_user( int $id ): \WP_User {
		$value = get_userdata( $id );
		$this->assertInstanceOf( \WP_User::class, $value );
		return $value;
	}

	/**
	 * A native verified request from a different browser and connection.
	 *
	 * @param int    $number Synthetic subject number.
	 * @param string $action Native protected door.
	 * @return array<string,string>
	 */
	private function request( int $number, string $action = 'registration' ): array {
		$_COOKIE[ Identity::COOKIE ] = md5( 'registration-capacity-' . $number );
		$_SERVER['REMOTE_ADDR']      = '192.0.2.' . $number;
		$identity                    = Identity::current();
		$this->assertInstanceOf( Identity::class, $identity );
		$ledger = new Ledger();
		$id     = wp_generate_uuid4();
		$fp     = hash( 'sha256', $id );
		$this->assertIsArray( $ledger->reserve( $id, $fp, array( new Allowance( 'fixture_verify_' . $action, $identity->browser, 1, HOUR_IN_SECONDS ) ), 10, array(), 'verification_' . $action, $identity->binding() ) );
		$this->assertIsArray( $ledger->dispatch( $id, $fp ) );
		$this->assertIsArray( $ledger->complete( $id, $fp, 1 ) );
		return array(
			'linker_request_id' => wp_generate_uuid4(),
			'linker_proof'      => ( new Proof() )->issue( 'verified', $action, $identity, $id ),
		);
	}

	/**
	 * Actual public Woo validation must refuse before user/VIES/mail side effects.
	 */
	public function test_public_woo_gate_refuses_full_pending_capacity_before_creation(): void {
		wc_load_cart();
		$previous_cart = WC()->cart;
		WC()->cart     = new \WC_Cart();
		$this->later(
			static function () use ( $previous_cart ): void {
				WC()->cart = $previous_cart;
			}
		);
		$product = $this->product( '125' );
		$this->assertNotFalse( WC()->cart->add_to_cart( $product->get_id(), 2 ) );
		$draft   = WC()->cart->get_cart_hash();
		$initial = $this->summary();
		for ( $i = $initial['pending_users']; $i < RegistrationSlots::MAX_PENDING; ++$i ) {
			$this->assertIsArray( RegistrationSlots::reserve( wp_generate_uuid4(), 2048 ) );
		}
		$post   = $this->public_post( 31 );
		$before = count_users()['total_users'];
		$jobs   = self::mail_jobs_after( 0 );
		$errors = apply_filters( 'woocommerce_process_registration_errors', new WP_Error(), 'capacity-full', $post['password'], $post['email'] );
		$this->assertContains( 'linker_registration_capacity', $errors->get_error_codes() );
		$this->assertSame( $post, $_POST, 'Keep all native inputs; never persist the password for recovery.' );
		$this->assertSame( $before, count_users()['total_users'] );
		$this->assertSame( $jobs, self::mail_jobs_after( 0 ) );
		$this->assertSame( $draft, WC()->cart->get_cart_hash(), 'A registration refusal must retain the real solution draft.' );
		$stamp   = (string) ( time() - 5 );
		$inquiry = $this->request( 31, 'inquiry' ) + array(
			'name'                 => 'Maria Example',
			'email'                => self::TESTER,
			'company'              => 'Synthetic pending-capacity fixture',
			'message'              => 'Synthetic inquiry remains available while registration is full.',
			'consent'              => '1',
			'linker_inquiry_nonce' => wp_create_nonce( 'linker_inquiry' ),
			'linker_started'       => $stamp,
			'linker_started_nonce' => wp_create_nonce( 'linker_inquiry_started_' . $stamp ),
			'linker_draft_hash'    => $draft,
		);
		$order   = ( new \Linker\Commerce\Inquiry\Handler() )->process( $inquiry );
		$this->assertInstanceOf( \WC_Order::class, $order );
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		$this->assertSame( 0, $order->get_customer_id() );
		$this->assertSame( 2, $order->get_item_count() );
	}

	/**
	 * A real native create must bind its slot before VAT and persist both notice states.
	 */
	public function test_public_native_creation_has_owned_slot_and_durable_notice_states(): void {
		$post   = $this->public_post( 32 );
		$errors = apply_filters( 'woocommerce_process_registration_errors', new WP_Error(), '', $post['password'], $post['email'] );
		$this->assertFalse( $errors->has_errors(), implode( ' ', $errors->get_error_messages() ) );
		$id = wc_create_new_customer( $post['email'], '', $post['password'] );
		$this->assertIsInt( $id );
		$this->later(
			static function () use ( $id ): void {
				include_once ABSPATH . 'wp-admin/includes/user.php';
				wp_delete_user( $id );
			}
		);
		$this->assertNotSame( '', get_user_meta( $id, RegistrationSlots::META, true ), 'The earliest native created hook must not finish only the operation.' );
		$notice = get_user_meta( $id, '_linker_registration_notices', true );
		$this->assertIsArray( $notice );
		$this->assertArrayHasKey( 'team', $notice );
		$this->assertArrayHasKey( 'received', $notice );
	}

	/**
	 * Critical notice exhaustion is a pre-create refusal too, not a saved account.
	 */
	public function test_public_gate_refuses_full_critical_notification_capacity(): void {
				$store = new \Linker\Commerce\Mail\JobStore();
		$used          = 0;
		foreach ( self::mail_jobs_after( 0 ) as $job ) {
			$native = $store->load( $job );
			$this->assertNotNull( $native );
			if ( $native['message']->critical || $store->critical( $job ) ) {
				++$used; }
		}
		$this->assertIsArray( Capacity::reserve_critical( 'fixture-full-critical', Capacity::LIMITS['critical']['count'] - $used, 1 ) );
		$post   = $this->public_post( 33 );
		$before = count_users()['total_users'];
		$errors = apply_filters( 'woocommerce_process_registration_errors', new WP_Error(), '', $post['password'], $post['email'] );
		$this->assertContains( 'linker_registration_capacity', $errors->get_error_codes() );
		$this->assertSame( $before, count_users()['total_users'] );
		$this->assertSame( 0, $this->summary()['interrupted'] );
		$this->assertSame( $post, $_POST );
	}

	/**
	 * Unknown notification handoff keeps its real user and recovers exactly once.
	 */
	public function test_native_job_and_notice_acknowledgement_roll_back_together_then_recover(): void {
		$post = $this->public_post( 34 );
		$this->assertFalse( apply_filters( 'woocommerce_process_registration_errors', new WP_Error(), '', $post['password'], $post['email'] )->has_errors() );
		$fail = static fn ( $old, $id, $key ) => RegistrationNotices::META === $key ? false : $old;
		add_filter( 'update_user_metadata', $fail, 10, 3 );
		try {
			$id = wc_create_new_customer( $post['email'], '', $post['password'] );
		} finally {
				remove_filter( 'update_user_metadata', $fail, 10 );
		}
		$this->assertIsInt( $id );
		$this->own_user( $id );
		$pending = $this->notices( $id );
		$this->assertSame( 'pending', $pending['team']['state'] );
		$this->assertSame( 'pending', $pending['received']['state'] );
		$this->assertArrayHasKey( 'parts', $pending['team'] );
		$this->assertCount( 0, self::mail_jobs_after( $this->mail_marker ) );
		RegistrationNotices::recover();
		$accepted = $this->notices( $id );
		$this->assertSame( 'accepted', $accepted['team']['state'] );
		$this->assertSame( 'accepted', $accepted['received']['state'] );
		$this->assertArrayNotHasKey( 'parts', $accepted['team'] );
		$this->assertArrayNotHasKey( 'message', $accepted['received'] );
		$this->assertCount( 2, self::mail_jobs_after( $this->mail_marker ) );
		RegistrationNotices::recover();
		do_action( 'linker_commerce_customer_registered', $id );
		$this->assertSame( $accepted, $this->notices( $id ) );
		$this->assertCount( 2, self::mail_jobs_after( $this->mail_marker ) );
	}

	/**
	 * Native configured template/filters freeze once; every legal future field fits.
	 */
	public function test_complete_native_message_bound_includes_all_vat_id_and_locale_shapes(): void {
		$emails = WC()->mailer()->get_emails();
		$user   = new \WP_User(
			(object) array(
				'ID'              => 0,
				'user_email'      => self::TESTER,
				'display_name'    => 'Maria',
				'user_registered' => gmdate( 'Y-m-d H:i:s' ),
			)
		);
		foreach ( array( 'en_US', 'de_DE_formal' ) as $locale ) {
			foreach ( array( $emails[ NewCustomerEmail::class ], $emails[ RegistrationReceivedEmail::class ] ) as $email ) {
				$this->assertTrue( $email instanceof NewCustomerEmail || $email instanceof RegistrationReceivedEmail );
				$plan = RegistrationMessage::prepare( $email, $user, array( 'billing_company' => str_repeat( 'Full & \" ü ', 2000 ) ), $locale );
				$this->assertIsArray( $plan );
				foreach ( array( 1, 999999999, PHP_INT_MAX ) as $id ) {
					foreach ( array( '', VatProfile::NONE, VatProfile::VALID, VatProfile::INVALID, VatProfile::UNVERIFIED ) as $vat ) {
						$message = RegistrationMessage::complete( $plan, $id, $vat );
						$this->assertInstanceOf( Message::class, $message );
						$this->assertLessThanOrEqual( $plan['max_bytes'], strlen( (string) wp_json_encode( $message->to_array() ) ) );
						$this->assertStringNotContainsString( 'registration.invalid', $message->body );
						if ( $email instanceof NewCustomerEmail ) {
							$this->assertStringContainsString( 'focus=' . $id, $message->body );
						}
					}
				}
				$this->assertSame( '', $plan['message']['body'], 'Exactly one bounded body copy, held in structural parts.' );
			}
		}
	}

	/**
	 * An override losing the actual anchor cannot masquerade as a proven bound.
	 */
	public function test_template_override_without_controlled_link_is_refused_before_creation(): void {
		$rewrite = static fn ( string $body ): string => str_replace( 'https://registration.invalid/', 'https://override.invalid/', $body );
		add_filter( 'woocommerce_mail_content', $rewrite );
		try {
			$post   = $this->public_post( 35 );
			$errors = apply_filters( 'woocommerce_process_registration_errors', new WP_Error(), '', $post['password'], $post['email'] );
			$this->assertContains( 'linker_registration_capacity', $errors->get_error_codes() );
			$this->assertFalse( email_exists( $post['email'] ) );
			$this->assertSame( 0, $this->summary()['interrupted'] );
		} finally {
			remove_filter( 'woocommerce_mail_content', $rewrite );
		}
	}

	/**
	 * No unrelated nested native account may consume the current verified permit.
	 */
	public function test_unrelated_native_created_hook_keeps_the_expected_registration_pending(): void {
		$post = $this->public_post( 36 );
		$this->assertFalse( apply_filters( 'woocommerce_process_registration_errors', new WP_Error(), '', $post['password'], $post['email'] )->has_errors() );
		$other = wp_insert_user(
			array(
				'user_login' => 'unrelated-' . self::tag(),
				'user_email' => 'unrelated-' . self::tag() . '@example.test',
				'user_pass'  => 'Separate-native-fixture!',
				'role'       => 'subscriber',
			)
		);
		$this->assertIsInt( $other );
		$this->own_user( $other );
		$this->assertSame( '', get_user_meta( $other, RegistrationSlots::META, true ) );
		$id = wc_create_new_customer( $post['email'], '', $post['password'] );
		$this->assertIsInt( $id );
		$this->own_user( $id );
		$this->assertNotSame( '', get_user_meta( $id, RegistrationSlots::META, true ) );
	}

	/**
	 * The optional native core door shares pending capacity, not default-role approval.
	 */
	public function test_core_public_registration_is_owned_and_does_not_use_default_approval(): void {
		$post                                      = $this->public_post( 37 );
		$_POST['linker_native_registration_nonce'] = wp_create_nonce( 'linker_native_registration' );
		$id                                        = register_new_user( 'core-' . self::tag(), $post['email'] );
		$this->assertIsInt( $id );
		$this->own_user( $id );
		$this->assertSame( 'core', get_user_meta( $id, '_linker_public_registration_entry', true ) );
		$this->assertSame( Approval::PENDING, ( new Approval() )->status( $id ) );
		$this->assertNotSame( '', get_user_meta( $id, RegistrationSlots::META, true ) );
		$this->assertSame( 'accepted', $this->notices( $id )['team']['state'] );
		$this->assertCount( 2, self::mail_jobs_after( $this->mail_marker ), 'Only the two bounded project notices; no extra native core mail.' );
	}

	/**
	 * The verified-email framework exports and erases the copied native notification.
	 */
	public function test_pending_and_accepted_notice_privacy_uses_native_verified_email_callbacks(): void {
		$post = $this->public_post( 38 );
		$this->assertFalse( apply_filters( 'woocommerce_process_registration_errors', new WP_Error(), '', $post['password'], $post['email'] )->has_errors() );
		$id = wc_create_new_customer( $post['email'], '', $post['password'] );
		$this->assertIsInt( $id );
		$this->own_user( $id );
		$privacy = new RegistrationPrivacy();
		$export  = $privacy->export( $post['email'] );
		$this->assertIsArray( $export );
		$this->assertNotEmpty( $export['data'] );
		$this->assertStringNotContainsString( $post['password'], (string) wp_json_encode( $privacy->export( $post['email'] ) ) );
		$this->assertCount( 2, self::mail_jobs_after( $this->mail_marker ) );
		$this->assertTrue( $privacy->erase( $post['email'] )['items_removed'] );
		$this->assertCount( 0, self::mail_jobs_after( $this->mail_marker ) );
		$this->assertSame( array( 'state' => 'erased' ), $this->notices( $id )['team'] );
		RegistrationNotices::recover();
		$this->assertCount( 0, self::mail_jobs_after( $this->mail_marker ) );
	}

	/**
	 * Disabled optional notice is durably skipped and cancels only its unused count-one scope.
	 */
	public function test_disabled_receipt_cancels_only_its_own_unused_reservation(): void {
		$emails           = WC()->mailer()->get_emails();
		$receipt          = $emails[ RegistrationReceivedEmail::class ];
		$enabled          = $receipt->enabled;
		$receipt->enabled = 'no';
		try {
			$post = $this->public_post( 43 );
			$this->assertFalse( apply_filters( 'woocommerce_process_registration_errors', new WP_Error(), '', $post['password'], $post['email'] )->has_errors() );
			$id = wc_create_new_customer( $post['email'], '', $post['password'] );
			$this->assertIsInt( $id );
			$this->own_user( $id );
			$state = $this->notices( $id );
			$this->assertSame( 'accepted', $state['team']['state'] );
			$this->assertSame(
				array(
					'state'  => 'skipped',
					'reason' => 'disabled',
				),
				$state['received']
			);
			$this->assertCount( 1, self::mail_jobs_after( $this->mail_marker ) );
			RegistrationNotices::recover();
			$this->assertSame( $state, $this->notices( $id ) );
		} finally {
			$receipt->enabled = $enabled;
		}
	}

	/**
	 * Native receipt budget policy skip is explicit and never blocks team mail.
	 */
	public function test_optional_receipt_quota_skip_is_durable_without_leaking_a_slot(): void {
		for ( $i = 0; $i < 10; ++$i ) {
			$this->assertSame( '', \Linker\Commerce\Protection\ReceiptBudget::reason( 'policy-' . $i . '@example.test', 'fixture-' . $i, 'registration' ) );
		}
		$post = $this->public_post( 44 );
		$this->assertFalse( apply_filters( 'woocommerce_process_registration_errors', new WP_Error(), '', $post['password'], $post['email'] )->has_errors() );
		$id = wc_create_new_customer( $post['email'], '', $post['password'] );
		$this->assertIsInt( $id );
		$this->own_user( $id );
		$this->assertSame(
			array(
				'state'  => 'skipped',
				'reason' => 'daily_cap',
			),
			$this->notices( $id )['received']
		);
		$this->assertSame( 'accepted', $this->notices( $id )['team']['state'] );
		$state = get_option( IntakeStore::OPTION );
		$this->assertSame( 0, array_sum( array_column( $state['mail_capacity']['reservations'], 'remaining' ) ) );
		RegistrationNotices::recover();
		$this->assertCount( 1, self::mail_jobs_after( $this->mail_marker ) );
	}

	/**
	 * Same verified UUID after a lost ACK cannot create a second native account or mail.
	 */
	public function test_completed_public_registration_replay_does_not_repeat_side_effects(): void {
		$post = $this->public_post( 45 );
		$this->assertFalse( apply_filters( 'woocommerce_process_registration_errors', new WP_Error(), '', $post['password'], $post['email'] )->has_errors() );
		$id = wc_create_new_customer( $post['email'], '', $post['password'] );
		$this->assertIsInt( $id );
		$this->own_user( $id );
		$before = count_users()['total_users'];
		$state  = $this->notices( $id );
		$errors = apply_filters( 'woocommerce_process_registration_errors', new WP_Error(), '', $post['password'], $post['email'] );
		$this->assertContains( 'linker_admission_already_completed', $errors->get_error_codes() );
		$this->assertSame( $before, count_users()['total_users'] );
		$this->assertSame( $state, $this->notices( $id ) );
		$this->assertCount( 2, self::mail_jobs_after( $this->mail_marker ) );
	}

	/**
	 * Staff action, not time, role defaults or email delivery, releases an orphan.
	 */
	public function test_staff_explicit_interrupted_disposition_is_audited_and_nonpublic(): void {
		$audit = get_option( 'linker_registration_dispositions' );
		$this->later(
			static function () use ( $audit ): void {
				delete_option( 'linker_registration_dispositions' );
				if ( false !== $audit ) {
					update_option( 'linker_registration_dispositions', $audit, false );
				}
			}
		);
		$slot = RegistrationSlots::reserve( wp_generate_uuid4(), 2048 );
		$this->assertIsArray( $slot );
		$this->assertFalse( RegistrationSlots::resolve_interrupted( $slot['key'], 'No native account exists.' ) );
		$staff = get_users(
			array(
				'role'   => 'administrator',
				'fields' => 'ID',
				'number' => 1,
			)
		);
		$this->as_user( (int) $staff[0] );
		$this->assertFalse( RegistrationSlots::resolve_interrupted( $slot['key'], '' ) );
		$this->assertTrue( RegistrationSlots::resolve_interrupted( $slot['key'], 'Native account lookup completed; interrupted pre-create placeholder.' ) );
		$this->assertSame( 0, $this->summary()['interrupted'] );
		$this->assertSame( $slot['key'], array_slice( get_option( 'linker_registration_dispositions' ), -1 )[0]['key'] );
		$this->assertSame( (int) $staff[0], array_slice( get_option( 'linker_registration_dispositions' ), -1 )[0]['by'] );
	}

	/**
	 * Native display-name schema cannot fail after creating an otherwise valid account.
	 */
	public function test_native_name_size_guard_preserves_full_input_before_creation(): void {
		$post                        = $this->public_post( 46 );
		$_POST['billing_first_name'] = str_repeat( 'ü', 251 );
		$expected                    = $_POST;
		$errors                      = apply_filters( 'woocommerce_process_registration_errors', new WP_Error(), '', $post['password'], $post['email'] );
		$this->assertContains( 'billing_first_name', $errors->get_error_codes() );
		$this->assertSame( $expected, $_POST );
		$this->assertFalse( email_exists( $post['email'] ) );
	}

	/**
	 * Actual pending Woo profile growth is blocked; equal/shrinking values still save in debt.
	 */
	public function test_pending_native_billing_growth_shares_bytes_without_blocking_shrink(): void {
		$customer = $this->customer();
		update_user_meta( $customer->get_id(), Approval::STATUS_META, Approval::PENDING );
		$this->as_user( $customer->get_id() );
		$before = $this->summary();
		$this->assertIsArray( RegistrationSlots::reserve( wp_generate_uuid4(), RegistrationSlots::MAX_BYTES - $before['business_bytes'] ) );
		$original = $customer->get_billing_company();
		$customer->set_billing_company( $original . ' extra growth' );
		$refused = false;
		try {
			$customer->save();
		} catch ( \WC_Data_Exception $error ) {
			$refused = true;
		}
		$this->assertTrue( $refused, 'The existing authenticated billing writer must not bypass the byte envelope.' );
		$this->assertSame( $original, get_user_meta( $customer->get_id(), 'billing_company', true ) );
		$customer = new \WC_Customer( $customer->get_id() );
		$customer->set_billing_company( substr( $original, 0, -1 ) . 'X' );
		$customer->save();
		$this->assertSame( substr( $original, 0, -1 ) . 'X', get_user_meta( $customer->get_id(), 'billing_company', true ) );
		$customer->set_billing_company( 'Small company' );
		$customer->save();
		$this->assertSame( 'Small company', get_user_meta( $customer->get_id(), 'billing_company', true ) );
		$this->assertLessThan( $before['business_bytes'], $this->summary()['business_bytes'] );
	}

	/**
	 * Native core users/me edit gets its normal WP_Error, not a successful partial write.
	 */
	public function test_pending_native_rest_profile_cannot_bypass_shared_business_bytes(): void {
		$customer = $this->customer();
		update_user_meta( $customer->get_id(), Approval::STATUS_META, Approval::PENDING );
		$this->as_user( $customer->get_id() );
		$before = $this->summary();
		$this->assertIsArray( RegistrationSlots::reserve( wp_generate_uuid4(), RegistrationSlots::MAX_BYTES - $before['business_bytes'] ) );
		$name    = $this->native_user( $customer->get_id() )->display_name;
		$request = new \WP_REST_Request( 'POST', '/wp/v2/users/me' );
		$request->set_param( 'name', $name . ' extra growth' );
		$response = rest_do_request( $request );
		$this->assertSame( 503, $response->get_status() );
		$this->assertSame( 'linker_registration_profile_capacity', $response->get_data()['code'] );
		$this->assertSame( $name, $this->native_user( $customer->get_id() )->display_name );
	}

	/**
	 * The actual core error hook rolls back preceding native profile extension metadata.
	 */
	public function test_pending_core_profile_error_restores_earlier_billing_writes(): void {
		$customer = $this->customer();
		update_user_meta( $customer->get_id(), Approval::STATUS_META, Approval::PENDING );
		$this->as_user( $customer->get_id() );
		$before = $this->summary();
		$this->assertIsArray( RegistrationSlots::reserve( wp_generate_uuid4(), RegistrationSlots::MAX_BYTES - $before['business_bytes'] ) );
		$original = $customer->get_billing_company();
		do_action( 'personal_options_update', $customer->get_id() );
		update_user_meta( $customer->get_id(), 'billing_company', $original . ' growth' );
		$errors = new WP_Error();
		$user   = (object) array(
			'ID'           => $customer->get_id(),
			'display_name' => $this->native_user( $customer->get_id() )->display_name,
		);
		do_action_ref_array( 'user_profile_update_errors', array( &$errors, true, &$user ) );
		$this->assertContains( 'linker_registration_profile_capacity', $errors->get_error_codes() );
		$this->assertSame( $original, get_user_meta( $customer->get_id(), 'billing_company', true ) );
	}

	/**
	 * A busy capacity mutex must also roll back core extension fields written before validation.
	 */
	public function test_busy_core_profile_does_not_save_earlier_extension_fields(): void {
		$customer = $this->customer();
		update_user_meta( $customer->get_id(), Approval::STATUS_META, Approval::PENDING );
		$this->as_user( $customer->get_id() );
		global $wpdb;
		$other = new \wpdb( (string) constant( 'DB_USER' ), (string) constant( 'DB_PASSWORD' ), (string) constant( 'DB_NAME' ), (string) constant( 'DB_HOST' ) );
		$lock  = 'linker-assessment-' . md5( (string) constant( 'DB_NAME' ) . '/' . $wpdb->prefix . '/registration-capacity' );
		$this->assertSame( '1', $other->get_var( $other->prepare( 'SELECT GET_LOCK(%s, 0)', $lock ) ) );
		try {
			$original = $customer->get_billing_company();
			do_action( 'personal_options_update', $customer->get_id() );
			update_user_meta( $customer->get_id(), 'billing_company', $original . ' must roll back' );
			$errors = new WP_Error();
			$user   = (object) array(
				'ID'           => $customer->get_id(),
				'display_name' => $this->native_user( $customer->get_id() )->display_name,
			);
			do_action_ref_array( 'user_profile_update_errors', array( &$errors, true, &$user ) );
			$this->assertContains( 'linker_registration_profile_capacity', $errors->get_error_codes() );
			$this->assertSame( $original, get_user_meta( $customer->get_id(), 'billing_company', true ) );
		} finally {
			$other->get_var( $other->prepare( 'SELECT RELEASE_LOCK(%s)', $lock ) );
			$other->close();
		}
	}

	/**
	 * Even the same database connection cannot dispose a creator that still owns its permit.
	 */
	public function test_staff_cannot_resolve_a_live_creator_on_the_same_connection(): void {
		$slot = RegistrationSlots::reserve( wp_generate_uuid4(), 2048 );
		$this->assertIsArray( $slot );
		$this->assertTrue( RegistrationSlots::hold( $slot['key'] ) );
		$staff = get_users(
			array(
				'role'   => 'administrator',
				'fields' => 'ID',
				'number' => 1,
			)
		);
		$this->as_user( (int) $staff[0] );
		try {
			$this->assertFalse( RegistrationSlots::resolve_interrupted( $slot['key'], 'A still-running creator is not an orphan.' ) );
		} finally {
				RegistrationSlots::release( $slot['key'] );
		}
		$this->assertSame( 1, $this->summary()['interrupted'] );
	}

	/**
	 * A frozen notification still belongs to the original verified address after a native account email edit.
	 */
	public function test_original_recipient_privacy_after_account_address_changes(): void {
		$post = $this->public_post( 47 );
		$this->assertFalse( apply_filters( 'woocommerce_process_registration_errors', new WP_Error(), '', $post['password'], $post['email'] )->has_errors() );
		$id = wc_create_new_customer( $post['email'], '', $post['password'] );
		$this->assertIsInt( $id );
		$this->own_user( $id );
		wp_update_user(
			array(
				'ID'         => $id,
				'user_email' => 'changed-' . self::tag() . '@example.test',
			)
		);
		$privacy = new RegistrationPrivacy();
		$export  = $privacy->export( $post['email'] );
		$this->assertIsArray( $export );
		$this->assertNotEmpty( $export['data'] );
		$this->assertTrue( $privacy->erase( $post['email'] )['done'] );
		$this->assertCount( 0, self::mail_jobs_after( $this->mail_marker ) );
		RegistrationNotices::recover();
		$this->assertCount( 0, self::mail_jobs_after( $this->mail_marker ) );
		$this->assertSame( '', get_user_meta( $id, RegistrationNotices::OWNER, true ) );
	}

	/**
	 * Explicit staff decisions/maintenance keep their native edit path even when legacy debt fills the public pool.
	 */
	public function test_approved_and_staff_maintenance_do_not_use_pending_growth_capacity(): void {
		$customer = $this->customer();
		$staff    = get_users(
			array(
				'role'   => 'administrator',
				'fields' => 'ID',
				'number' => 1,
			)
		);
		$before   = $this->summary();
		$this->assertIsArray( RegistrationSlots::reserve( wp_generate_uuid4(), RegistrationSlots::MAX_BYTES - $before['business_bytes'] ) );
		update_user_meta( $customer->get_id(), Approval::STATUS_META, Approval::APPROVED );
		update_user_meta( $customer->get_id(), Approval::CHANGED_BY_META, (int) $staff[0] );
		update_user_meta( $customer->get_id(), Approval::CHANGED_AT_META, time() );
		$this->as_user( $customer->get_id() );
		$customer->set_billing_company( str_repeat( 'Approved business ', 50 ) );
		$customer->save();
		$this->assertSame( str_repeat( 'Approved business ', 50 ), get_user_meta( $customer->get_id(), 'billing_company', true ) );
		update_user_meta( $customer->get_id(), Approval::STATUS_META, Approval::PENDING );
		$this->as_user( (int) $staff[0] );
		$customer->set_billing_company( str_repeat( 'Staff verified business ', 50 ) );
		$customer->save();
		$this->assertSame( str_repeat( 'Staff verified business ', 50 ), get_user_meta( $customer->get_id(), 'billing_company', true ) );
	}

	/**
	 * Off/observe do not enforce the registration business envelope or pending profile growth.
	 */
	public function test_observe_and_off_preserve_native_business_writers(): void {
		foreach ( array( 'off', 'observe' ) as $mode ) {
			putenv( 'LINKER_PUBLIC_PROTECTION_MODE=' . $mode );
			$customer = $this->customer();
			$this->as_user( $customer->get_id() );
			update_user_meta( $customer->get_id(), Approval::STATUS_META, Approval::PENDING );
			$before = $this->summary();
			update_option(
				RegistrationSlots::OPTION,
				array(
					str_repeat( 'f', 64 ) => array(
						'at'    => time(),
						'bytes' => RegistrationSlots::MAX_BYTES,
					),
				),
				false
			);
			$customer->set_billing_company( str_repeat( $mode, 100 ) );
			$customer->save();
			$this->assertSame( str_repeat( $mode, 100 ), get_user_meta( $customer->get_id(), 'billing_company', true ) );
			$this->as_user( 0 );
			$post = $this->public_post( 'off' === $mode ? 48 : 49 );
			$this->assertFalse( apply_filters( 'woocommerce_process_registration_errors', new WP_Error(), '', $post['password'], $post['email'] )->has_errors() );
			$id = wc_create_new_customer( $post['email'], '', $post['password'] );
			$this->assertIsInt( $id );
			$this->own_user( $id );
			$this->assertSame( '', get_user_meta( $id, RegistrationSlots::META, true ) );
			delete_option( RegistrationSlots::OPTION );
		}
	}

	/**
	 * A failed registry CAS must not leave a staff audit claiming that capacity was released.
	 */
	public function test_staff_disposition_audit_rolls_back_if_capacity_write_fails(): void {
		$audit = get_option( 'linker_registration_dispositions' );
		$this->later(
			static function () use ( $audit ): void {
				delete_option( 'linker_registration_dispositions' );
				if ( false !== $audit ) {
					update_option( 'linker_registration_dispositions', $audit, false );
				}
			}
		);
		$slot = RegistrationSlots::reserve( wp_generate_uuid4(), 2048 );
		$this->assertIsArray( $slot );
		$staff = get_users(
			array(
				'role'   => 'administrator',
				'fields' => 'ID',
				'number' => 1,
			)
		);
		$this->as_user( (int) $staff[0] );
		$fail = static fn ( string $query ): string => str_starts_with( $query, 'UPDATE ' ) && str_contains( $query, RegistrationSlots::OPTION ) ? 'DO 0' : $query;
		add_filter( 'query', $fail );
		try {
			$this->assertFalse( RegistrationSlots::resolve_interrupted( $slot['key'], 'This must not be committed without its release.' ) );
		} finally {
				remove_filter( 'query', $fail );
		}
		$this->assertSame( $audit, get_option( 'linker_registration_dispositions' ) );
		$this->assertSame( 1, $this->summary()['interrupted'] );
	}

	/**
	 * Killing a pre-create process leaves no user/body/reservation, while the public attempt stays charged.
	 */
	public function test_killed_native_precreate_rolls_back_only_uncommitted_capacity(): void {
		$initial = $this->summary();
		$post    = $this->public_post( 50 );
		$barrier = tempnam( sys_get_temp_dir(), 'registration-kill-' );
		unlink( $barrier );
		$ready   = $barrier . '.ready';
		$command = array( PHP_BINARY, '-c', dirname( (string) getenv( 'LINKER_WP_ROOT' ) ) . '/php.ini', dirname( __DIR__, 2 ) . '/fixtures/registration_capacity_writer.php' );
		$process = proc_open( $command, array( array( 'pipe', 'r' ), array( 'pipe', 'w' ), array( 'pipe', 'w' ) ), $pipes );
		$this->assertIsResource( $process );
		fwrite(
			$pipes[0],
			(string) wp_json_encode(
				array(
					'post'    => $post,
					'cookie'  => $_COOKIE[ Identity::COOKIE ],
					'address' => '192.0.2.50',
					'ready'   => $ready,
					'release' => $barrier,
				)
			)
		);
		fclose( $pipes[0] );
		$until = microtime( true ) + 10;
		while ( ! file_exists( $ready ) && microtime( true ) < $until ) {
			usleep( 20000 );
		}
		$this->assertFileExists( $ready );
		proc_terminate( $process, 9 );
		fclose( $pipes[1] );
		fclose( $pipes[2] );
		proc_close( $process );
		unlink( $ready );
		$this->assertFalse( email_exists( $post['email'] ) );
		$until = microtime( true ) + 2;
		do {
			$final = RegistrationSlots::summary();
			if ( is_array( $final ) ) {
				break;
			} usleep( 20000 );
		} while ( microtime( true ) < $until );
		$this->assertSame( $initial, $final );
		$this->assertCount( 0, self::mail_jobs_after( $this->mail_marker ) );
		wp_cache_delete( Ledger::OPTION, 'options' );
		$this->assertStringContainsString( $post['linker_request_id'], (string) wp_json_encode( get_option( Ledger::OPTION ) ) );
	}

	/** An authenticated pending edit and a new registration cannot spend the same final profile bytes. */
	public function test_pending_edit_and_registration_share_one_native_serial_point(): void {
		$customer = $this->customer();
		update_user_meta( $customer->get_id(), Approval::STATUS_META, Approval::PENDING );
		$initial     = $this->summary();
		$post        = $this->public_post( 51 );
		$prospective = RegistrationSlots::profile_bytes( $post, $post['email'], 'en_US' );
		$this->assertIsArray( RegistrationSlots::reserve( wp_generate_uuid4(), RegistrationSlots::MAX_BYTES - $initial['business_bytes'] - $prospective ) );
		$barrier = tempnam( sys_get_temp_dir(), 'registration-edit-' );
		unlink( $barrier );
		$ready   = $barrier . '.ready';
		$company = $customer->get_billing_company() . str_repeat( ' native edit', 12 );
		$command = array( PHP_BINARY, '-c', dirname( (string) getenv( 'LINKER_WP_ROOT' ) ) . '/php.ini', dirname( __DIR__, 2 ) . '/fixtures/registration_capacity_writer.php' );
		$process = proc_open( $command, array( array( 'pipe', 'r' ), array( 'pipe', 'w' ), array( 'pipe', 'w' ) ), $pipes );
		$this->assertIsResource( $process );
		fwrite(
			$pipes[0],
			(string) wp_json_encode(
				array(
					'edit_user' => $customer->get_id(),
					'company'   => $company,
					'post'      => array(),
					'cookie'    => $_COOKIE[ Identity::COOKIE ],
					'address'   => '192.0.2.51',
					'ready'     => $ready,
					'release'   => $barrier,
				)
			)
		);
		fclose( $pipes[0] );
		$until = microtime( true ) + 10;
		while ( ! file_exists( $ready ) && microtime( true ) < $until ) {
			usleep( 20000 ); }
		$this->assertFileExists( $ready );
		$started = microtime( true );
		$errors  = apply_filters( 'woocommerce_process_registration_errors', new WP_Error(), '', $post['password'], $post['email'] );
		$this->assertContains( 'linker_registration_capacity', $errors->get_error_codes() );
		$this->assertLessThan( 2, microtime( true ) - $started );
		$this->assertFalse( email_exists( $post['email'] ) );
		file_put_contents( $barrier, 'release' );
		$result = json_decode( (string) stream_get_contents( $pipes[1] ), true );
		$stderr = stream_get_contents( $pipes[2] );
		fclose( $pipes[1] );
		fclose( $pipes[2] );
		$this->assertSame( 0, proc_close( $process ), (string) $stderr );
		unlink( $ready );
		unlink( $barrier );
		$this->assertSame( $company, $result['saved'] );
		wp_cache_delete( $customer->get_id(), 'user_meta' );
		$this->assertSame( $company, get_user_meta( $customer->get_id(), 'billing_company', true ) );
		$summary = $this->summary();
		$this->assertLessThanOrEqual( RegistrationSlots::MAX_BYTES, $summary['business_bytes'] + $summary['reserved_bytes'] );
		$this->assertCount( 0, self::mail_jobs_after( $this->mail_marker ) );
	}

	/** A lost profile COMMIT acknowledgement must show unknown and read back the committed native state. */
	public function test_unknown_profile_commit_does_not_claim_that_confirmed_native_changes_were_unsaved(): void {
		$customer = $this->customer();
		update_user_meta( $customer->get_id(), Approval::STATUS_META, Approval::PENDING );
		$this->as_user( $customer->get_id() );
		global $wpdb;
		$before_suppress = $wpdb->suppress_errors( true );
		$lose_ack        = null;
		$lose_ack        = static function ( string $query ) use ( &$lose_ack, $wpdb ): string {
			if ( 'COMMIT' === $query ) {
				remove_filter( 'query', $lose_ack );
				$wpdb->query( 'COMMIT' );
				return 'SYNTHETIC LOST COMMIT ACK';
			}
			return $query;
		};
		add_filter( 'query', $lose_ack );
		try {
			$customer->set_billing_company( 'Committed native profile' );
			$customer->save();
			$this->fail( 'The unknown SQL acknowledgement must not be reported as a normal success.' );
		} catch ( \WC_Data_Exception $error ) {
			$this->assertStringContainsString( 'could not be confirmed', $error->getMessage() );
			$this->assertStringNotContainsString( 'could not be saved', $error->getMessage() );
		} finally {
			remove_filter( 'query', $lose_ack );
			$wpdb->suppress_errors( $before_suppress ); }
		$this->assertSame( 'Committed native profile', ( new \WC_Customer( $customer->get_id() ) )->get_billing_company() );
	}

	/** Committed identity plus a lost acknowledgement remains a created account with two recoverable native notices. */
	public function test_unknown_registration_commit_keeps_native_account_and_pending_notifications(): void {
		$post = $this->public_post( 52 );
		$this->assertFalse( apply_filters( 'woocommerce_process_registration_errors', new WP_Error(), '', $post['password'], $post['email'] )->has_errors() );
		global $wpdb;
		$before_suppress = $wpdb->suppress_errors( true );
		$lose_ack        = null;
		$lose_ack        = static function ( string $query ) use ( &$lose_ack, $wpdb ): string {
			if ( 'COMMIT' === $query ) {
				remove_filter( 'query', $lose_ack );
				$wpdb->query( 'COMMIT' );
				return 'SYNTHETIC LOST COMMIT ACK'; }
			return $query;
		};
		add_filter( 'query', $lose_ack );
		try {
			wc_create_new_customer( $post['email'], '', $post['password'] );
			$this->fail( 'The account completion acknowledgement must remain unknown.' );
		} catch ( \RuntimeException $error ) {
			$this->assertStringContainsString( 'could not be confirmed', $error->getMessage() );
			$this->assertStringNotContainsString( 'has not been created', $error->getMessage() );
		} finally {
			remove_filter( 'query', $lose_ack );
			$wpdb->suppress_errors( $before_suppress );
			foreach ( $GLOBALS['wp_filter']['user_register']->callbacks as $callbacks ) {
				foreach ( $callbacks as $callback ) {
					$function = $callback['function'];
					if ( is_array( $function ) && $function[0] instanceof \Linker\Commerce\Protection\Accounts ) {
						$function[0]->unfinished(); }
				}
			}
		}
		$id = email_exists( $post['email'] );
		$this->assertIsInt( $id );
		$this->own_user( $id );
		$this->assertSame( 'pending', $this->notices( $id )['team']['state'] );
		$this->assertSame( 'pending', $this->notices( $id )['received']['state'] );
		$this->assertCount( 0, self::mail_jobs_after( $this->mail_marker ) );
		do_action( \Linker\Commerce\Inquiry\Assessment\RecoverySchedule::HOOK );
		$this->assertSame( 'accepted', $this->notices( $id )['team']['state'] );
		$this->assertSame( 'accepted', $this->notices( $id )['received']['state'] );
		$this->assertCount( 2, self::mail_jobs_after( $this->mail_marker ) );
	}

	/** Native explicit staff dispositions, not a customer/default label, release real users from the pending pool. */
	public function test_native_staff_approval_rejection_and_deletion_release_only_explicit_accounts(): void {
		$customer = $this->customer();
		update_user_meta( $customer->get_id(), Approval::STATUS_META, Approval::PENDING );
		$initial = $this->summary()['pending_users'];
		update_user_meta( $customer->get_id(), Approval::STATUS_META, Approval::APPROVED );
		$this->assertSame( $initial, $this->summary()['pending_users'] );
		update_user_meta( $customer->get_id(), Approval::STATUS_META, Approval::PENDING );
		$staff = get_users(
			array(
				'role'   => 'administrator',
				'fields' => 'ID',
				'number' => 1,
			)
		);
		$this->as_user( (int) $staff[0] );
		$this->assertTrue( ( new Approval() )->set( $customer->get_id(), Approval::RESTRICTED, 'Please confirm your company details.' ) );
		$this->assertSame( $initial, $this->summary()['pending_users'] );
		$this->assertTrue( ( new Approval() )->set( $customer->get_id(), Approval::APPROVED ) );
		$this->assertSame( $initial - 1, $this->summary()['pending_users'] );
		$this->assertTrue( ( new Approval() )->set( $customer->get_id(), Approval::RESTRICTED, 'Please confirm the updated details.' ) );
		$this->assertSame( $initial, $this->summary()['pending_users'] );
		$this->assertTrue( ( new Approval() )->set( $customer->get_id(), Approval::REJECTED, 'Company details could not be verified.' ) );
		$this->assertSame( $initial - 1, $this->summary()['pending_users'] );
		( new Approval() )->set( $customer->get_id(), Approval::PENDING );
		$this->assertSame( $initial, $this->summary()['pending_users'] );
		require_once ABSPATH . 'wp-admin/includes/user.php';
		$this->assertTrue( wp_delete_user( $customer->get_id() ) );
		$this->assertSame( $initial - 1, $this->summary()['pending_users'] );
	}

	/** Actual Woo billing handler must return its normal notice instead of an uncaught save exception. */
	public function test_native_billing_form_handler_refuses_before_its_uncaught_save_boundary(): void {
		$customer = $this->customer();
		update_user_meta( $customer->get_id(), Approval::STATUS_META, Approval::PENDING );
		$this->as_user( $customer->get_id() );
		$before = $this->summary();
		$this->assertIsArray( RegistrationSlots::reserve( wp_generate_uuid4(), RegistrationSlots::MAX_BYTES - $before['business_bytes'] ) );
		$old_request = $_REQUEST;
		$this->later(
			static function () use ( $old_request ): void {
				$_REQUEST = $old_request;
				wc_clear_notices();
			}
		);
		wc_clear_notices();
		$_POST                                      = array(
			'action'             => 'edit_address',
			'billing_country'    => 'DE',
			'billing_first_name' => 'Maria',
			'billing_last_name'  => 'Beispiel',
			'billing_company'    => 'A larger native form company',
			'billing_address_1'  => 'Teststrasse 1',
			'billing_city'       => 'Cologne',
			'billing_postcode'   => '50667',
			'billing_email'      => $customer->get_email(),
		);
		$_REQUEST['woocommerce-edit-address-nonce'] = wp_create_nonce( 'woocommerce-edit_address' );
		$expected                                   = $_POST;
		global $wp;
		$query_vars                     = $wp->query_vars;
		$wp->query_vars['edit-address'] = 'billing';
		try {
			\WC_Form_Handler::save_address(); } finally {
			$wp->query_vars = $query_vars; }
			$this->assertSame( 1, wc_notice_count( 'error' ) );
			$this->assertStringContainsString( 'could not be saved', wc_get_notices( 'error' )[0]['notice'] );
			$this->assertSame( $expected, $_POST );
			$this->assertSame( $customer->get_billing_company(), get_user_meta( $customer->get_id(), 'billing_company', true ) );
	}

	/** A skipped notice's cancellation and source acknowledgement must roll back together. */
	public function test_skipped_notice_ack_failure_retains_its_native_reservation_until_recovery(): void {
		$receipt          = WC()->mailer()->get_emails()[ RegistrationReceivedEmail::class ];
		$enabled          = $receipt->enabled;
		$receipt->enabled = 'no';
		$this->later(
			static function () use ( $receipt, $enabled ): void {
				$receipt->enabled = $enabled;
			}
		);
		$post = $this->public_post( 53 );
		$this->assertFalse( apply_filters( 'woocommerce_process_registration_errors', new WP_Error(), '', $post['password'], $post['email'] )->has_errors() );
		$fail = static fn ( $old, $id, $key ) => RegistrationNotices::META === $key ? false : $old;
		add_filter( 'update_user_metadata', $fail, 10, 3 );
		try {
			$id = wc_create_new_customer( $post['email'], '', $post['password'] ); } finally {
			remove_filter( 'update_user_metadata', $fail, 10 ); }
			$this->assertIsInt( $id );
			$this->own_user( $id );
			$state = $this->notices( $id );
			$scope = $state['received']['reservation'];
			wp_cache_delete( IntakeStore::OPTION, 'options' );
			$this->assertArrayHasKey( $scope, get_option( IntakeStore::OPTION )['mail_capacity']['reservations'] );
			RegistrationNotices::recover();
			$this->assertArrayNotHasKey( 'reservation', $this->notices( $id )['received'] );
			$this->assertSame( 'skipped', $this->notices( $id )['received']['state'] );
			$this->assertSame( '', get_user_meta( $id, RegistrationNotices::PENDING, true ) );
			$this->assertCount( 1, self::mail_jobs_after( $this->mail_marker ) );
	}

	/** Privacy cannot delete owned jobs/free capacity if the durable source cannot acknowledge erasure. */
	public function test_native_privacy_source_write_failure_rolls_back_job_deletion_and_capacity(): void {
		$post = $this->public_post( 54 );
		$this->assertFalse( apply_filters( 'woocommerce_process_registration_errors', new WP_Error(), '', $post['password'], $post['email'] )->has_errors() );
		$id = wc_create_new_customer( $post['email'], '', $post['password'] );
		$this->assertIsInt( $id );
		$this->own_user( $id );
		$before = $this->notices( $id );
		$jobs   = self::mail_jobs_after( $this->mail_marker );
		$fail   = static fn ( $old, $user_id, $key ) => RegistrationNotices::META === $key ? false : $old;
		add_filter( 'update_user_metadata', $fail, 10, 3 );
		try {
			$this->assertFalse( RegistrationNotices::erase( $id ) ); } finally {
			remove_filter( 'update_user_metadata', $fail, 10 ); }
			$this->assertSame( $before, $this->notices( $id ) );
			wp_cache_set_posts_last_changed();
			$this->assertSame( $jobs, self::mail_jobs_after( $this->mail_marker ) );
			$this->assertTrue( RegistrationNotices::erase( $id ) );
			$this->assertCount( 0, self::mail_jobs_after( $this->mail_marker ) );
	}

	/** A second native worker already dispatching a notice keeps erasure pending without partial deletion. */
	public function test_native_privacy_keeps_both_jobs_if_another_connection_owns_one_notice(): void {
		$post = $this->public_post( 55 );
		$this->assertFalse( apply_filters( 'woocommerce_process_registration_errors', new WP_Error(), '', $post['password'], $post['email'] )->has_errors() );
		$id = wc_create_new_customer( $post['email'], '', $post['password'] );
		$this->assertIsInt( $id );
		$this->own_user( $id );
		$state = $this->notices( $id );
		$jobs  = self::mail_jobs_after( $this->mail_marker );
		global $wpdb;
		$other = new \wpdb( (string) constant( 'DB_USER' ), (string) constant( 'DB_PASSWORD' ), (string) constant( 'DB_NAME' ), (string) constant( 'DB_HOST' ) );
		$lock  = 'linker-assessment-' . md5( (string) constant( 'DB_NAME' ) . '/' . $wpdb->prefix . '/mail-job-' . $state['received']['job'] );
		$this->assertSame( '1', $other->get_var( $other->prepare( 'SELECT GET_LOCK(%s, 0)', $lock ) ) );
		try {
			$this->assertFalse( RegistrationNotices::erase( $id ) );
			$this->assertSame( $state, $this->notices( $id ) );
			$this->assertSame( $jobs, self::mail_jobs_after( $this->mail_marker ) );
		} finally {
			$other->get_var( $other->prepare( 'SELECT RELEASE_LOCK(%s)', $lock ) );
			$other->close(); }
		$this->assertTrue( RegistrationNotices::erase( $id ) );
	}

	/** A failed source ACK may roll back its savepoint, never an unrelated outer owner's uncommitted write. */
	public function test_native_privacy_ack_failure_preserves_outer_transaction_owner(): void {
		$post = $this->public_post( 56 );
		$this->assertFalse( apply_filters( 'woocommerce_process_registration_errors', new WP_Error(), '', $post['password'], $post['email'] )->has_errors() );
		$id = wc_create_new_customer( $post['email'], '', $post['password'] );
		$this->assertIsInt( $id );
		$this->own_user( $id );
		global $wpdb;
		$key = 'linker_registration_outer_' . self::tag();
		$wpdb->query( 'START TRANSACTION' );
		$wpdb->insert(
			$wpdb->options,
			array(
				'option_name'  => $key,
				'option_value' => 'caller-owned',
				'autoload'     => 'off',
			)
		);
		$fail = static fn ( $old, $user_id, $meta_key ) => RegistrationNotices::META === $meta_key ? false : $old;
		add_filter( 'update_user_metadata', $fail, 10, 3 );
		try {
			$this->assertFalse( RegistrationNotices::erase( $id ) );
			$this->assertTrue( Capacity::transaction_active() );
			$this->assertSame( 'caller-owned', $wpdb->get_var( $wpdb->prepare( "SELECT option_value FROM {$wpdb->options} WHERE option_name = %s", $key ) ) );
			$other = new \wpdb( (string) constant( 'DB_USER' ), (string) constant( 'DB_PASSWORD' ), (string) constant( 'DB_NAME' ), (string) constant( 'DB_HOST' ) );
			$query = $wpdb->prepare( "SELECT option_value FROM {$wpdb->options} WHERE option_name = %s", $key );
			$this->assertNull( $other->get_var( $query ) );
			$other->close();
		} finally {
			remove_filter( 'update_user_metadata', $fail, 10 );
			$wpdb->query( 'ROLLBACK' ); }
		$this->assertCount( 2, self::mail_jobs_after( $this->mail_marker ) );
	}

	/** Extra native business metadata cannot commit beyond the profile envelope proved before creation. */
	public function test_native_post_filter_profile_expansion_cannot_escape_precreate_byte_bound(): void {
		$post = $this->public_post( 57 );
		$this->assertFalse( apply_filters( 'woocommerce_process_registration_errors', new WP_Error(), '', $post['password'], $post['email'] )->has_errors() );
		$expand = static function ( array $meta ): array {
			$meta['billing_fixture_extra'] = str_repeat( 'x', 4096 );
			return $meta;
		};
		add_filter( 'insert_custom_user_meta', $expand, PHP_INT_MAX );
		$refused = false;
		try {
			$new = wc_create_new_customer( $post['email'], '', $post['password'] );
			if ( is_int( $new ) ) {
				$this->own_user( $new ); }
		} catch ( \RuntimeException $error ) {
			$refused = str_contains( $error->getMessage(), 'could not be confirmed' ); } finally {
			remove_filter( 'insert_custom_user_meta', $expand, PHP_INT_MAX ); }
			$this->assertTrue( $refused, 'An unreserved native profile expansion cannot become a committed account.' );
			$this->assertFalse( email_exists( $post['email'] ) );
			$this->assertSame( 0, $this->summary()['interrupted'] );
			$this->assertCount( 0, self::mail_jobs_after( $this->mail_marker ) );
	}

	/** Woo account details writes core names before customer->save, so the guard must precede both writers. */
	public function test_native_account_details_handler_does_not_partially_save_core_names_at_full_capacity(): void {
		$customer = $this->customer();
		update_user_meta( $customer->get_id(), Approval::STATUS_META, Approval::PENDING );
		$this->as_user( $customer->get_id() );
		$before = $this->summary();
		$this->assertIsArray( RegistrationSlots::reserve( wp_generate_uuid4(), RegistrationSlots::MAX_BYTES - $before['business_bytes'] ) );
		$user        = $this->native_user( $customer->get_id() );
		$first       = get_user_meta( $user->ID, 'first_name', true );
		$old_request = $_REQUEST;
		$this->later(
			static function () use ( $old_request ): void {
				$_REQUEST = $old_request;
				wc_clear_notices();
			}
		);
		wc_clear_notices();
		$_POST                                  = array(
			'action'               => 'save_account_details',
			'account_first_name'   => 'Maria extra business data',
			'account_last_name'    => 'Beispiel',
			'account_display_name' => $user->display_name . ' growth',
			'account_email'        => $user->user_email,
		);
		$_REQUEST['save-account-details-nonce'] = wp_create_nonce( 'save_account_details' );
		$expected                               = $_POST;
		\WC_Form_Handler::save_account_details();
		$this->assertSame( 1, wc_notice_count( 'error' ) );
		$this->assertSame( $first, get_user_meta( $user->ID, 'first_name', true ), 'The earlier wp_update_user write must not bypass the envelope.' );
		$this->assertSame( $user->display_name, $this->native_user( $user->ID )->display_name );
		$this->assertSame( $expected, $_POST );
		$old_query           = $GLOBALS['wp_query'];
		$GLOBALS['wp_query'] = new \WP_Query( array( 'page_id' => wc_get_page_id( 'myaccount' ) ) ); // phpcs:ignore WordPress.WP.GlobalVariablesOverride.Prohibited -- Render the actual account template in its native page context.
		$this->later(
			static function () use ( $old_query ): void {
				$GLOBALS['wp_query'] = $old_query; // phpcs:ignore WordPress.WP.GlobalVariablesOverride.Prohibited -- Restore only the native query replaced by this fixture.
			}
		);
		$this->assertTrue( is_account_page() );
		ob_start();
		wc_get_template( 'myaccount/form-edit-account.php', array( 'user' => $this->native_user( $user->ID ) ) );
		$html = (string) ob_get_clean();
		$this->assertStringContainsString( 'value="Maria extra business data"', $html, 'The real form must retain the refused non-secret name, not only $_POST.' );
		$this->assertStringNotContainsString( 'name="password_current" value=', $html );
		$_POST['account_first_name'] = 'Unverified later input';
		$this->assertSame( 'Maria extra business data', \Linker\Commerce\Registration\PendingProfileCapacity::account_value( 'account_first_name', 'native' ) );
		$this->assertSame( 'empty', \Linker\Commerce\Registration\PendingProfileCapacity::account_value( 'password_current', 'empty' ) );
		$this->as_user( 0 );
		$this->assertSame( 'native', \Linker\Commerce\Registration\PendingProfileCapacity::account_value( 'account_first_name', 'native' ) );
	}

	/**
	 * Actual native creation/profile writes must never reconnect into autocommit.
	 *
	 * @testWith ["registration", false]
	 *           ["registration", true]
	 *           ["profile", false]
	 *           ["profile", true]
	 * @param string $writer Native writer across before/after hooks.
	 * @param bool   $partial Kill after a first uncommitted native write.
	 * @throws \RuntimeException The synthetic profile fixture must have its actual native owner.
	 */
	public function test_real_connection_loss_cannot_partially_commit_native_registration_or_profile( string $writer, bool $partial ): void {
		global $wpdb;
		$observer   = new \wpdb( (string) constant( 'DB_USER' ), (string) constant( 'DB_PASSWORD' ), (string) constant( 'DB_NAME' ), (string) constant( 'DB_HOST' ) );
		$retries    = $wpdb->__get( 'reconnect_retries' );
		$report     = ( new \mysqli_driver() )->report_mode;
		$customer   = null;
		$found      = 0;
		$orphan     = 0;
		$company    = '';
		$name       = '';
		$profile_id = 0;
		$post       = array();
		if ( 'registration' === $writer ) {
			$post   = $this->public_post( $partial ? 54 : 53 );
			$errors = apply_filters( 'woocommerce_process_registration_errors', new WP_Error(), '', $post['password'], $post['email'] );
			$this->assertFalse( $errors->has_errors(), implode( ' ', $errors->get_error_messages() ) );
		} else {
			$customer   = $this->customer();
			$profile_id = $customer->get_id();
			$customer->set_billing_company( 'Original business' );
			$customer->save();
			update_user_meta( $customer->get_id(), Approval::STATUS_META, Approval::PENDING );
			$this->as_user( $customer->get_id() );
			$customer->set_display_name( 'Uncommitted profile name' );
			$customer->set_billing_company( 'Uncommitted business' );
		}
		$killed = false;
		$kill   = static function ( string $sql ) use ( $observer, $writer, $partial, &$killed ): string {
			global $wpdb;
			$write    = preg_match( '/^(INSERT|UPDATE) /', $sql );
			$target   = $partial ? $wpdb->usermeta : $wpdb->users;
			$specific = ! $partial || str_contains( $sql, 'registration' === $writer ? RegistrationSlots::META : 'billing_company' );
			if ( ! $killed && $write && str_contains( $sql, $target ) && $specific ) {
				$killed = true;
				$observer->query( 'KILL CONNECTION ' . $wpdb->__get( 'dbh' )->thread_id );
			}
			return $sql;
		};
		add_filter( 'query', $kill );
		$caught = false;
		try {
			if ( 'registration' === $writer ) {
				wc_create_new_customer( $post['email'], '', $post['password'] );
			} else {
				if ( ! $customer instanceof \WC_Customer ) {
					throw new \RuntimeException( 'fixture_missing_native_profile' ); }
				$customer->save(); }
		} catch ( \Throwable $error ) {
			$caught = true; } finally {
			remove_filter( 'query', $kill );
			$hook  = 'registration' === $writer ? 'user_register' : 'woocommerce_before_customer_object_save';
			$class = 'registration' === $writer ? \Linker\Commerce\Protection\Accounts::class : \Linker\Commerce\Registration\PendingProfileCapacity::class;
			foreach ( $GLOBALS['wp_filter'][ $hook ]->callbacks as $callbacks ) {
				foreach ( $callbacks as $callback ) {
					$function = $callback['function'];
					if ( is_array( $function ) && $function[0] instanceof $class ) {
						$function[0]->unfinished(); }
				}
			}
			}

			if ( 'registration' === $writer ) {
				$found  = (int) $observer->get_var( $observer->prepare( 'SELECT ID FROM %i WHERE user_email = %s', $wpdb->users, $post['email'] ) );
				$marker = hash_hmac( 'sha256', 'registration|' . $post['linker_request_id'], wp_salt( 'auth' ) );
				$orphan = (int) $observer->get_var( $observer->prepare( 'SELECT COUNT(*) FROM %i WHERE meta_key = %s AND meta_value = %s', $wpdb->usermeta, RegistrationSlots::META, $marker ) );
			} else {
				$company = $observer->get_var( $observer->prepare( 'SELECT meta_value FROM %i WHERE user_id = %d AND meta_key = %s', $wpdb->usermeta, $profile_id, 'billing_company' ) );
				$name    = $observer->get_var( $observer->prepare( 'SELECT display_name FROM %i WHERE ID = %d', $wpdb->users, $profile_id ) );
			}
			// Only the fixture reconnects its dead local test client after observing native state.
			$this->assertTrue( $wpdb->db_connect( false ) );
			$observer->close();
			if ( 'registration' === $writer && $found ) {
				$this->own_user( $found ); }
			$this->assertTrue( $killed );
			$this->assertTrue( $caught, 'A lost original transaction cannot be acknowledged as success.' );
			$this->assertSame( $retries, $wpdb->__get( 'reconnect_retries' ) );
			$this->assertSame( $report, ( new \mysqli_driver() )->report_mode );
			if ( 'registration' === $writer ) {
				$this->assertSame( 0, $found, 'No native user may be replayed into autocommit after connection loss.' );
				$this->assertSame( 0, $orphan, 'A rolled-back user must not leave replayed orphan registration metadata.' );
			} else {
				$this->assertSame( 'Original business', $company );
				$this->assertNotSame( 'Uncommitted profile name', $name );
			}
	}

	/**
	 * Staff audit/slot and privacy source/job writes must not split after real connection loss.
	 *
	 * @testWith ["disposition"]
	 *           ["privacy"]
	 * @param string $writer Actual native short writer.
	 */
	public function test_real_connection_loss_keeps_staff_disposition_or_privacy_atomic( string $writer ): void {
		global $wpdb;
		$observer = new \wpdb( (string) constant( 'DB_USER' ), (string) constant( 'DB_PASSWORD' ), (string) constant( 'DB_NAME' ), (string) constant( 'DB_HOST' ) );
		$before   = array();
		$id       = 0;
		$slot     = array();
		if ( 'privacy' === $writer ) {
			$post = $this->public_post( 57 );
			$this->assertFalse( apply_filters( 'woocommerce_process_registration_errors', new WP_Error(), '', $post['password'], $post['email'] )->has_errors() );
			$id = wc_create_new_customer( $post['email'], '', $post['password'] );
			$this->assertIsInt( $id );
			$this->own_user( $id );
			$before = $this->notices( $id );
		} else {
			$slot = RegistrationSlots::reserve( wp_generate_uuid4(), 2048 );
			$this->assertIsArray( $slot );
			$staff = get_users(
				array(
					'role'   => 'administrator',
					'fields' => 'ID',
					'number' => 1,
				)
			);
			$this->as_user( (int) $staff[0] );
			$before = get_option( 'linker_registration_dispositions', array() );
		}
		$killed = false;
		$kill   = static function ( string $sql ) use ( $observer, $writer, &$killed ): string {
			global $wpdb;
			$target = 'privacy' === $writer ? RegistrationNotices::META : RegistrationSlots::OPTION;
			if ( ! $killed && preg_match( '/^(INSERT|UPDATE) /', $sql ) && str_contains( $sql, $target ) ) {
				$killed = true;
				$observer->query( 'KILL CONNECTION ' . $wpdb->__get( 'dbh' )->thread_id );
			}
			return $sql;
		};
		add_filter( 'query', $kill );
		try {
			$result = 'privacy' === $writer ? RegistrationNotices::erase( $id ) : RegistrationSlots::resolve_interrupted( $slot['key'], 'Synthetic killed audit cannot release this slot.' ); } finally {
			remove_filter( 'query', $kill ); }
			$this->assertTrue( $wpdb->db_connect( false ) );
			$observer->close();
			$this->assertTrue( $killed );
			$this->assertFalse( $result );
			if ( 'privacy' === $writer ) {
				$this->assertSame( $before, $this->notices( $id ) );
				foreach ( $before as $plan ) {
					clean_post_cache( $plan['job'] );
					$this->assertNotNull( ( new \Linker\Commerce\Mail\JobStore() )->load( $plan['job'] ) ); }
				$this->assertTrue( RegistrationNotices::erase( $id ) );
			} else {
				wp_cache_delete( 'linker_registration_dispositions', 'options' );
				$this->assertSame( $before, get_option( 'linker_registration_dispositions', array() ) );
				$this->assertSame( 1, $this->summary()['interrupted'] );
			}
	}

	/** The committed native registration job already has recovery before any dispatch and consumes once. */
	public function test_native_registration_accepted_source_has_original_action_before_dispatch_and_consumes_once(): void {
		$post = $this->public_post( 58 );
		$this->assertFalse( apply_filters( 'woocommerce_process_registration_errors', new WP_Error(), '', $post['password'], $post['email'] )->has_errors() );
		$id = wc_create_new_customer( $post['email'], '', $post['password'] );
		$this->assertIsInt( $id );
		$this->own_user( $id );
		$state = $this->notices( $id );
		foreach ( $state as $plan ) {
			$this->assertSame( 'accepted', $plan['state'] );
			$this->assertArrayNotHasKey( 'parts', $plan );
			$this->assertNotFalse( as_has_scheduled_action( \Linker\Commerce\Mail\Outbox::HOOK, array( $plan['job'] ), \Linker\Commerce\Mail\Outbox::GROUP ) );
		}
		$job       = $state['team']['job'];
		$calls     = 0;
		$transport = static function () use ( &$calls ) {
			++$calls;
			return true;
		};
		add_filter( 'pre_wp_mail', $transport, -1000 );
		try {
			do_action( \Linker\Commerce\Mail\Outbox::HOOK, $job );
			do_action( \Linker\Commerce\Mail\Outbox::HOOK, $job );
		} finally {
			remove_filter( 'pre_wp_mail', $transport, -1000 ); }
		$this->assertSame( 1, $calls, 'The original native job consumes once; the transport is synthetic and sends no email.' );
		$this->assertNull( ( new \Linker\Commerce\Mail\JobStore() )->load( $job ) );
		$this->assertFalse( as_has_scheduled_action( \Linker\Commerce\Mail\Outbox::HOOK, array( $job ), \Linker\Commerce\Mail\Outbox::GROUP ) );
		RegistrationNotices::recover();
		$this->assertSame( $state, $this->notices( $id ), 'A consumed job is never recreated from the cleared source.' );
	}

	/** A completed policy keeps the frozen recipient after a failed handoff and native email edit. */
	public function test_review_receipt_recovery_keeps_frozen_recipient_after_policy_completion(): void {
		$post = $this->public_post( 59 );
		$this->assertFalse( apply_filters( 'woocommerce_process_registration_errors', new WP_Error(), '', $post['password'], $post['email'] )->has_errors() );
		$fail = static fn ( $old, $id, $key ) => RegistrationNotices::META === $key ? false : $old;
		add_filter( 'update_user_metadata', $fail, 10, 3 );
		try {
			$id = wc_create_new_customer( $post['email'], '', $post['password'] );
		} finally {
			remove_filter( 'update_user_metadata', $fail, 10 );
		}
		$this->assertIsInt( $id );
		$this->own_user( $id );
		$this->assertSame( 'pending', $this->notices( $id )['received']['state'] );
		$budget = json_decode( (string) get_option( Ledger::OPTION ), true );
		$policy = array_filter( $budget['receipts'], static fn ( array $r ): bool => 'customer_receipt' === $r['purpose'] );
		$this->assertCount( 1, $policy );
		$this->assertSame( 'completed', reset( $policy )['status'] );
		add_filter( 'send_email_change_email', '__return_false' );
		try {
			$this->assertIsInt(
				wp_update_user(
					array(
						'ID'         => $id,
						'user_email' => 'changed-' . self::tag() . '@example.test',
					)
				)
			);
		} finally {
			remove_filter( 'send_email_change_email', '__return_false' );
		}
		RegistrationNotices::deliver( $id, 'received' );
		$state = $this->notices( $id );
		$this->assertSame( 'accepted', $state['received']['state'] );
		$job = ( new \Linker\Commerce\Mail\JobStore() )->load( $state['received']['job'] );
		$this->assertNotNull( $job );
		$this->assertSame( array( $post['email'] ), $job['message']->to );
		$recovered = json_decode( (string) get_option( Ledger::OPTION ), true );
		$after     = array_filter( $recovered['receipts'], static fn ( array $r ): bool => 'customer_receipt' === $r['purpose'] );
		$this->assertSame( $policy, $after );
		$this->assertSame( $budget['buckets'], $recovered['buckets'] );
	}

	/** A nonthrowing final Ledger completion failure must not commit a native account. */
	public function test_review_final_operation_ack_failure_rolls_back_native_account(): void {
		$post = $this->public_post( 60 );
		$this->assertFalse( apply_filters( 'woocommerce_process_registration_errors', new WP_Error(), '', $post['password'], $post['email'] )->has_errors() );
		$failed = false;
		$fault  = static function ( string $sql ) use ( &$failed ): string {
			if ( ! $failed && str_starts_with( $sql, 'UPDATE ' ) && str_contains( $sql, Ledger::OPTION ) ) {
				$failed = true;
				return 'DO 0';
			}
			return $sql;
		};
		add_filter( 'query', $fault );
		$unknown = false;
		try {
			$id = wc_create_new_customer( $post['email'], '', $post['password'] );
			if ( is_int( $id ) ) {
				$this->own_user( $id );
			}
		} catch ( \RuntimeException $error ) {
			$unknown = str_contains( $error->getMessage(), 'could not be confirmed' );
		} finally {
			remove_filter( 'query', $fault );
		}
		$this->assertTrue( $failed );
		$this->assertTrue( $unknown );
		$this->assertFalse( email_exists( $post['email'] ) );
		$this->assertCount( 0, self::mail_jobs_after( $this->mail_marker ) );
		$this->assertSame( 0, $this->summary()['interrupted'] );
	}

	/**
	 * A failed original-owner selector must not become empty-complete or poison retry.
	 *
	 * @testWith ["export"]
	 *           ["erase"]
	 * @param string $method Registered native privacy callback.
	 */
	public function test_review_privacy_owner_read_failure_is_retryable_after_email_edit( string $method ): void {
		$post = $this->public_post( 61 );
		$this->assertFalse( apply_filters( 'woocommerce_process_registration_errors', new WP_Error(), '', $post['password'], $post['email'] )->has_errors() );
		$id = wc_create_new_customer( $post['email'], '', $post['password'] );
		$this->assertIsInt( $id );
		$this->own_user( $id );
		add_filter( 'send_email_change_email', '__return_false' );
		try {
			wp_update_user(
				array(
					'ID'         => $id,
					'user_email' => 'changed-' . self::tag() . '@example.test',
				)
			);
		} finally {
			remove_filter( 'send_email_change_email', '__return_false' );
		}
		$before = $this->notices( $id );
		$failed = false;
		$fault  = static function ( string $sql ) use ( &$failed ): string {
			if ( ! $failed && str_starts_with( $sql, 'SELECT ' ) && str_contains( $sql, RegistrationNotices::OWNER ) ) {
				$failed = true;
				return 'SELECT id FROM linker_synthetic_missing_owner_table';
			}
			return $sql;
		};
		global $wpdb;
		$previous = $wpdb->suppress_errors( true );
		add_filter( 'query', $fault );
		$privacy = new RegistrationPrivacy();
		try {
			$result = $privacy->$method( $post['email'] );
		} finally {
			remove_filter( 'query', $fault );
			$wpdb->suppress_errors( $previous );
		}
		$this->assertTrue( $failed );
		$this->assertSame( $before, $this->notices( $id ) );
		if ( 'export' === $method ) {
			$this->assertInstanceOf( WP_Error::class, $result );
		} else {
			$this->assertTrue( $result['items_retained'] );
			$this->assertFalse( $result['done'] );
			$this->assertFalse( $result['items_removed'] );
		}
		$export = $privacy->export( $post['email'] );
		$this->assertIsArray( $export );
		$this->assertNotEmpty( $export['data'] );
		$this->assertTrue( $privacy->erase( $post['email'] )['done'] );
		$this->assertSame( 'erased', $this->notices( $id )['received']['state'] );
	}

	/**
	 * The actual native handler and parsed write target own both final-byte success and refusal.
	 *
	 * @testWith ["case"]
	 *           ["body_target"]
	 * @param string $variant Native REST matching/parameter behavior.
	 */
	public function test_review_native_rest_actual_target_respects_last_profile_byte( string $variant ): void {
		$customer = $this->customer();
		$id       = $customer->get_id();
		update_user_meta( $id, Approval::STATUS_META, Approval::PENDING );
		$this->as_user( $id );
		$before = $this->summary();
		$this->assertIsArray( RegistrationSlots::reserve( wp_generate_uuid4(), RegistrationSlots::MAX_BYTES - $before['business_bytes'] - 1 ) );
		foreach ( array( 'x', 'xx' ) as $index => $value ) {
			$request = new \WP_REST_Request( 'POST', 'case' === $variant ? '/WP/v2/USERS/ME' : '/wp/v2/users/99999999' );
			$request->set_header( 'content-type', 'application/json' );
			$request->set_body(
				(string) wp_json_encode(
					array(
						'id'         => $id,
						'first_name' => $value,
					)
				)
			);
			$result = rest_do_request( $request );
			$this->assertSame( 0 === $index ? 200 : 503, $result->get_status() );
			$this->assertSame( 'x', get_user_meta( $id, 'first_name', true ) );
			$after = $this->summary();
			$this->assertSame( RegistrationSlots::MAX_BYTES, $after['business_bytes'] + $after['reserved_bytes'] );
		}
	}

	/** Frozen To normalization keeps the original single-recipient receipt identity byte-for-byte. */
	public function test_review_receipt_policy_single_target_is_compatible_with_frozen_to(): void {
		$policy = \Linker\Commerce\Protection\ReceiptBudget::class;
		$this->assertSame( '', $policy::reason( 'one@example.test', 600, 'registration' ) );
		$before = json_decode( (string) get_option( Ledger::OPTION ), true );
		$this->assertSame( '', $policy::reason( array( 'Fixture <ONE@example.test>', ' one@example.test ' ), 600, 'registration' ) );
		$after = json_decode( (string) get_option( Ledger::OPTION ), true );
		$this->assertSame( $before['receipts'], $after['receipts'] );
		$this->assertSame( $before['buckets'], $after['buckets'] );
	}

	/** All frozen targets reserve atomically, replay independent of order and count site once. */
	public function test_review_receipt_policy_multi_target_is_atomic_and_site_is_once(): void {
		$policy = \Linker\Commerce\Protection\ReceiptBudget::class;
		$this->assertSame( '', $policy::reason( array( 'two@example.test', 'one@example.test', 'ONE@example.test' ), 601, 'registration' ) );
		$before = json_decode( (string) get_option( Ledger::OPTION ), true );
		$this->assertCount( 1, $before['receipts'] );
		$this->assertCount( 5, $before['buckets'] );
		$this->assertSame( '', $policy::reason( array( 'one@example.test', 'two@example.test' ), 601, 'registration' ) );
		$after = json_decode( (string) get_option( Ledger::OPTION ), true );
		$this->assertSame( $before['buckets'], $after['buckets'] );
		$this->assertSame( '', $policy::reason( 'one@example.test', 602, 'registration' ) );
		$before = json_decode( (string) get_option( Ledger::OPTION ), true );
		$this->assertSame( 'target_cap', $policy::reason( array( 'fresh@example.test', 'one@example.test' ), 603, 'registration' ) );
		$this->assertSame( $before['buckets'], json_decode( (string) get_option( Ledger::OPTION ), true )['buckets'] );
		foreach ( range( 1, 7 ) as $n ) {
			$this->assertSame( '', $policy::reason( 'site-' . $n . '@example.test', 610 + $n, 'registration' ) );
		}
		$this->assertSame( '', $policy::reason( array( 'last-a@example.test', 'last-b@example.test' ), 620, 'registration' ) );
		$before = json_decode( (string) get_option( Ledger::OPTION ), true );
		$this->assertSame( 'daily_cap', $policy::reason( array( 'overflow-a@example.test', 'overflow-b@example.test' ), 621, 'registration' ) );
		$this->assertSame( $before['buckets'], json_decode( (string) get_option( Ledger::OPTION ), true )['buckets'] );
	}

	/** A real lost writer must not revive a stale sibling payload after independent native erasure. */
	public function test_review_policy_skip_connection_loss_cannot_revive_erased_parts(): void {
		$post = $this->public_post( 62 );
		$this->assertFalse( apply_filters( 'woocommerce_process_registration_errors', new WP_Error(), '', $post['password'], $post['email'] )->has_errors() );
		$fail = static fn ( $old, $id, $key ) => RegistrationNotices::META === $key ? false : $old;
		add_filter( 'update_user_metadata', $fail, 10, 3 );
		try {
			$id = wc_create_new_customer( $post['email'], '', $post['password'] );
		} finally {
			remove_filter( 'update_user_metadata', $fail, 10 );
		}
		$this->assertIsInt( $id );
		$this->own_user( $id );
		$this->assertArrayHasKey( 'parts', $this->notices( $id )['received'] );
		$email          = WC()->mailer()->get_emails()[ NewCustomerEmail::class ];
		$enabled        = $email->enabled;
		$email->enabled = 'no';
		global $wpdb;
		$observer = new \wpdb( (string) constant( 'DB_USER' ), (string) constant( 'DB_PASSWORD' ), (string) constant( 'DB_NAME' ), (string) constant( 'DB_HOST' ) );
		$fired    = false;
		$child    = null;
		$stderr   = '';
		$exit     = -1;
		$fault    = static function ( string $sql ) use ( $observer, $id, &$fired, &$child, &$stderr, &$exit ): string {
			global $wpdb;
			if ( ! $fired && str_starts_with( $sql, 'UPDATE ' ) && str_contains( $sql, RegistrationNotices::META ) && str_contains( $sql, 'skipped' ) ) {
				$fired = true;
				$observer->query( 'KILL CONNECTION ' . $wpdb->__get( 'dbh' )->thread_id );
				$command = array( PHP_BINARY, '-c', dirname( (string) getenv( 'LINKER_WP_ROOT' ) ) . '/php.ini', dirname( __DIR__, 2 ) . '/fixtures/registration_notice_erase_writer.php' );
				$process = proc_open( $command, array( array( 'pipe', 'r' ), array( 'pipe', 'w' ), array( 'pipe', 'w' ) ), $pipes );
				if ( ! is_resource( $process ) ) {
					throw new \RuntimeException( 'native_erase_fixture_unavailable' );
				}
				fwrite( $pipes[0], (string) wp_json_encode( array( 'user' => $id ) ) );
				fclose( $pipes[0] );
				$child  = json_decode( (string) stream_get_contents( $pipes[1] ), true );
				$stderr = (string) stream_get_contents( $pipes[2] );
				fclose( $pipes[1] );
				fclose( $pipes[2] );
				$exit = proc_close( $process );
			}
			return $sql;
		};
		add_filter( 'query', $fault );
		try {
			RegistrationNotices::deliver( $id, 'team' );
		} finally {
			remove_filter( 'query', $fault );
			$email->enabled = $enabled;
			$observer->close();
		}
		$this->assertTrue( $wpdb->db_connect( false ) );
		$this->assertTrue( $fired );
		$this->assertSame( 0, $exit, $stderr );
		$this->assertTrue( $child['erased'] );
		$after = $this->notices( $id );
		$this->assertArrayNotHasKey( 'parts', $after['received'], 'The original sibling payload must not be resurrected by the stale writer.' );
		foreach ( $after as $plan ) {
			$this->assertSame( 'erased', $plan['state'] );
			$this->assertArrayNotHasKey( 'parts', $plan );
		}
		RegistrationNotices::recover();
		$this->assertSame( $after, $this->notices( $id ) );
	}

	/** A healthy writer must also reject a source erased after its policy snapshot. */
	public function test_review_policy_skip_refuses_erased_snapshot_without_connection_loss(): void {
		$post = $this->public_post( 63 );
		$this->assertFalse( apply_filters( 'woocommerce_process_registration_errors', new WP_Error(), '', $post['password'], $post['email'] )->has_errors() );
		$fail = static fn ( $old, $id, $key ) => RegistrationNotices::META === $key ? false : $old;
		add_filter( 'update_user_metadata', $fail, 10, 3 );
		try {
			$id = wc_create_new_customer( $post['email'], '', $post['password'] );
		} finally {
			remove_filter( 'update_user_metadata', $fail, 10 );
		}
		$this->assertIsInt( $id );
		$this->own_user( $id );
		$email  = WC()->mailer()->get_emails()[ NewCustomerEmail::class ];
		$erased = false;
		$erase  = static function () use ( $id, &$erased ): bool {
			$erased = RegistrationNotices::erase( $id );
			return false;
		};
		add_filter( 'woocommerce_email_enabled_' . $email->id, $erase );
		try {
			RegistrationNotices::deliver( $id, 'team' );
		} finally {
			remove_filter( 'woocommerce_email_enabled_' . $email->id, $erase );
		}
		$this->assertTrue( $erased );
		foreach ( $this->notices( $id ) as $plan ) {
			$this->assertSame( 'erased', $plan['state'] );
			$this->assertArrayNotHasKey( 'parts', $plan );
		}
	}

	/**
	 * Independent actual public workers compete while the first reservation is uncommitted.
	 *
	 * @dataProvider scarce_registration_resources
	 * @param        string $scarce_resource The last native shared resource.
	 */
	public function test_two_native_connections_cannot_create_past_count_or_bytes( string $scarce_resource ): void {
		$initial                        = $this->summary();
		$first                          = $this->public_post( 41 );
		$first[ VatProfile::VAT_META ]  = 'DE143454214';
		$first_cookie                   = $_COOKIE[ Identity::COOKIE ];
		$second                         = $this->public_post( 42 );
		$second[ VatProfile::VAT_META ] = 'DE143454214';
		$second_cookie                  = $_COOKIE[ Identity::COOKIE ];
		if ( 'count' === $scarce_resource ) {
			for ( $i = $initial['pending_users']; $i < RegistrationSlots::MAX_PENDING - 1; ++$i ) {
				$this->assertIsArray( RegistrationSlots::reserve( wp_generate_uuid4(), 1 ) );
			}
		} else {
			$bytes = RegistrationSlots::profile_bytes( $first, $first['email'], 'en_US' );
			$this->assertIsArray( RegistrationSlots::reserve( wp_generate_uuid4(), RegistrationSlots::MAX_BYTES - $initial['business_bytes'] - $bytes ) );
		}
		$barrier = tempnam( sys_get_temp_dir(), 'registration-capacity-' );
		unlink( $barrier );
		$ready = $barrier . '.ready';
		$this->later(
			static function () use ( $barrier, $ready ): void {
				if ( file_exists( $barrier ) ) {
					unlink( $barrier );
				} if ( file_exists( $ready ) ) {
					unlink( $ready );
				}
			}
		);
		$start               = static function ( array $data ): array {
			$command = array( PHP_BINARY, '-c', dirname( (string) getenv( 'LINKER_WP_ROOT' ) ) . '/php.ini', dirname( __DIR__, 2 ) . '/fixtures/registration_capacity_writer.php' );
			$process = proc_open( $command, array( array( 'pipe', 'r' ), array( 'pipe', 'w' ), array( 'pipe', 'w' ) ), $pipes );
			if ( ! is_resource( $process ) ) {
				throw new \RuntimeException( 'fixture_process_failed' );
			}
			fwrite( $pipes[0], (string) wp_json_encode( $data ) );
			fclose( $pipes[0] );
			return array( $process, $pipes );
		};
		[ $one, $one_pipes ] = $start(
			array(
				'post'    => $first,
				'cookie'  => $first_cookie,
				'address' => '192.0.2.41',
				'ready'   => $ready,
				'release' => $barrier,
			)
		);
		$until               = microtime( true ) + 10;
		while ( ! file_exists( $ready ) && microtime( true ) < $until ) {
			usleep( 20000 );
		}
		$this->assertFileExists( $ready );
		[ $two, $two_pipes ] = $start(
			array(
				'post'    => $second,
				'cookie'  => $second_cookie,
				'address' => '192.0.2.42',
			)
		);
		$loser               = json_decode( (string) stream_get_contents( $two_pipes[1] ), true );
		$two_error           = stream_get_contents( $two_pipes[2] );
		$this->assertSame( 0, proc_close( $two ), (string) $two_error );
		file_put_contents( $barrier, 'release' );
		$winner    = json_decode( (string) stream_get_contents( $one_pipes[1] ), true );
		$one_error = stream_get_contents( $one_pipes[2] );
		$this->assertSame( 0, proc_close( $one ), (string) $one_error );
		$this->assertIsArray( $winner );
		$this->assertIsArray( $loser );
		$this->assertGreaterThan( 0, $winner['created'] );
		$this->own_user( $winner['created'] );
		$this->assertSame( 1, $winner['vies_calls'] );
		$this->assertSame( 0, $loser['created'] );
		$this->assertSame( 0, $loser['vies_calls'] );
		$this->assertContains( 'linker_registration_capacity', $loser['errors'] );
		$this->assertLessThan( 2, $loser['elapsed'], 'NOWAIT must not hold a public customer behind the other transaction.' );
		$this->assertFalse( email_exists( $second['email'] ) );
		$final = $this->summary();
		$this->assertSame( $initial['pending_users'] + 1, $final['pending_users'] );
		$this->assertLessThanOrEqual( RegistrationSlots::MAX_BYTES, $final['business_bytes'] + $final['reserved_bytes'] );
		$this->assertSame( 'accepted', $winner['notices']['team']['state'] );
		$this->assertSame( 'accepted', $winner['notices']['received']['state'] );
		wp_cache_set_posts_last_changed();
		$this->assertCount( 2, self::mail_jobs_after( $this->mail_marker ) );
	}

	/**
	 * Independent count and byte envelopes.
	 *
	 * @return list<array{string}>
	 */
	public static function scarce_registration_resources(): array {
		return array( array( 'count' ), array( 'bytes' ) );
	}

	/**
	 * Native isolated user deletion also verifies no prepared body/job is stranded.
	 *
	 * @param int $id Fixture user.
	 */
	private function own_user( int $id ): void {
		$this->later(
			static function () use ( $id ): void {
				include_once ABSPATH . 'wp-admin/includes/user.php';
				wp_delete_user( $id );
			}
		);
	}

	/**
	 * Complete real public form fields and native proof, with no external calls.
	 *
	 * @param  int $number Test subject.
	 * @return array<string,string>
	 */
	private function public_post( int $number ): array {
		$start = (string) ( time() - 5 );
		$_POST = $this->request( $number ) + array(
			'billing_company'      => 'Capacity Fixture GmbH',
			'billing_first_name'   => 'Maria',
			'billing_last_name'    => 'Beispiel',
			'billing_country'      => 'DE',
			CustomerRole::META     => 'installer',
			Website::META          => 'example.test',
			VatProfile::VAT_META   => '',
			'email'                => 'capacity-' . self::tag() . '@example.test',
			'password'             => 'Native-fixture-2026!',
			'register'             => 'Register',
			'linker_started'       => $start,
			'linker_started_nonce' => wp_create_nonce( 'linker_inquiry_started_' . $start ),
		);
		return $_POST;
	}

	/**
	 * Changing all cheap identities must retain the site's registration window.
	 */
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

	/**
	 * Existing unresolved accounts and interrupted native creation share capacity.
	 */
	public function test_pending_native_accounts_and_interrupted_creation_never_expire(): void {
		$initial   = $this->summary();
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
		$this->assertSame( $remaining, $this->summary()['interrupted'] );
	}

	/**
	 * A real pending native user replaces its exact placeholder without a refund.
	 */
	public function test_only_matching_native_user_can_replace_its_placeholder(): void {
		$before = $this->summary();
		$slot   = RegistrationSlots::reserve( wp_generate_uuid4(), 2048 );
		$this->assertIsArray( $slot );
		$user = $this->customer();
		update_user_meta( $user->get_id(), Approval::STATUS_META, Approval::PENDING );
		$this->assertInstanceOf( WP_Error::class, RegistrationSlots::bind( $slot['key'], $user->get_id() ) );
		update_user_meta( $user->get_id(), RegistrationSlots::META, $slot['key'] );
		$this->assertSame( array( 'user' => $user->get_id() ), RegistrationSlots::bind( $slot['key'], $user->get_id() ) );
		$bound = $this->summary();
		$this->assertSame( $before['pending_users'] + 1, $bound['pending_users'] );
		$this->assertSame( 0, $bound['interrupted'] );
		update_user_meta( $user->get_id(), Approval::STATUS_META, Approval::RESTRICTED );
		$this->assertSame( $bound['pending_users'], $this->summary()['pending_users'] );
		update_user_meta( $user->get_id(), Approval::STATUS_META, Approval::APPROVED );
		$this->assertSame( $bound['pending_users'], $this->summary()['pending_users'], 'A status label alone is not a staff disposition.' );
		$staff = get_users(
			array(
				'role'   => 'administrator',
				'fields' => 'ID',
				'number' => 1,
			)
		);
		$this->assertNotEmpty( $staff );
		$this->as_user( (int) $staff[0] );
		$this->assertTrue( ( new Approval() )->set( $user->get_id(), Approval::REJECTED, 'Synthetic review completed.' ) );
		$this->assertSame( $before['pending_users'], $this->summary()['pending_users'] );
	}

	/**
	 * The independent byte envelope fills before the count envelope.
	 */
	public function test_pending_business_bytes_and_unknown_reservations_are_not_refunded(): void {
		$before = $this->summary();
		$room   = RegistrationSlots::MAX_BYTES - $before['business_bytes'];
		$this->assertGreaterThan( 0, $room );
		$this->assertIsArray( RegistrationSlots::reserve( wp_generate_uuid4(), $room ) );
		$this->assertInstanceOf( WP_Error::class, RegistrationSlots::reserve( wp_generate_uuid4(), 1 ) );
		$full = $this->summary();
		$this->assertSame( 1, $full['interrupted'] );
		$this->assertSame( $room, $full['reserved_bytes'] );
		$this->assertSame( RegistrationSlots::MAX_BYTES, $full['business_bytes'] + $full['reserved_bytes'] );
	}

	/**
	 * Prospective native templates read full business values without side effects.
	 */
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
