<?php
/**
 * Real public handlers, native records and optional receipt boundaries.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Tests\Fixtures\NormalMailAuthorizationFixture;

// phpcs:disable WordPress.Security.NonceVerification -- Fixture snapshots and posted data are intentionally sent to the actual native nonce/proof validators.
// phpcs:disable WordPress.PHP.DiscouragedPHPFunctions.runtime_configuration_putenv -- Isolated private env fixtures are restored in cleanup.

use Linker\Commerce\Contact\Handler as ContactHandler;
use Linker\Commerce\Contact\Form as ContactForm;
use Linker\Commerce\Inquiry\Handler;
use Linker\Commerce\Inquiry\Sender;
use Linker\Commerce\Inquiry\Statuses;
use Linker\Commerce\Contact\Submission;
use Linker\Commerce\Protection\Business;
use Linker\Commerce\Protection\Admission;
use Linker\Commerce\Protection\Configuration;
use Linker\Commerce\Protection\FormFields;
use Linker\Commerce\Protection\Allowance;
use Linker\Commerce\Protection\BusinessRecord;
use Linker\Commerce\Protection\Identity;
use Linker\Commerce\Protection\Ledger;
use Linker\Commerce\Protection\Proof;
use Linker\Commerce\Protection\ReceiptBudget;
use WC_Order;
use WP_Error;

/**
 * Native proof is established by the separately tested Siteverify controller.
 *
 * @coversNothing
 */
final class BusinessAdmissionTest extends IntegrationTestCase {

	/** Typed local service with native consumers.
	 *
	 * @var NormalMailAuthorizationFixture
	 */
	private NormalMailAuthorizationFixture $authorization;

	/**
	 * Private fixtures never use live keys or send customer mail.
	 */
	protected function setUp(): void {
		parent::setUp();
		require_once dirname( __DIR__, 2 ) . '/fixtures/NormalMailAuthorizationFixture.php';
		$this->authorization = NormalMailAuthorizationFixture::install(
			function ( callable $remove ): void {
				$this->later( $remove );
			}
		);
		$this->as_user( 0 );
		$old    = get_option( Ledger::OPTION );
		$review = get_option( \Linker\Commerce\Protection\IntakeStore::OPTION );
		delete_option( \Linker\Commerce\Protection\IntakeStore::OPTION );
		delete_option( Ledger::OPTION );
		$cookie                      = $_COOKIE; // phpcs:ignore WordPress.Security.NonceVerification -- Restore the fixture request.
		$_COOKIE[ Identity::COOKIE ] = str_repeat( 'b', 32 );
		$settings                    = array(
			'LINKER_PUBLIC_PROTECTION_MODE' => 'enforce',
			'LINKER_TURNSTILE_SITE_KEY'     => '1x00000000000000000000AA',
			'LINKER_TURNSTILE_SECRET_KEY'   => '1x0000000000000000000000000000000AA',
			'LINKER_TURNSTILE_HOSTNAME'     => 'localhost',
		);
		$env                         = array();
		foreach ( $settings as $key => $value ) {
			$env[ $key ] = getenv( $key );
			putenv( $key . '=' . $value );
		}
		$this->later(
			static function () use ( $env, $old, $cookie, $review ): void {
				foreach ( $env as $key => $value ) {
					putenv( false === $value ? $key : $key . '=' . $value );
				}
				delete_option( Ledger::OPTION );
				if ( false !== $old ) {
					update_option( Ledger::OPTION, $old, false );
				}
				delete_option( \Linker\Commerce\Protection\IntakeStore::OPTION );
				if ( false !== $review ) {
					update_option( \Linker\Commerce\Protection\IntakeStore::OPTION, $review, false );
				}
				$_COOKIE = $cookie;
			}
		);
		wc_load_cart();
		WC()->cart->empty_cart();
		$this->later( static fn () => WC()->cart->empty_cart() );
	}

	/** Unknown dispatched writes stay recoverable; definite refusals return to a fresh check. */
	public function test_native_recovery_pages_preserve_unknown_dispatch_without_looping_definite_refusals(): void {
		$identity = Identity::current();
		$this->assertInstanceOf( Identity::class, $identity );
		foreach ( array( 'contact', 'inquiry' ) as $action ) {
			foreach ( array( 'reserved', 'dispatched', 'unresolved', 'completed' ) as $status ) {
				$id      = wp_generate_uuid4();
				$payload = array(
					'fixture' => self::tag(),
					'email'   => 'native-recovery@example.test',
				);
				$fp      = \Linker\Commerce\Protection\Fingerprint::make( $identity, $action, $payload );
				$this->assertIsString( $fp );
				$at     = time() - ( 'unresolved' === $status ? 121 : 0 );
				$ledger = new Ledger( static fn (): int => $at );
				$this->assertIsArray( $ledger->reserve( $id, $fp, array( new Allowance( 'fixture_recovery', $identity->browser, 100, HOUR_IN_SECONDS ) ), 120, array(), $action, $identity->binding() ) );
				if ( 'reserved' !== $status ) {
					$this->assertIsArray( $ledger->dispatch( $id, $fp ) );
				}
				if ( 'completed' === $status ) {
					$this->assertIsArray( $ledger->complete( $id, $fp, 0 ) );
				}
				$called  = false;
				$work    = static function () use ( &$called ): WP_Error {
					$called = true;
					return new WP_Error( 'unexpected_fixture_write' );
				};
				$unknown = Business::run(
					$action,
					array(
						'linker_request_id' => $id,
						'linker_proof'      => '',
					),
					$payload,
					$work
				);
				$this->assertInstanceOf( WP_Error::class, $unknown );
				$this->assertSame( 'linker_inquiry_pending', $unknown->get_error_code(), $action . ':' . $status );
				$this->assertFalse( $called );
			}
			$fresh = Business::run(
				$action,
				array(
					'linker_request_id' => wp_generate_uuid4(),
					'linker_proof'      => '',
				),
				$payload,
				$work
			);
			$this->assertInstanceOf( WP_Error::class, $fresh );
			$this->assertSame( 'linker_admission_proof', $fresh->get_error_code() );
		}
	}

