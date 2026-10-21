<?php
/**
 * Real public handlers, native records and optional receipt boundaries.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

// phpcs:disable WordPress.Security.NonceVerification -- Fixture snapshots and posted data are intentionally sent to the actual native nonce/proof validators.
// phpcs:disable WordPress.PHP.DiscouragedPHPFunctions.runtime_configuration_putenv -- Isolated private env fixtures are restored in cleanup.

use Linker\Commerce\Contact\Handler as ContactHandler;
use Linker\Commerce\Contact\Form as ContactForm;
use Linker\Commerce\Inquiry\Handler;
use Linker\Commerce\Inquiry\Sender;
use Linker\Commerce\Inquiry\Statuses;
use Linker\Commerce\Contact\Submission;
use Linker\Commerce\Protection\Business;
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
	/** Private fixtures never use live keys or send customer mail. */
	protected function setUp(): void {
		parent::setUp();
		$this->as_user( 0 );
		$old = get_option( Ledger::OPTION );
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
			static function () use ( $env, $old, $cookie ): void {
				foreach ( $env as $key => $value ) {
					putenv( false === $value ? $key : $key . '=' . $value );
				}
				delete_option( Ledger::OPTION );
				if ( false !== $old ) {
					update_option( Ledger::OPTION, $old, false );
				}
				$_COOKIE = $cookie;
			}
		);
		wc_load_cart();
		WC()->cart->empty_cart();
		$this->later( static fn () => WC()->cart->empty_cart() );
	}

	/**
	 * One native form attempt, immediately after autofill without a fake clock.
	 *
	 * @param string $action Native action.
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
		return array(
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

	/** A valid proof replaces the old fixed delay and three-per-connection limit. */
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

	/** Missing proof and native nonce failures create neither an inquiry nor mail. */
	public function test_invalid_proofs_and_nonces_have_zero_business_side_effects(): void {
		$marker = self::newest_mail_job();
		$post   = $this->post();
		foreach ( array( array( 'linker_proof' => '' ), array( 'linker_proof' => 'forged' ), array( 'linker_inquiry_nonce' => 'forged' ) ) as $bad ) {
			$this->assertInstanceOf( WP_Error::class, ( new Handler() )->process( array_replace( $post, $bad ) ) );
		}
		$this->assertSame(
			array(),
			wc_get_orders(
				array(
					'billing_email' => $post['email'],
					'return'        => 'ids',
				)
			)
		);
		$this->assertSame( array(), self::mail_jobs_after( $marker ) );
	}

	/** Completed browser retry returns the same native order after the cart was emptied. */
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

	/** A native received record survives loss of the final ledger acknowledgement. */
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

	/** Woo and WordPress both stop before reset key creation when proof is absent. */
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

	/** Woo's real four-argument filter must use email, never its password argument. */
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
	}

	/** Core registration cannot create an account through its direct helper without proof. */
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

	/** Optional customer receipt is fixed; every actual message retains team notification. */
	public function test_target_receipt_cap_retains_business_and_team_with_no_reflected_spam(): void {
		$target = 'same-target@example.test';
		update_option( \Linker\Commerce\Mail\Throttle::OPTION, array_fill( 0, \Linker\Commerce\Mail\Throttle::PER_MINUTE, time() ), false );
		$store = new \Linker\Commerce\Mail\JobStore();
		for ( $i = 0; $i < 3; ++$i ) {
			$post   = array_replace(
				$this->post( 'contact' ),
				array(
					'email'   => $target,
					'name'    => 'ArbitrarySpamName',
					'message' => 'https://spam.example.test/claim ArbitrarySpamBody',
				)
			);
			$marker = self::newest_mail_job();
			$this->assertSame( 2 === $i ? 'sent_no_receipt' : 'sent', ( new ContactHandler() )->process( $post ) );
			$jobs = array_map( static fn ( int $id ) => $store->load( $id ), self::mail_jobs_after( $marker ) );
			$this->assertCount( 2 === $i ? 1 : 2, $jobs );
			foreach ( $jobs as $job ) {
				$this->assertNotNull( $job );
				if ( str_contains( $job['message']->subject, 'Your inquiry' ) ) {
					$this->assertStringNotContainsString( 'ArbitrarySpamName', $job['message']->body );
					$this->assertStringNotContainsString( 'ArbitrarySpamBody', $job['message']->body );
					$this->assertStringNotContainsString( 'spam.example.test', $job['message']->body );
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
				} }
		);
	}

	/** Login succeeds normally; only repeated failed use needs a scoped proof. */
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

	/** Direct native draft commands stop before native side effects without proof. */
	public function test_native_draft_transport_and_store_api_require_scoped_proof(): void {
		$guard   = new \Linker\Commerce\Protection\Draft();
		$product = $this->product( '125' );
		$this->assertTrue( $guard->decision( array( 'product_id' => $product->get_id() ) ), 'A read-only query parameter is not a write.' );
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

	/** Only unauthenticated pingback writing is removed; staff XML-RPC stays native. */
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

	/** Native REST and form hooks consume one proof at the same native insertion. */
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
		$reply = rest_do_request( $request );
		$this->assertSame( 201, $reply->get_status(), wp_json_encode( $reply->get_data() ) ?: 'Native comment returned an unencodable response.' );
		$data = $reply->get_data();
		$this->assertGreaterThan( 0, $data['id'] );
		$this->later(
			static function () use ( $data ): void {
				wp_delete_comment( $data['id'], true );
			}
		);
		$this->assertGreaterThanOrEqual( 400, rest_do_request( $request )->get_status(), 'The consumed logical UUID cannot insert the comment twice.' );
	}

	/** Contact recovery retains editable fields once, excluding credentials. */
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

	/** Native Woo erasure removes all public retry references with the inquiry PII. */
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

	/** Target refusal does not spend the independent site's final receipt slot. */
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