	/** Actual native redirects preserve pending recovery and clear definite refusals on the next page. */
	public function test_both_native_handlers_restore_pending_and_return_definite_refusals_to_verification(): void {
		$original_post       = $_POST;
		$original_cookies    = $_COOKIE;
		$original_shortcodes = $GLOBALS['shortcode_tags'];
		$original_session    = array();
		foreach ( array( 'linker_form_recovery_contact', 'linker_inquiry_fields', 'linker_inquiry_error', 'linker_inquiry_error_locale', 'linker_intake_grouped' ) as $key ) {
			$original_session[ $key ] = WC()->session->get( $key );
		}
		$this->later(
			static function () use ( $original_post, $original_cookies, $original_shortcodes, $original_session ): void {
				$_POST                     = $original_post;
				$_COOKIE                   = $original_cookies;
				$GLOBALS['shortcode_tags'] = $original_shortcodes;
				foreach ( $original_session as $key => $value ) {
					WC()->session->set( $key, $value );
				}
			}
		);
		$stop_redirect = static function ( string $location ): string {
			if ( str_starts_with( $location, home_url() ) ) {
				throw new \RuntimeException( 'fixture_native_recovery_redirect' );
			}
			return $location;
		};
		foreach ( array( 'contact', 'inquiry' ) as $action ) {
			foreach ( array( 'pending', 'refused' ) as $outcome ) {
				$post = $this->post( $action );
				if ( 'pending' === $outcome ) {
					$identity = Identity::current();
					$this->assertInstanceOf( Identity::class, $identity );
					$details = Submission::from_post( $post, 'contact' === $action );
					$this->assertInstanceOf( Submission::class, $details );
					$payload = 'contact' === $action ? get_object_vars( $details ) : array(
						'details' => get_object_vars( $details ),
						'billing' => \Linker\Commerce\Inquiry\BillingFields::values( $post ),
						'draft'   => $post['linker_draft_hash'],
					);
					$fp      = \Linker\Commerce\Protection\Fingerprint::make( $identity, $action, $payload );
					$this->assertIsString( $fp );
					$ledger = new Ledger();
					$this->assertIsArray( $ledger->reserve( $post['linker_request_id'], $fp, array( new Allowance( 'fixture_redirect_recovery', $identity->browser, 100, HOUR_IN_SECONDS ) ), 120, array(), $action, $identity->binding() ) );
					$this->assertIsArray( $ledger->dispatch( $post['linker_request_id'], $fp ) );
					$post['linker_proof'] = '';
				} elseif ( 'inquiry' === $action ) {
					$post['message'] = '';
				} else {
					$post['linker_proof'] = '';
				}
				$_POST = $post;
				add_filter( 'wp_redirect', $stop_redirect, PHP_INT_MAX );
				try {
					( 'contact' === $action ? new ContactHandler() : new Handler() )->handle();
					$this->fail( 'The native redirect must be intercepted before exit.' );
				} catch ( \RuntimeException $redirect ) {
					$this->assertSame( 'fixture_native_recovery_redirect', $redirect->getMessage() );
				} finally {
					remove_filter( 'wp_redirect', $stop_redirect, PHP_INT_MAX );
				}
				$_COOKIE['wp_woocommerce_session_fixture'] = 'local-session-present';
				if ( 'contact' === $action ) {
					$stored = WC()->session->get( 'linker_form_recovery_contact' )['fields'];
					$html   = ( new ContactForm() )->render();
				} else {
					$stored = WC()->session->get( 'linker_inquiry_fields' );
					$form   = new \Linker\Commerce\Inquiry\Form();
					$form->register();
					$html = $form->render();
				}
				$this->assertSame( $post['linker_request_id'], $stored['linker_request_id'] );
				$this->assertSame( 'pending' === $outcome ? '1' : '0', $stored['linker_recovery_available'], $action . ':' . $outcome );
				$this->assertSame( 'pending' === $outcome, str_contains( $html, 'data-linker-protection-recovery="true"' ), $action . ':' . $outcome );
				$this->assertSame( array(), wc_get_orders( array( 'billing_email' => $post['email'] ) ) );
			}
		}
	}


	/**
	 * A customer who edits a message after an unconfirmed result must be able to
	 * send it: the journal refuses the old UUID on every attempt, so the native
	 * form is given a new one instead of resubmitting it forever.
	 */
	public function test_a_changed_message_after_an_unconfirmed_result_can_be_sent_again(): void {
		$this->optional_business_verification();
		$original_post       = $_POST;
		$original_cookies    = $_COOKIE;
		$original_shortcodes = $GLOBALS['shortcode_tags'];
		$original_session    = array();
		foreach ( array( 'linker_form_recovery_contact', 'linker_inquiry_fields', 'linker_inquiry_error', 'linker_inquiry_error_locale', 'linker_intake_grouped' ) as $key ) {
			$original_session[ $key ] = WC()->session->get( $key );
		}
		$this->later(
			static function () use ( $original_post, $original_cookies, $original_shortcodes, $original_session ): void {
				$_POST                     = $original_post;
				$_COOKIE                   = $original_cookies;
				$GLOBALS['shortcode_tags'] = $original_shortcodes;
				foreach ( $original_session as $key => $value ) {
					WC()->session->set( $key, $value );
				}
			}
		);
		$stop_redirect = static function ( string $location ): string {
			if ( str_starts_with( $location, home_url() ) ) {
				throw new \RuntimeException( 'fixture_changed_input_redirect' );
			}
			return $location;
		};
		foreach ( array( 'contact', 'inquiry' ) as $action ) {
			$post     = $this->post( $action );
			$original = $post['linker_request_id'];
			// The journal already answered this UUID for the sender's earlier text.
			$identity = Identity::current();
			$this->assertInstanceOf( Identity::class, $identity );
			$ledger = new Ledger();
			$this->assertIsArray( $ledger->reserve( $original, hash( 'sha256', 'earlier-input-' . self::tag() ), array( new Allowance( 'fixture_changed_input', $identity->browser, 100, HOUR_IN_SECONDS ) ), 120, array(), $action, $identity->binding() ) );
			// The customer then edits the question and sends again from the native form.
			$post['message']     .= ' Additional detail.';
			$post['linker_proof'] = '';
			$_POST                = $post;
			add_filter( 'wp_redirect', $stop_redirect, PHP_INT_MAX );
			try {
				( 'contact' === $action ? new ContactHandler() : new Handler() )->handle();
				$this->fail( 'The native redirect must be intercepted before exit.' );
			} catch ( \RuntimeException $redirect ) {
				$this->assertSame( 'fixture_changed_input_redirect', $redirect->getMessage() );
			} finally {
				remove_filter( 'wp_redirect', $stop_redirect, PHP_INT_MAX );
			}
			$_COOKIE['wp_woocommerce_session_fixture'] = 'local-session-present';
			if ( 'contact' === $action ) {
				$stored = WC()->session->get( 'linker_form_recovery_contact' )['fields'];
				$html   = ( new ContactForm() )->render();
			} else {
				$stored = WC()->session->get( 'linker_inquiry_fields' );
				$form   = new \Linker\Commerce\Inquiry\Form();
				$form->register();
				$html = $form->render();
			}
			$this->assertSame( '', $stored['linker_request_id'], $action . ': the refused UUID is not offered again' );
			$this->assertSame( '0', $stored['linker_recovery_available'], $action . ': a changed-input refusal needs a fresh proof' );
			$this->assertSame( 'Please provide product guidance. Additional detail.', $stored['message'], $action . ': the edited text stays' );
			$this->assertStringNotContainsString( 'data-linker-protection-recovery="true"', $html, $action );
			$this->assertSame( 1, preg_match( '/name="linker_request_id" value="([0-9a-f-]{36})"/', $html, $fresh ), $action . ': the native form still carries a request id' );
			$replacement = $fresh[1] ?? '';
			$this->assertNotSame( $original, $replacement, $action . ': the replaced UUID is new' );
			$this->assertTrue( wp_is_uuid( $replacement, 4 ), $action . ': the replacement is a native UUID' );
			$this->assertSame( array(), wc_get_orders( array( 'billing_email' => $post['email'] ) ), $action );
		}
	}

	/** An unreadable journal is not evidence that an old native request was refused. */
	public function test_native_recovery_lookup_storage_failure_preserves_unknown_result(): void {
		$switched = switch_to_locale( 'de_DE_formal' );
		$this->assertSame( 'de_DE_formal', get_locale() );
		load_textdomain( 'linker-commerce', dirname( __DIR__, 3 ) . '/languages/linker-commerce-de_DE_formal.mo', 'de_DE_formal' );
		$old = get_option( Ledger::OPTION );
		update_option( Ledger::OPTION, 'invalid-fixture-journal', false );
		$called = false;
		try {
			$result = Business::run(
				'inquiry',
				array(
					'linker_request_id' => wp_generate_uuid4(),
					'linker_proof'      => '',
				),
				array( 'fixture' => self::tag() ),
				static function () use ( &$called ): WP_Error {
					$called = true;
					return new WP_Error( 'unexpected_fixture_write' );
				}
			);
			$this->assertInstanceOf( WP_Error::class, $result );
			$this->assertSame( 'linker_admission_storage', $result->get_error_code() );
			$this->assertSame( 'Der Status Ihrer Anfrage lässt sich derzeit nicht bestätigen. Bitte prüfen Sie ihn, bevor Sie die Anfrage erneut senden.', $result->get_error_message() );
			$this->assertTrue( \Linker\Commerce\Protection\FormRecovery::after_error( $result ) );
			$this->assertFalse( $called );
		} finally {
			if ( $switched ) {
				restore_previous_locale();
			}
			if ( false === $old ) {
				delete_option( Ledger::OPTION );
			} else {
				update_option( Ledger::OPTION, $old, false );
			}
		}
	}


	/**
	 * One native form attempt, immediately after autofill without a fake clock.
	 *
	 * @param  string $action Native action.
	 * @return array<string,string>
	 */
	private function post( string $action = 'inquiry' ): array {
		$identity = Identity::current();
		$this->assertInstanceOf( Identity::class, $identity );
		$challenge = wp_generate_uuid4();
		$fp        = hash( 'sha256', $challenge );
		$ledger    = new Ledger();
		$this->assertIsArray( $ledger->reserve( $challenge, $fp, array( new Allowance( 'fixture_verify', $identity->browser, 100, HOUR_IN_SECONDS ) ), 10, array(), 'verification_' . $action, $identity->binding() ) );
		$this->assertIsArray( $ledger->dispatch( $challenge, $fp ) );
		$this->assertIsArray( $ledger->complete( $challenge, $fp, 1 ) );
		$started = (string) time();
		return array(
			'linker_started'       => $started,
			'linker_started_nonce' => wp_create_nonce( 'linker_inquiry_started_' . $started ),
			'name'                 => 'Fixture Installer',
			'email'                => 'fixture-' . self::tag() . '@example.test',
			'company'              => 'Fixture Company',
			'message'              => 'Please provide product guidance.',
			'consent'              => '1',
			'linker_request_id'    => wp_generate_uuid4(),
			'linker_proof'         => ( new Proof() )->issue( 'verified', $action, $identity, $challenge ),
			'linker_inquiry_nonce' => wp_create_nonce( Handler::ACTION ),
			'linker_contact_nonce' => wp_create_nonce( ContactForm::NONCE_ACTION ),
			'linker_draft_hash'    => WC()->cart->get_cart_hash(),
		);
	}

	/** Private rollout choice is restored after every fixture. */
	private function optional_business_verification(): void {
		$old = getenv( 'LINKER_BUSINESS_VERIFICATION' );
		putenv( 'LINKER_BUSINESS_VERIFICATION=optional' );
		$this->later(
			static function () use ( $old ): void {
				putenv( false === $old ? 'LINKER_BUSINESS_VERIFICATION' : 'LINKER_BUSINESS_VERIFICATION=' . $old );
			}
		);
	}

	/** Both actual business writers remain idempotent without any widget/key. */
	public function test_optional_business_verification_preserves_native_records_and_retries_without_keys(): void {
		$this->optional_business_verification();
		$keys = array( 'LINKER_TURNSTILE_SITE_KEY', 'LINKER_TURNSTILE_SECRET_KEY' );
		foreach ( $keys as $key ) {
			$old = getenv( $key );
			putenv( $key );
			$this->later(
				static function () use ( $old, $key ): void {
					putenv( false === $old ? $key : $key . '=' . $old );
				}
			);
		}
		foreach ( array( 'contact', 'inquiry' ) as $action ) {
			$post                 = $this->post( $action );
			$post['linker_proof'] = '';
			$send                 = 'contact' === $action ? new ContactHandler() : new Handler();
			$first                = $send->process( $post );
			$this->assertFalse( is_wp_error( $first ) );
			$orders = wc_get_orders( array( 'billing_email' => $post['email'] ) );
			$this->assertIsArray( $orders );
			$this->assertCount( 1, $orders );
			$order = $orders[0];
			$this->later(
				static function () use ( $order ): void {
					$order->delete( true );
				}
			);
			$this->assertSame( Statuses::RECEIVED, $order->get_status() );
			$this->assertSame( 0, $order->get_customer_id() );
			$this->assertSame( $post['linker_request_id'], $order->get_meta( BusinessRecord::REQUEST ) );
			$this->assertFalse( is_wp_error( $send->process( $post ) ) );
			$retry = wc_get_orders( array( 'billing_email' => $post['email'] ) );
			$this->assertIsArray( $retry );
			$this->assertCount( 1, $retry );
			$this->assertStringNotContainsString( '<noscript>', FormFields::render( $action ) );
		}
	}

	/** Optional challenge never changes the enforced shared submission budget. */
	public function test_optional_business_verification_still_enforces_atomic_quota(): void {
		$this->optional_business_verification();
		$limit = static fn ( array $limits, string $action, Identity $identity ): array => array_merge( $limits, array( new Allowance( 'optional_fixture', $identity->browser, 1, HOUR_IN_SECONDS ) ) );
		add_filter( 'linker_commerce_public_business_limits', $limit, 99, 3 );
		$this->later(
			static function () use ( $limit ): void {
				remove_filter( 'linker_commerce_public_business_limits', $limit, 99 );
			}
		);
		$first                 = $this->post( 'contact' );
		$first['linker_proof'] = '';
		$this->assertSame( 'saved_review', ( new ContactHandler() )->process( $first ) );
		$orders = wc_get_orders( array( 'billing_email' => $first['email'] ) );
		$this->assertIsArray( $orders );
		$order = $orders[0];
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		$second                 = $this->post( 'contact' );
		$second['linker_proof'] = '';
		$this->assertSame( 'throttled', ( new ContactHandler() )->process( $second ) );
		$this->assertSame( array(), wc_get_orders( array( 'billing_email' => $second['email'] ) ) );
	}

	/** Native input guards and all non-business proof requirements stay intact. */
	public function test_optional_business_verification_preserves_native_guards_and_other_action_proofs(): void {
		$this->optional_business_verification();
		$post                 = $this->post( 'contact' );
		$post['linker_proof'] = '';
		foreach ( array( array( 'website' => 'https://spam.example.test' ), array( 'linker_contact_nonce' => 'forged' ), array( 'linker_started_nonce' => 'forged' ) ) as $bad ) {
			$this->assertSame( 'invalid', ( new ContactHandler() )->process( array_replace( $post, $bad ) ) );
		}
		$this->assertSame( array(), wc_get_orders( array( 'billing_email' => $post['email'] ) ) );
		foreach ( array( 'genie', 'genie_contact', 'genie_inquiry', 'draft_write', 'registration', 'password_reset', 'login', 'comment' ) as $action ) {
			$this->assertTrue( Configuration::verification_required( $action ) );
			$permit = ( new Admission( Configuration::current() ) )->reserve( $action, '', wp_generate_uuid4(), array(), array(), 10 );
			$this->assertInstanceOf( WP_Error::class, $permit );
			$this->assertSame( 'linker_admission_proof', $permit->get_error_code() );
		}
	}

	/**
	 * A valid proof replaces the old fixed delay and three-per-connection limit.
	 */
	public function test_fast_validated_customers_share_a_nat_without_the_old_three_message_limit(): void {
		for ( $i = 0; $i < 4; ++$i ) {
			$post = $this->post( 'contact' );
			$this->assertSame( 'sent', ( new ContactHandler() )->process( $post ) );
			$orders = wc_get_orders( array( 'billing_email' => $post['email'] ) );
			$this->assertIsArray( $orders );
			$this->assertCount( 1, $orders );
			$order = $orders[0];
			$this->later(
				static function () use ( $order ): void {
					$order->delete( true );
				}
			);
			$this->assertSame( $post['linker_request_id'], $order->get_meta( BusinessRecord::REQUEST ) );
		}
	}

	/**
	 * Optional policy preserves a held inquiry; native nonce failures still create none.
	 */
	public function test_invalid_proofs_save_held_inquiry_while_bad_nonce_has_no_side_effects(): void {
		$this->optional_business_verification();
		$marker = self::newest_mail_job();
		$post   = $this->post();
		$this->assertInstanceOf( WP_Error::class, ( new Handler() )->process( array_replace( $post, array( 'linker_inquiry_nonce' => 'forged' ) ) ) );
		$this->assertSame( array(), wc_get_orders( array( 'billing_email' => $post['email'] ) ) );
		foreach ( array( '', 'forged' ) as $proof ) {
			$order = ( new Handler() )->process( array_replace( $post, array( 'linker_proof' => $proof ) ) );
			$this->assertInstanceOf( WC_Order::class, $order );
			$this->assertTrue( \Linker\Commerce\Mail\NotificationHold::held( $order ) );
			$this->later(
				static function () use ( $order ): void {
					$order->delete( true );
				}
			);
		}
		$orders = wc_get_orders(
			array(
				'billing_email' => $post['email'],
				'limit'         => 10,
			)
		);
		$this->assertIsArray( $orders );
		$this->assertCount( 1, $orders );
		$this->assertSame( array(), self::mail_jobs_after( $marker ) );
	}

	/**
	 * Verified autofill keeps the native signature and empty honeypot checks.
	 */
	public function test_verified_submission_still_rejects_filled_traps_and_forged_starts(): void {
		$post   = $this->post( 'contact' );
		$marker = self::newest_mail_job();
		foreach ( array( array( 'website' => 'https://spam.example.test' ), array( 'linker_started_nonce' => 'forged' ) ) as $bad ) {
			$this->assertSame( 'invalid', ( new ContactHandler() )->process( array_replace( $post, $bad ) ) );
		}
		$this->assertSame( array(), wc_get_orders( array( 'billing_email' => $post['email'] ) ) );
		$this->assertSame( array(), self::mail_jobs_after( $marker ) );
	}

	/**
	 * An ordinary correctable empty message consumes no business proof/UUID.
	 */
	public function test_empty_inquiry_can_be_corrected_with_the_same_logical_request(): void {
		$post  = array_replace( $this->post(), array( 'message' => '' ) );
		$error = ( new Handler() )->process( $post );
		$this->assertInstanceOf( WP_Error::class, $error );
		$this->assertSame( 'linker_inquiry_empty', $error->get_error_code() );
		$this->assertStringNotContainsString( $post['linker_request_id'], (string) get_option( Ledger::OPTION ) );
		$post['message'] = 'A corrected ordinary inquiry.';
		$order           = ( new Handler() )->process( $post );
		$this->assertInstanceOf( WC_Order::class, $order );
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		$this->assertSame( 'A corrected ordinary inquiry.', $order->get_customer_note() );
	}

	/**
	 * Native retired checkout never updates customer/session details.
	 */
	public function test_retired_checkout_stops_before_its_native_session_update(): void {
		$product = $this->product( '125' );
		WC()->cart->add_to_cart( $product->get_id(), 1 );
		$post    = $_POST;
		$request = $_REQUEST;
		$this->later(
			static function () use ( $post, $request ): void {
				$_POST    = $post;
				$_REQUEST = $request;
			}
		);
		$country  = WC()->customer->get_billing_country();
		$_POST    = array(
			'billing_country' => 'FR',
			'billing_email'   => 'unverified@example.test',
			'payment_method'  => 'linker_proforma',
		);
		$_REQUEST = array_merge( $_POST, array( 'woocommerce-process-checkout-nonce' => wp_create_nonce( 'woocommerce-process_checkout' ) ) );
		WC()->checkout()->process_checkout();
		$this->assertSame( $country, WC()->customer->get_billing_country() );
		$this->assertSame( 1, WC()->cart->get_cart_contents_count() );
	}

	/** Native stock refusal retains the draft and leaves ordinary retry unspent. */
	public function test_stock_preflight_keeps_the_same_request_retryable(): void {
		$product = $this->product( '125' );
		$key     = WC()->cart->add_to_cart( $product->get_id(), 1 );
		$this->assertIsString( $key );
		$post = $this->post();
		$line = WC()->cart->get_cart_item( $key );
		$line['data']->set_stock_status( 'outofstock' );
		$error = ( new Handler() )->process( $post );
		$this->assertInstanceOf( WP_Error::class, $error );
		$this->assertSame( 'out-of-stock', $error->get_error_code() );
		$this->assertSame( 1, WC()->cart->get_cart_contents_count() );
		$this->assertStringNotContainsString( $post['linker_request_id'], (string) get_option( Ledger::OPTION ) );
		$line['data']->set_stock_status( 'instock' );
		$order = ( new Handler() )->process( $post );
		$this->assertInstanceOf( WC_Order::class, $order );
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
	}

	/** Unverified registration receipt names the address use, not a supposed sender. */
	public function test_native_registration_receipt_does_not_claim_the_recipient_registered(): void {
		$customer = $this->customer();
		$email    = WC()->mailer()->get_emails()[ \Linker\Commerce\Registration\Emails\RegistrationReceivedEmail::class ];
		$this->assertInstanceOf( \Linker\Commerce\Registration\Emails\RegistrationReceivedEmail::class, $email );
		$original = $email->object;
		$this->later(
			static function () use ( $email, $original ): void {
				$email->object = $original;
			}
		);
		$email->object = get_userdata( $customer->get_id() );
		$body          = $email->get_content_html();
		$this->assertSame( 'Registration received', $email->get_default_subject() );
		$this->assertStringContainsString( 'A partner registration was submitted using this email address.', $body );
		$this->assertStringContainsString( 'you can ignore this email', $body );
		$this->assertStringNotContainsString( 'your partner registration', $body );
		$this->assertStringNotContainsString( 'your partner account', $body );
	}

	/**
	 * Completed browser retry returns the same native order after the cart was emptied.
	 */
	public function test_native_inquiry_retry_is_idempotent_and_payload_changes_are_refused(): void {
		$product = $this->product( '125' );
		WC()->cart->add_to_cart( $product->get_id(), 2 );
		$post  = $this->post();
		$first = ( new Handler() )->process( $post );
		$this->assertInstanceOf( WC_Order::class, $first );
		$this->later(
			static function () use ( $first ): void {
				$first->delete( true );
			}
		);
		$marker = self::newest_mail_job();
		$this->assertTrue( WC()->cart->is_empty() );
		$retry = ( new Handler() )->process( $post );
		$this->assertInstanceOf( WC_Order::class, $retry );
		$this->assertSame( $first->get_id(), $retry->get_id() );
		$this->assertSame( array(), self::mail_jobs_after( $marker ) );
		$this->assertInstanceOf( WP_Error::class, ( new Handler() )->process( array_replace( $post, array( 'message' => 'Different submission.' ) ) ) );
		$_COOKIE[ Identity::COOKIE ] = str_repeat( 'c', 32 );
		$this->assertInstanceOf( WP_Error::class, ( new Handler() )->process( $post ) );
	}

	/**
	 * A native received record survives loss of the final ledger acknowledgement.
	 */
	public function test_received_native_record_recovers_without_repeating_the_writer(): void {
		$post    = $this->post( 'contact' );
		$details = Submission::from_post( $post );
		$this->assertInstanceOf( Submission::class, $details );
		$original = null;
		try {
			Business::run(
				'contact',
				$post,
				get_object_vars( $details ),
				function () use ( $details, &$original ): WC_Order {
					$original = ( new Sender() )->message( $details );
					throw new \RuntimeException( 'Synthetic crash after native save before final journal completion.' );
				}
			);
		} catch ( \RuntimeException $error ) {
			$this->assertStringContainsString( 'Synthetic crash', $error->getMessage() );
		}
		$this->assertInstanceOf( WC_Order::class, $original );
		$this->later(
			static function () use ( $original ): void {
				$original->delete( true );
			}
		);
		$marker = self::newest_mail_job();
		$retry  = Business::run(
			'contact',
			$post,
			get_object_vars( $details ),
			static function (): WP_Error {
				self::fail( 'Recovered native result must not repeat the writer.' );
			}
		);
		$this->assertInstanceOf( WC_Order::class, $retry );
		$this->assertSame( $original->get_id(), $retry->get_id() );
		$this->assertSame( Statuses::RECEIVED, $retry->get_status() );
		$this->assertSame( array(), self::mail_jobs_after( $marker ) );
	}

	/**
	 * Woo and WordPress both stop before reset key creation when proof is absent.
	 */
	public function test_both_native_password_reset_paths_require_proof_before_key_and_mail(): void {
		$customer = $this->customer();
		$user     = get_userdata( $customer->get_id() );
		$this->assertInstanceOf( \WP_User::class, $user );
		$before = $user->user_activation_key;
		$post   = $_POST;
		$this->later(
			static function () use ( $post ): void {
				$_POST = $post;
			}
		);
		$_POST  = array( 'user_login' => $user->user_email );
		$marker = self::newest_mail_job();
		$this->assertFalse( \WC_Shortcode_My_Account::retrieve_password() );
		$this->assertInstanceOf( WP_Error::class, retrieve_password( $user->user_email ) );
		$loaded = get_userdata( $user->ID );
		$this->assertInstanceOf( \WP_User::class, $loaded );
		$this->assertSame( $before, $loaded->user_activation_key );
		$this->assertSame( array(), self::mail_jobs_after( $marker ) );
		$_POST = array_merge(
			$this->post( 'password_reset' ),
			array(
				'user_login'                  => $user->user_email,
				'linker_password_reset_nonce' => wp_create_nonce( 'linker_password_reset' ),
			)
		);
		$this->assertTrue( \WC_Shortcode_My_Account::retrieve_password() );
		$loaded = get_userdata( $user->ID );
		$this->assertInstanceOf( \WP_User::class, $loaded );
		$this->assertNotSame( $before, $loaded->user_activation_key );
		$this->assertFalse( \WC_Shortcode_My_Account::retrieve_password(), 'Repeated UUID cannot generate another reset key/email.' );
	}

	/** Real Woo session and render hooks restore only the failed reset login. */
	public function test_password_reset_recovery_renders_only_the_saved_login_inside_the_card(): void {
		$session_key = 'linker_form_recovery_password_reset';
		$previous    = WC()->session->get( $session_key );
		$this->later( static fn () => WC()->session->set( $session_key, $previous ) );
		$post = $_POST;
		$this->later(
			static function () use ( $post ): void {
				$_POST = $post;
			}
		);
		$_COOKIE['wp_woocommerce_session_recovery_fixture'] = 'native-presence';
		// An earlier failed attempt cannot follow a new non-failing submission.
		\Linker\Commerce\Protection\FormRecovery::save(
			'password_reset',
			array( 'user_login' => 'previous@example.test' )
		);
		$_POST = array(
			'wc_reset_password' => 'true',
			'user_login'        => '<b>installer@example.test</b>',
			'password_1'        => 'never-store-password',
			'reset_key'         => 'never-store-key',
			'linker_proof'      => 'never-store-proof',
		);
		$this->assertNotFalse( has_action( 'lostpassword_post', array( \Linker\Commerce\Mail\ResetNotice::class, 'capture_submission' ) ) );
		\Linker\Commerce\Mail\ResetNotice::capture_submission( new WP_Error(), new \WP_User() );
		$this->assertNull( WC()->session->get( $session_key ), 'A non-failing attempt neither saves the new login nor leaves the earlier retry.' );

		// A first-time visitor's newly set cookie is not in this request yet.
		unset( $_COOKIE['wp_woocommerce_session_recovery_fixture'] );
		\Linker\Commerce\Mail\ResetNotice::capture_submission( new WP_Error( 'fixture', 'Synthetic failure' ), new \WP_User() );
		$saved = WC()->session->get( $session_key, array() );
		$this->assertIsArray( $saved );
		$this->assertSame( array( 'user_login' => 'installer@example.test' ), $saved['fields'] );

		$notice = static function (): void {
			echo '<div class="woocommerce-error">Synthetic retry notice</div>';
		};
		add_action( 'woocommerce_before_lost_password_form', $notice ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound, WooCommerce.Commenting.CommentHooks.MissingHookComment -- Fixture output at Woo's native hook.
		$this->later(
			static function () use ( $notice ): void {
				remove_action( 'woocommerce_before_lost_password_form', $notice );
			}
		);
		$this->assertNotFalse( has_action( 'woocommerce_before_lost_password_form', array( \Linker\Commerce\Mail\ResetNotice::class, 'render_begin' ) ) );
		$this->assertNotFalse( has_action( 'woocommerce_after_lost_password_form', array( \Linker\Commerce\Mail\ResetNotice::class, 'render_end' ) ) );
		ob_start();
		require dirname( __DIR__, 3 ) . '/templates/myaccount/auth/form-lost-password.php';
		$html = (string) ob_get_clean();

		$this->assertMatchesRegularExpression( '/<section class="linker-auth-card"[^>]*>.*Synthetic retry notice.*name="user_login"/s', $html );
		$processor = new \WP_HTML_Tag_Processor( $html );
		$found     = false;
		while ( $processor->next_tag( array( 'tag_name' => 'INPUT' ) ) ) {
			if ( 'user_login' === $processor->get_attribute( 'name' ) ) {
				$this->assertSame( 'installer@example.test', $processor->get_attribute( 'value' ) );
				$found = true;
				break;
			}
		}
		$this->assertTrue( $found );
		$this->assertNull( WC()->session->get( $session_key ), 'The session value is consumed once.' );
	}

	/**
	 * Woo's real four-argument filter must use email, never its password argument.
	 */
	public function test_native_woocommerce_registration_binds_validated_email_without_the_password(): void {
		$post = $_POST;
		$this->later(
			static function () use ( $post ): void {
				$_POST = $post;
			}
		);
		$_POST  = array_merge(
			$this->post( 'registration' ),
			array(
				'billing_first_name'     => 'Fixture',
				'billing_last_name'      => 'Installer',
				'billing_company'        => 'Fixture Company',
				'billing_country'        => 'DE',
				'linker_customer_role'   => 'installer',
				'linker_company_website' => 'https://example.test',
			)
		);
		$email  = sanitize_email( wp_unslash( $_POST['email'] ?? '' ) );
		$errors = apply_filters( 'woocommerce_process_registration_errors', new WP_Error(), '', 'SyntheticPasswordNeverPartOfPayload', $email ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound, WooCommerce.Commenting.CommentHooks.MissingHookComment -- Actual native Woo four-argument registration boundary.
		$this->assertInstanceOf( WP_Error::class, $errors );
		$this->assertFalse( $errors->has_errors(), implode( ';', $errors->get_error_messages() ) );
		$owned = ( new Ledger() )->privacy( array( \Linker\Commerce\Protection\Allowance::owner_for( Identity::recipient( $email ) ) ), false );
		$this->assertIsArray( $owned );
		$this->assertSame( 'registration', $owned['data'][0]['purpose'] );
		$this->assertStringNotContainsString( 'SyntheticPasswordNeverPartOfPayload', (string) get_option( Ledger::OPTION ) );
		$this->assertFalse( email_exists( $email ), 'Validation alone creates no account or registration mail.' );
		$id = wc_create_new_customer( $email, '', 'SyntheticPasswordNeverPartOfPayload' );
		$this->assertIsInt( $id );
		$this->assertGreaterThan( 0, $id );
		$this->later(
			static function () use ( $id ): void {
				require_once ABSPATH . 'wp-admin/includes/user.php';
				wp_delete_user( $id );
			}
		);
		$owned = ( new Ledger() )->privacy( array( Allowance::owner_for( Identity::recipient( $email ) ) ), false );
		$this->assertIsArray( $owned );
		$this->assertSame( 'completed', $owned['data'][0]['status'] );
		$this->assertSame( $id, $owned['data'][0]['outcome'] );
	}

	/**
	 * Core registration cannot create an account through its direct helper without proof.
	 */
	public function test_wordpress_registration_cannot_bypass_the_native_account_gate(): void {
		$post = $_POST;
		$this->later(
			static function () use ( $post ): void {
				$_POST = $post;
			}
		);
		$_POST  = array();
		$tag    = self::tag();
		$email  = 'native-' . $tag . '@example.test';
		$result = register_new_user( 'native-' . $tag, $email );
		$this->assertInstanceOf( WP_Error::class, $result );
		$this->assertFalse( email_exists( $email ) );
	}

	/**
	 * Optional customer receipt is fixed; every actual message retains team notification.
	 */
	public function test_target_receipt_cap_retains_normal_business_and_complete_authorized_receipts(): void {
		$target = 'same-target-' . self::tag() . '@example.test';
		delete_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION );
		update_option( \Linker\Commerce\Mail\Throttle::OPTION, array_fill( 0, \Linker\Commerce\Mail\Throttle::PER_MINUTE, time() ), false );
		$store = new \Linker\Commerce\Mail\JobStore();
		for ( $i = 0; $i < 3; ++$i ) {
			$post   = array_replace(
				$this->post( 'contact' ),
				array(
					'email'   => $target,
					'name'    => 'InstallerFixtureName',
					'message' => 'Please quote three compatible inverters. https://example.test/product',
				)
			);
			$marker = self::newest_mail_job();
			$this->assertSame( 'sent', ( new ContactHandler() )->process( $post ), 'Receipt admission follows the background verdict.' );
			$this->authorization->drain();
			$jobs = array_map( static fn ( int $id ) => $store->load( $id ), self::mail_jobs_after( $marker ) );
			$this->assertCount( 2 === $i ? 1 : 2, $jobs );
			foreach ( $jobs as $job ) {
					$this->assertNotNull( $job );
				if ( str_contains( $job['message']->subject, 'Your inquiry' ) ) {
					$this->assertStringContainsString( 'InstallerFixtureName', $job['message']->body );
					$this->assertStringContainsString( 'Please quote three compatible inverters.', $job['message']->body );
					$this->assertStringContainsString( 'https://example.test/product', $job['message']->body );
				}
			}
		}
		$orders = wc_get_orders( array( 'billing_email' => $target ) );
		$this->assertIsArray( $orders );
		$this->assertCount( 3, $orders );
		$this->later(
			static function () use ( $orders ): void {
				foreach ( $orders as $order ) {
					$order->delete( true );
				}
			}
		);
	}

	/**
	 * Login succeeds normally; only repeated failed use needs a scoped proof.
	 */
	public function test_genie_native_handoffs_report_all_suppressed_receipts(): void {
		delete_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION );
		update_option( \Linker\Commerce\Mail\Throttle::OPTION, array_fill( 0, \Linker\Commerce\Mail\Throttle::PER_MINUTE, time() ), false );
		foreach ( array( 'contact', 'inquiry' ) as $door ) {
			foreach ( array( 'target_cap', 'unavailable' ) as $reason ) {
				delete_option( Ledger::OPTION );
				$email = $door . '-' . $reason . '@example.test';
				if ( 'target_cap' === $reason ) {
					$this->assertTrue( ReceiptBudget::take( $email, wp_generate_uuid4() ) );
					$this->assertTrue( ReceiptBudget::take( $email, wp_generate_uuid4() ) );
				} else {
					update_option( Ledger::OPTION, 'synthetic damaged journal', false );
				}
				$payload = array(
					'customer' => array(
						'name'  => 'Synthetic handoff',
						'email' => $email,
					),
					'message'  => 'Please contact us.',
					'summary'  => array( 'Please contact us.' ),
					'locale'   => 'en',
				);
				$marker  = self::newest_mail_job();
				// phpcs:ignore WooCommerce.Commenting.CommentHooks.MissingHookComment, WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- Exercise the existing native Genie handoff constants.
				$result = apply_filters( 'contact' === $door ? \Linker\Commerce\Genie\Module::CONTACT_FILTER : \Linker\Commerce\Genie\Module::INQUIRY_FILTER, null, $payload );
				$this->assertIsArray( $result );
				$this->assertFalse( $result['receipt'] );
				$order = wc_get_order( $result['order'] );
				$this->assertInstanceOf( WC_Order::class, $order );
				$this->later(
					static function () use ( $order ): void {
						$order->delete( true );
					}
				);
				$this->assertSame( 'inquiry-received', $order->get_status() );
				$this->assertSame( 'assessment_pending', $order->get_meta( \Linker\Commerce\Inquiry\ReceiptLimit::SKIPPED_META ) );
				$this->authorization->drain();
				$order->read_meta_data( true );
				$this->assertSame( $reason, $order->get_meta( \Linker\Commerce\Inquiry\ReceiptLimit::SKIPPED_META ) );
				$this->assertCount( 1, self::mail_jobs_after( $marker ), 'Only the normal team notice is queued.' );
			}
		}
	}

	/** Login's progressive challenge does not change its native password check. */
	public function test_progressive_login_preserves_normal_success_and_gates_failed_use(): void {
		$customer = $this->customer();
		$user     = get_userdata( $customer->get_id() );
		$this->assertInstanceOf( \WP_User::class, $user );
		$password = 'Synthetic-local-login-fixture-520';
		wp_set_password( $password, $user->ID );
		$this->assertInstanceOf( \WP_User::class, wp_authenticate( $user->user_login, $password ) );
		for ( $i = 0; $i < 3; ++$i ) {
			$this->assertInstanceOf( WP_Error::class, wp_authenticate( $user->user_login, 'synthetic-wrong-password' ) );
		}
		$blocked = wp_authenticate( $user->user_login, $password );
		$this->assertInstanceOf( WP_Error::class, $blocked );
		$this->assertSame( 'linker_admission_configuration', $blocked->get_error_code() );
		$post = $_POST;
		$this->later(
			static function () use ( $post ): void {
				$_POST = $post;
			}
		);
		$_POST = $this->post( 'login' );
		$this->assertInstanceOf( \WP_User::class, wp_authenticate( $user->user_login, $password ) );
		$this->assertInstanceOf( WP_Error::class, wp_authenticate( $user->user_login, 'synthetic-wrong-password' ) );
	}

	/**
	 * Direct native draft commands stop before native side effects without proof.
	 */
	public function test_native_draft_transport_and_store_api_require_scoped_proof(): void {
		$guard   = new \Linker\Commerce\Protection\Draft();
		$product = $this->product( '125' );
		$this->assertTrue( $guard->decision( array( 'product_id' => $product->get_id() ) ), 'A read-only query parameter is not a write.' );
		$shipping = WC()->customer->get_shipping_country();
		$this->assertInstanceOf(
			WP_Error::class,
			$guard->decision(
				array(
					'calc_shipping'         => '1',
					'calc_shipping_country' => 'FR',
					'woocommerce-shipping-calculator-nonce' => wp_create_nonce( 'woocommerce-shipping-calculator' ),
				)
			)
		);
		$this->assertSame( $shipping, WC()->customer->get_shipping_country() );
		$this->assertInstanceOf( WP_Error::class, $guard->decision( array( 'add-to-cart' => $product->get_id() ) ) );
		$this->assertInstanceOf(
			WP_Error::class,
			$guard->decision(
				array(
					'wc-ajax'       => 'remove_from_cart',
					'cart_item_key' => 'synthetic',
				)
			)
		);
		$post = array_merge(
			$this->post( 'draft_write' ),
			array(
				'add-to-cart' => $product->get_id(),
				'quantity'    => 2,
			)
		);
		$this->assertTrue( $guard->decision( $post ) );
		$guard->complete();
		$this->assertInstanceOf( WP_Error::class, $guard->decision( $post ), 'Native duplicate add cannot write twice.' );
		$this->assertTrue( WC()->cart->is_empty() );
		$request = new \WP_REST_Request( 'POST', '/wc/store/v1/cart/add-item' );
		$request->set_param( 'id', $product->get_id() );
		$request->set_param( 'quantity', 1 );
		$request->set_header( 'Nonce', wp_create_nonce( 'wc_store_api' ) );
		$reply = rest_do_request( $request );
		$this->assertGreaterThanOrEqual( 400, $reply->get_status() );
		$this->assertTrue( WC()->cart->is_empty() );
	}

	/**
	 * Native cart aliases and mixed-case native routes retain the same write gate.
	 */
	public function test_store_api_cart_aliases_cannot_bypass_the_actual_mutation_gate(): void {
		$product = $this->product( '125' );
		$coupon  = new \WC_Coupon();
		$coupon->set_code( 'fixture520-' . self::tag() );
		$coupon->set_amount( '1' );
		$coupon->save();
		$this->later(
			static function () use ( $coupon ): void {
				$coupon->delete( true );
			}
		);
		$key = WC()->cart->add_to_cart( $product->get_id(), 1 );
		$this->assertIsString( $key );
		$cases = array(
			array( 'POST', '/wc/store/v1/cart/items' ),
			array( 'DELETE', '/wc/store/v1/cart/items' ),
			array( 'PUT', '/wc/store/v1/cart/items/' . $key ),
			array( 'PATCH', '/wc/store/v1/cart/items/' . $key ),
			array( 'DELETE', '/wc/store/v1/cart/items/' . $key ),
			array( 'POST', '/wc/store/v1/cart/coupons' ),
			array( 'DELETE', '/wc/store/v1/cart/coupons' ),
			array( 'DELETE', '/wc/store/v1/cart/coupons/' . $coupon->get_code() ),
			array( 'POST', '/WC/STORE/V1/CART/ITEMS' ),
		);
		foreach ( $cases as [ $method, $route ] ) {
			$request = new \WP_REST_Request( $method, $route );
			$request->set_param( 'id', $product->get_id() );
			$request->set_param( 'quantity', 2 );
			$request->set_param( 'code', $coupon->get_code() );
			$request->set_header( 'Nonce', wp_create_nonce( 'wc_store_api' ) );
			$reply = rest_do_request( $request );
			$data  = $reply->get_data();
			$this->assertGreaterThanOrEqual( 400, $reply->get_status(), $method . ' ' . $route );
			$this->assertStringStartsWith( 'linker_admission_', $data['code'], $method . ' ' . $route );
			$this->assertSame( 1, WC()->cart->get_cart_contents_count() );
		}
		$batch = new \WP_REST_Request( 'POST', '/batch/v1' );
		$batch->set_body_params(
			array(
				'requests' => array(
					array(
						'method'  => 'POST',
						'path'    => '/wc/store/v1/cart/items',
						'headers' => array( 'Nonce' => wp_create_nonce( 'wc_store_api' ) ),
						'body'    => array(
							'id'       => $product->get_id(),
							'quantity' => 2,
						),
					),
				),
			)
		);
		$batch_reply = rest_do_request( $batch );
		$this->assertSame( 207, $batch_reply->get_status() );
		$batch_data = $batch_reply->get_data();
		$this->assertStringStartsWith( 'linker_admission_', $batch_data['responses'][0]['body']['code'] );
		$this->assertSame( 1, WC()->cart->get_cart_contents_count() );
		$request = new \WP_REST_Request( 'POST', '/wc/store/v1/cart/items' );
		foreach ( $this->post( 'draft_write' ) as $field => $value ) {
			$request->set_param( $field, $value );
		}
		$request->set_param( 'id', $product->get_id() );
		$request->set_param( 'quantity', 2 );
		$request->set_header( 'Nonce', wp_create_nonce( 'wc_store_api' ) );
		$this->assertSame( 201, rest_do_request( $request )->get_status() );
		$this->assertSame( 3, WC()->cart->get_cart_contents_count() );
	}

	/**
	 * Only unauthenticated pingback writing is removed; staff XML-RPC stays native.
	 */
	public function test_comments_and_xmlrpc_do_not_offer_an_unprotected_public_write(): void {
		$methods  = array(
			'pingback.ping'                    => 'pingback',
			'wp.getPosts'                      => 'authenticated',
			'pingback.extensions.getPingbacks' => 'readonly',
		);
		$filtered = apply_filters( 'xmlrpc_methods', $methods ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound, WooCommerce.Commenting.CommentHooks.MissingHookComment -- Invoke WordPress's native XML-RPC method map.
		$this->assertArrayNotHasKey( 'pingback.ping', $filtered );
		$this->assertSame( 'authenticated', $filtered['wp.getPosts'] );
		$this->assertSame( 'readonly', $filtered['pingback.extensions.getPingbacks'] );
		$request = new \WP_REST_Request( 'POST', '/wp/v2/comments' );
		$request->set_param( 'post', 1 );
		$request->set_param( 'content', 'Synthetic local comment.' );
		$this->assertGreaterThanOrEqual( 400, rest_do_request( $request )->get_status(), 'Native anonymous REST comments stay closed.' );
	}

	/**
	 * Native REST and form hooks consume one proof at the same native insertion.
	 */
	public function test_valid_native_rest_comment_does_not_require_a_second_form_proof(): void {
		$customer = $this->customer();
		$this->as_user( $customer->get_id() );
		$id = wp_insert_post(
			array(
				'post_title'     => 'Local public comment fixture',
				'post_status'    => 'publish',
				'comment_status' => 'open',
			)
		);
		$this->assertGreaterThan( 0, $id );
		$this->later(
			static function () use ( $id ): void {
				wp_delete_post( $id, true );
			}
		);
		// The snapshot closes comments through a native filter. Open only this
		// disposable fixture to exercise the protected enabled-comments path.
		$open = static fn ( bool $allowed, int $post_id ): bool => $id === $post_id || $allowed;
		add_filter( 'comments_open', $open, 99, 2 );
		$this->later(
			static function () use ( $open ): void {
				remove_filter( 'comments_open', $open, 99 );
			}
		);
		$request = new \WP_REST_Request( 'POST', '/wp/v2/comments' );
		foreach ( $this->post( 'comment' ) as $key => $value ) {
			$request->set_param( $key, $value );
		}
		$request->set_param( 'post', $id );
		$request->set_param( 'content', 'Valid native REST comment fixture.' );
		$reply   = rest_do_request( $request );
		$encoded = wp_json_encode( $reply->get_data() );
		$this->assertSame( 201, $reply->get_status(), is_string( $encoded ) ? $encoded : 'Native comment returned an unencodable response.' );
		$data = $reply->get_data();
		$this->assertGreaterThan( 0, $data['id'] );
		$this->later(
			static function () use ( $data ): void {
				wp_delete_comment( $data['id'], true );
			}
		);
		$this->assertGreaterThanOrEqual( 400, rest_do_request( $request )->get_status(), 'The consumed logical UUID cannot insert the comment twice.' );
	}

	/**
	 * Contact recovery retains editable fields once, excluding credentials.
	 */
	public function test_native_contact_recovery_is_allowlisted_and_expires(): void {
		$_COOKIE['wp_woocommerce_session_local_fixture'] = 'native-session-presence-fixture';
		$post = array_merge(
			$this->post( 'contact' ),
			array(
				'password' => 'NeverRecoverPassword',
				'message'  => '<script>bad()</script>Existing question',
			)
		);
		\Linker\Commerce\Protection\FormRecovery::save( 'contact', $post );
		$fields = \Linker\Commerce\Protection\FormRecovery::consume( 'contact' );
		$this->assertSame( $post['email'], $fields['email'] );
		$this->assertSame( $post['linker_request_id'], $fields['linker_request_id'] );
		$this->assertArrayNotHasKey( 'password', $fields );
		$this->assertArrayNotHasKey( 'linker_proof', $fields );
		$this->assertArrayNotHasKey( 'linker_contact_nonce', $fields );
		$this->assertStringNotContainsString( '<script>', $fields['message'] );
		$this->assertSame( array(), \Linker\Commerce\Protection\FormRecovery::consume( 'contact' ) );
		WC()->session->set(
			'linker_form_recovery_contact_expired',
			array(
				'until'  => time() - 1,
				'fields' => array( 'email' => $post['email'] ),
			)
		);
		$this->assertSame( array(), \Linker\Commerce\Protection\FormRecovery::consume( 'contact_expired' ) );
	}

	/**
	 * Native Woo erasure removes all public retry references with the inquiry PII.
	 */
	public function test_native_order_erasure_removes_the_idempotency_association(): void {
		$post  = $this->post();
		$order = ( new Handler() )->process( $post );
		$this->assertInstanceOf( WC_Order::class, $order );
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		$this->assertSame( $post['linker_request_id'], $order->get_meta( BusinessRecord::REQUEST ) );
		\WC_Privacy_Erasers::remove_order_personal_data( $order );
		$loaded = wc_get_order( $order->get_id() );
		$this->assertInstanceOf( WC_Order::class, $loaded );
		foreach ( array( BusinessRecord::REQUEST, BusinessRecord::INPUT, BusinessRecord::SUBJECT ) as $key ) {
			$this->assertSame( '[deleted]', $loaded->get_meta( $key ) );
		}
		$this->assertInstanceOf( WP_Error::class, ( new Handler() )->process( $post ), 'Erased personal data cannot be recovered by replaying the old form.' );
	}

	/**
	 * Target refusal does not spend the independent site's final receipt slot.
	 */
	public function test_receipt_target_caps_are_atomic_with_site_cap(): void {
		$this->assertTrue( ReceiptBudget::take( 'target@example.test', 9900001 ) );
		$this->assertTrue( ReceiptBudget::take( 'TARGET@example.test', 9900002 ) );
		$this->assertFalse( ReceiptBudget::take( 'target@example.test', 9900003 ) );
		for ( $i = 0; $i < 8; ++$i ) {
			$this->assertTrue( ReceiptBudget::take( 'target-' . $i . '@example.test', 9900010 + $i ) );
		}
		$this->assertFalse( ReceiptBudget::take( 'another@example.test', 9900099 ) );
		$this->assertTrue( ReceiptBudget::take( 'target@example.test', 9900001 ), 'Native replay spends no additional allowance.' );
	}
}
