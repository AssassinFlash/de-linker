<?php
/**
 * Native bounded contact/inquiry reception and recovery.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

// phpcs:disable WordPress.PHP.DiscouragedPHPFunctions.runtime_configuration_putenv -- Per-test private mode restored on teardown.
// phpcs:disable WordPress.Security.NonceVerification -- Synthetic native requests exercise the real nonce/proof validators.

use Linker\Commerce\Contact\Form as ContactForm;
use Linker\Commerce\Contact\Handler as ContactHandler;
use Linker\Commerce\Inquiry\Handler;
use Linker\Commerce\Inquiry\Assessment\Queue;
use Linker\Commerce\Inquiry\Assessment\Result;
use Linker\Commerce\Mail\NotificationHold;
use Linker\Commerce\Mail\Throttle;
use Linker\Commerce\Mail\Outbox;
use Linker\Commerce\Protection\Allowance;
use Linker\Commerce\Protection\BusinessRecord;
use Linker\Commerce\Protection\Campaign;
use Linker\Commerce\Protection\Identity;
use Linker\Commerce\Protection\Intake;
use Linker\Commerce\Protection\IntakeStore;
use Linker\Commerce\Protection\Ledger;
use Linker\Commerce\Protection\Proof;
use WC_Order;
use WP_Error;

/**
 * Native intake boundaries with synthetic customer data.
 *
 * @coversNothing
 */
final class SafeIntakeTest extends IntegrationTestCase {
	/** Native isolation, deterministic private mode, no provider calls. */
	protected function setUp(): void {
		parent::setUp();
		$this->as_user( 0 );
		$settings = array(
			'LINKER_PUBLIC_PROTECTION_MODE' => 'enforce',
			'LINKER_BUSINESS_VERIFICATION'  => 'optional',
			'LINKER_TURNSTILE_SITE_KEY'     => '1x00000000000000000000AA',
			'LINKER_TURNSTILE_SECRET_KEY'   => '1x0000000000000000000000000000000AA',
			'LINKER_TURNSTILE_HOSTNAME'     => 'localhost',
		);
		foreach ( $settings as $key => $value ) {
			$old = getenv( $key );
			putenv( $key . '=' . $value );
			$this->later(
				static function () use ( $old, $key ): void {
					putenv( false === $old ? $key : $key . '=' . $old );
				}
			);
		}
		foreach ( array( Ledger::OPTION, IntakeStore::OPTION, Campaign::DISABLED, \Linker\Commerce\Mail\OptionBudgetLedger::OPTION ) as $key ) {
			$old = get_option( $key );
			delete_option( $key );
			$this->later(
				static function () use ( $key, $old ): void {
					delete_option( $key );
					if ( false !== $old ) {
						update_option( $key, $old, false );
					}
				}
			);
		}
		$_COOKIE[ Identity::COOKIE ] = str_repeat( 'a', 32 );
		wc_load_cart();
		WC()->cart->empty_cart();
		$this->later( static fn () => WC()->cart->empty_cart() );
	}

	/**
	 * Synthetic fast-filled native request, with optional persisted successful proof.
	 *
	 * @param bool   $verified Whether to create an actual verification receipt.
	 * @param string $action Native form action.
	 * @return array<string,string>
	 */
	private function post( bool $verified = false, string $action = 'inquiry' ): array {
		$started = (string) time();
		$post    = array(
			'name'                 => 'Safe intake fixture',
			'email'                => 'intake-' . self::tag() . '@example.test',
			'company'              => '',
			'message'              => 'Please advise on a 10 kWh system. https://example.test/product',
			'consent'              => '1',
			'lang'                 => 'en',
			'linker_request_id'    => wp_generate_uuid4(),
			'linker_proof'         => '',
			'linker_started'       => $started,
			'linker_started_nonce' => wp_create_nonce( 'linker_inquiry_started_' . $started ),
			'linker_inquiry_nonce' => wp_create_nonce( Handler::ACTION ),
			'linker_contact_nonce' => wp_create_nonce( ContactForm::NONCE_ACTION ),
			'linker_draft_hash'    => WC()->cart->get_cart_hash(),
		);
		if ( $verified ) {
			$identity = Identity::current();
			self::assertInstanceOf( Identity::class, $identity );
			$id     = wp_generate_uuid4();
			$fp     = hash( 'sha256', $id );
			$ledger = new Ledger();
			self::assertIsArray( $ledger->reserve( $id, $fp, array( new Allowance( 'fixture_verification', $identity->browser, 100, HOUR_IN_SECONDS ) ), 10, array(), 'verification_' . $action, $identity->binding() ) );
			self::assertIsArray( $ledger->dispatch( $id, $fp ) );
			self::assertIsArray( $ledger->complete( $id, $fp, 1 ) );
			$post['linker_proof'] = ( new Proof() )->issue( 'verified', $action, $identity, $id );
		}
		$this->later(
			static function () use ( $post ): void {
				$orders = wc_get_orders(
					array(
						'billing_email' => $post['email'],
						'limit'         => -1,
					)
				);
				self::assertIsArray( $orders );
				foreach ( $orders as $order ) {
					$order->delete( true );
				}
			}
		);
		return $post;
	}

	/** Required proof cannot enter either persistent review or grouping.
	 *
	 * @dataProvider required_failures
	 * @param string $action Native door.
	 * @param string $proof Invalid proof shape.
	 * @param string $lane Content/individual variation.
	 */
	public function test_required_verification_rejects_before_any_native_record( string $action, string $proof, string $lane ): void {
		putenv( 'LINKER_BUSINESS_VERIFICATION=required' );
		$post = $this->post( 'wrong-scope' === $proof, 'contact' === $action ? 'inquiry' : 'contact' );
		if ( 'signed-only' === $proof ) {
			$identity = Identity::current();
			self::assertInstanceOf( Identity::class, $identity );
			$post['linker_proof'] = ( new Proof() )->issue( 'verified', $action, $identity, wp_generate_uuid4() );
		} elseif ( 'wrong-scope' !== $proof ) {
			$post['linker_proof'] = $proof;
		}
		if ( 'normal' !== $lane ) {
			$post['message']                  = 'Вам перевод 100 руб. забрать тут https://fredmer.buzz/path';
			$post['linker_individual_review'] = 'individual' === $lane ? '1' : '';
		}
		$jobs     = self::newest_mail_job();
		$capacity = get_option( IntakeStore::OPTION );
		$budget   = get_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION );
		$result   = 'contact' === $action ? ( new ContactHandler() )->process( $post ) : ( new Handler() )->process( $post );
		if ( 'contact' === $action ) {
			self::assertSame( 'verification_failed', $result );
		} else {
			self::assertInstanceOf( WP_Error::class, $result );
			self::assertSame( 'linker_admission_proof', $result->get_error_code() );
		}
		self::assertSame( array(), wc_get_orders( array( 'billing_email' => $post['email'] ) ) );
		self::assertSame( array(), self::mail_jobs_after( $jobs ) );
		self::assertSame( $capacity, get_option( IntakeStore::OPTION ) );
		self::assertSame( $budget, get_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION ) );
	}

	/**
	 * Missing/forged scripts exercise both doors and each old fallback.
	 *
	 * @return array<string,array{string,string,string}> Native cases.
	 */
	public static function required_failures(): array {
		$cases = array();
		foreach ( array( 'contact', 'inquiry' ) as $action ) {
			foreach ( array( '', 'forged', 'wrong-scope', 'signed-only' ) as $proof ) {
				foreach ( array( 'normal', 'campaign', 'individual' ) as $lane ) {
					$cases[ $action . '/' . $proof . '/' . $lane ] = array( $action, $proof, $lane );
				}
			}
		}
		return $cases;
	}

	/** Valid customers retain their complete native result and safe UUID retries.
	 *
	 * @testWith ["contact"]
	 *           ["inquiry"]
	 * @param string $action Native door.
	 */
	public function test_required_valid_proof_saves_once_and_cannot_be_reused_for_new_input( string $action ): void {
		putenv( 'LINKER_BUSINESS_VERIFICATION=required' );
		$post = $this->post( true, $action );
		$send = 'contact' === $action ? new ContactHandler() : new Handler();
		$send->process( $post );
		$orders = wc_get_orders( array( 'billing_email' => $post['email'] ) );
		self::assertIsArray( $orders );
		self::assertCount( 1, $orders );
		$order = $orders[0];
		self::assertSame( $post['message'], $order->get_customer_note() );
		self::assertFalse( NotificationHold::held( $order ) );
		$retry                 = $post;
		$retry['linker_proof'] = '';
		$send->process( $retry );
		$retry_orders = wc_get_orders( array( 'billing_email' => $post['email'] ) );
		self::assertIsArray( $retry_orders );
		self::assertCount( 1, $retry_orders );
		$retry['message'] .= ' changed';
		$changed           = $send->process( $retry );
		self::assertTrue( 'contact' === $action ? 'verification_failed' === $changed : $changed instanceof WP_Error );
		$post['linker_request_id'] = wp_generate_uuid4();
		$reused                    = $send->process( $post );
		self::assertTrue( 'contact' === $action ? 'verification_failed' === $reused : $reused instanceof WP_Error );
		$final_orders = wc_get_orders( array( 'billing_email' => $post['email'] ) );
		self::assertIsArray( $final_orders );
		self::assertCount( 1, $final_orders );
	}

	/** Service configuration failure retains a retry, never a new review record. */
	public function test_required_configuration_outage_cannot_persist_an_unverified_inquiry(): void {
		putenv( 'LINKER_BUSINESS_VERIFICATION=required' );
		$post = $this->post( true );
		$old  = getenv( 'LINKER_TURNSTILE_SECRET_KEY' );
		putenv( 'LINKER_TURNSTILE_SECRET_KEY' );
		try {
			$result = ( new Handler() )->process( $post );
		} finally {
			putenv( false === $old ? 'LINKER_TURNSTILE_SECRET_KEY' : 'LINKER_TURNSTILE_SECRET_KEY=' . $old );
		}
		self::assertInstanceOf( WP_Error::class, $result );
		self::assertSame( 'linker_admission_configuration', $result->get_error_code() );
		self::assertSame( array(), wc_get_orders( array( 'billing_email' => $post['email'] ) ) );
		self::assertFalse( get_option( IntakeStore::OPTION ) );
	}

	/** Missing proof saves complete data, no snapshot, mail, model or receipt budget. */
	public function test_failed_verification_saves_native_record_and_idempotent_retry_without_side_effects(): void {
		$post   = $this->post();
		$jobs   = self::newest_mail_job();
		$budget = get_option( Throttle::OPTION );
		$order  = ( new Handler() )->process( $post );
		self::assertInstanceOf( WC_Order::class, $order );
		self::assertSame( $post['message'], $order->get_customer_note() );
		self::assertSame( $post['email'], $order->get_billing_email() );
		self::assertSame( $post['linker_request_id'], $order->get_meta( BusinessRecord::REQUEST ) );
		self::assertSame( 'verification', $order->get_meta( Intake::META )['lane'] );
		self::assertTrue( NotificationHold::held( $order ) );
		self::assertSame( array(), Queue::data( $order ) );
		self::assertSame( array(), self::mail_jobs_after( $jobs ) );
		self::assertSame( $budget, get_option( Throttle::OPTION ) );
		$retry = ( new Handler() )->process( $post );
		self::assertInstanceOf( WC_Order::class, $retry );
		self::assertSame( $order->get_id(), $retry->get_id() );
		$post['message'] .= ' edited';
		$changed          = ( new Handler() )->process( $post );
		self::assertInstanceOf( WP_Error::class, $changed );
		self::assertSame( 'linker_admission_payload_changed', $changed->get_error_code() );
		$queue = new Queue();
		$queue->process( $order->get_id() );
		$queue->expire( $order->get_id() );
		$queue->finish( $order->get_id(), Result::unknown( 'late' ) );
		self::assertSame( array(), self::mail_jobs_after( $jobs ) );
	}

	/** Forged and wrongly scoped proofs are unverified, never silently normal. */
	public function test_forged_wrong_scope_and_missing_proofs_all_use_bounded_review(): void {
		foreach ( array( '', 'forged', 'wrong-scope' ) as $value ) {
			$post = $this->post( 'wrong-scope' === $value, 'contact' );
			if ( 'wrong-scope' !== $value ) {
				$post['linker_proof'] = $value;
			}
			$order = ( new Handler() )->process( $post );
			self::assertInstanceOf( WC_Order::class, $order );
			self::assertTrue( NotificationHold::held( $order ) );
		}
	}

	/** Native field limits are UTF-8 characters, not JSON escape sequences. */
	public function test_valid_full_length_unicode_message_is_completely_saved(): void {
		$post            = $this->post();
		$post['message'] = str_repeat( '🔋', \Linker\Commerce\Contact\Submission::MAX_MESSAGE );
		$order           = ( new Handler() )->process( $post );
		self::assertInstanceOf( WC_Order::class, $order );
		self::assertSame( $post['message'], $order->get_customer_note() );
		self::assertTrue( NotificationHold::held( $order ) );
	}

	/** Both storage lanes are finite; verified acceptance ignores review fullness. */
	public function test_review_fullness_survives_days_and_does_not_consume_verified_capacity(): void {
		$entries = array();
		for ( $i = 0; $i < IntakeStore::CAPACITY['verification']; ++$i ) {
			$entries[ wp_generate_uuid4() ] = array(
				'lane'  => 'verification',
				'order' => 0,
				'at'    => time() - 2 * DAY_IN_SECONDS,
			);
		}
		update_option(
			IntakeStore::OPTION,
			array(
				'entries'        => $entries,
				'campaign_count' => 0,
			),
			false
		);
		$post     = $this->post();
		$rejected = ( new Handler() )->process( $post );
		self::assertInstanceOf( WP_Error::class, $rejected );
		self::assertSame( 'linker_intake_full', $rejected->get_error_code() );
		self::assertSame( array(), wc_get_orders( array( 'billing_email' => $post['email'] ) ) );
		$normal = ( new Handler() )->process( $this->post( true ) );
		self::assertInstanceOf( WC_Order::class, $normal );
		self::assertFalse( NotificationHold::held( $normal ) );
		self::assertSame( $entries, get_option( IntakeStore::OPTION )['entries'] );
	}

	/** Confirmed activity in any customer text field is refused before every writer. */
	public function test_confirmed_campaign_fields_cannot_create_grouped_or_individual_records(): void {
		$http  = 0;
		$block = static function () use ( &$http ): WP_Error {
			++$http;
			return new WP_Error( 'fixture_no_external_requests' );
		};
		add_filter( 'pre_http_request', $block );
		$this->later(
			static function () use ( $block ): void {
				remove_filter( 'pre_http_request', $block );
			}
		);
		$marker = self::newest_mail_job();
		foreach ( array( 'inquiry', 'contact' ) as $action ) {
			foreach ( array( 'name', 'company', 'message' ) as $field ) {
				foreach ( array( '', '1' ) as $individual ) {
					$post                             = $this->post( true, $action );
					$post[ $field ]                   = 'Вам перевод 100 руб. забрать тут https://xtimex.buzz/synthetic';
					$post['linker_individual_review'] = $individual;
					$ledger                           = get_option( Ledger::OPTION );
					$intake                           = get_option( IntakeStore::OPTION );
					$budget                           = get_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION );
					$throttle                         = get_option( Throttle::OPTION );
					if ( 'inquiry' === $action ) {
						$result = ( new Handler() )->process( $post );
						self::assertInstanceOf( WP_Error::class, $result );
						self::assertSame( 'linker_admission_input', $result->get_error_code() );
					} else {
						self::assertSame( 'verification_failed', ( new ContactHandler() )->process( $post ) );
					}
					self::assertSame( array(), wc_get_orders( array( 'billing_email' => $post['email'] ) ) );
					self::assertSame( $ledger, get_option( Ledger::OPTION ) );
					self::assertSame( $intake, get_option( IntakeStore::OPTION ) );
					self::assertSame( $budget, get_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION ) );
					self::assertSame( $throttle, get_option( Throttle::OPTION ) );
				}
			}
		}
		self::assertSame( array(), self::mail_jobs_after( $marker ) );
		self::assertSame( 0, $http );
	}

	/** The observed profit activity survives native name truncation without a URL. */
	public function test_confirmed_profit_activity_is_blocked_in_native_name_and_company_fields(): void {
		$messages = array(
			'Добрый день! Для вас открыт к платформе с доходностью от 12% в неделю. Мин. сумма 100 долларов, регистрация за 2 минуты.',
			'Здравствуйте. Вам доступен к системе с доходом от 12% в неделю. Вход 100 долларов, регистрация занимает 2 минуты.',
			'Для вас открыт закрытому фонду #7. Система автоматически генерирует доход от 12% еженедельно от вложенной суммы. Вход 100 долларов.',
			'Здравствуйте. Для вас открыт к платформе с доходностью от 12% в неделю. Вход 100 долларов, подключение за 2 минуты. Начать: https://xtimex.buzz/synthetic',
			'Здравствуйте. Вы получили это письмо по своей подписке, и для новых участников открыт доступ к закрытому фонду. Доходность от 12% в неделю при минимальном вложении 100$.',
			'Добрый день. Вы получили это письмо по своей подписке, и для новых участников открыт доступ к закрытому фонду. Доходность от 12% в неделю при депозите от 100$.',
		);
		foreach ( $messages as $message ) {
			self::assertTrue( Campaign::matches( $message ) );
			foreach ( array( 'name', 'company', 'message' ) as $field ) {
				$post           = $this->post( true );
				$post[ $field ] = $message;
				$result         = ( new Handler() )->process( $post );
				self::assertInstanceOf( WP_Error::class, $result );
				self::assertSame( 'linker_admission_input', $result->get_error_code() );
				self::assertSame( array(), wc_get_orders( array( 'billing_email' => $post['email'] ) ) );
			}
		}
	}

	/** Technical Russian, quotations, normal links and domain substrings stay normal. */
	public function test_campaign_rule_does_not_generalize_language_or_links(): void {
		$messages = array( 'Нужна батарея 10 кВт·ч https://fredmer.buzz/manual', 'Вам перевод 100 руб. забрать тут https://fredmer.buzz.evil.test/x', 'Вам перевод 100 руб. забрать тут https://example.test/fredmer.buzz', 'Please investigate this scam: Вам перевод 100 руб. забрать тут https://fredmer.buzz/x', "Вам перевод 100 руб. забрать тут https://fredmer.buzz/x\nPlease quote an inverter.", 'Нужна батарея 10 кВт·ч https://xtimex.buzz/manual', 'Вам перевод 100 руб. забрать тут https://xtimex.buzz.evil.test/x', 'Вам перевод 100 руб. забрать тут https://xtimex.buzz@example.test/x', 'Please investigate this scam: Вам перевод 100 руб. забрать тут https://xtimex.buzz/x', "Вам перевод 100 руб. забрать тут https://xtimex.buzz/x\nPlease quote an inverter." );
		foreach ( $messages as $message ) {
			self::assertFalse( Campaign::matches( $message ) );
			$post            = $this->post( true );
			$post['name']    = 'Александр Müller';
			$post['company'] = 'EPC Köln / 光伏工程';
			$post['message'] = $message;
			$order           = ( new Handler() )->process( $post );
			self::assertInstanceOf( WC_Order::class, $order );
			self::assertFalse( NotificationHold::held( $order ) );
		}
		self::assertTrue( Campaign::matches( 'Вам перевод 100 руб. получить тут https://fredmer.buzz/x' ) );
		self::assertTrue( Campaign::matches( 'Вам перевод 100 руб. забрать тут https://xtimex.buzz/x' ) );
		self::assertTrue( Campaign::matches( 'Вам перевод 100 руб. получить тут https://xtimex.buzz/x' ) );
		update_option( Campaign::DISABLED, 'yes', false );
		self::assertFalse( Campaign::matches( 'Вам перевод 100 руб. получить тут https://fredmer.buzz/x' ) );
		self::assertFalse( Campaign::matches( 'Вам перевод 100 руб. получить тут https://xtimex.buzz/x' ) );
	}

	/** Technical finance, quoted reports and multilingual customer names remain valid. */
	public function test_technical_roi_prices_and_quoted_activity_remain_normal(): void {
		$messages = array(
			'Здравствуйте. Нужна батарея 10 кВт·ч. Цена 100 долларов? КПД выше на 12%. https://example.test/datasheet.pdf',
			'Please quote the 100 USD monitoring option. Our technical ROI report assumes 12% yearly savings. https://example.test/report.pdf',
			'Bitte senden Sie das Datenblatt. Unser Bericht nennt 12% Wirkungsgradverbesserung und 100$ Mehrkosten. https://example.test/datenblatt.pdf',
			'Please investigate this quoted report: Добрый день! Для вас открыт к платформе с доходностью от 12% в неделю. Мин. сумма 100 долларов.',
			'Здравствуйте. Прошу проверить цитату: Для вас открыт закрытому фонду #7. Система автоматически генерирует доход от 12% еженедельно от вложенной суммы. Вход 100 долларов.',
		);
		foreach ( $messages as $message ) {
			self::assertFalse( Campaign::matches( $message ) );
			$post            = $this->post( true );
			$post['name']    = 'Александр Müller';
			$post['company'] = 'EPC Köln / 光伏工程';
			$post['message'] = $message;
			$order           = ( new Handler() )->process( $post );
			self::assertInstanceOf( WC_Order::class, $order );
			self::assertFalse( NotificationHold::held( $order ) );
		}
	}

	/** The original-job-absent case hands off exactly once, preserving all content. */
	public function test_staff_can_release_new_review_record_without_original_job_once(): void {
		$order = ( new Handler() )->process( $this->post() );
		self::assertInstanceOf( WC_Order::class, $order );
		$basis = NotificationHold::reference( $order );
		self::assertInstanceOf( WP_Error::class, NotificationHold::release( $order->get_id(), $basis ) );
		$staff = $this->customer();
		$user  = get_userdata( $staff->get_id() );
		self::assertInstanceOf( \WP_User::class, $user );
		$user->set_role( 'shop_manager' );
		$this->as_user( $staff->get_id() );
		$budget = array_fill( 0, Throttle::PER_DAY, time() );
		update_option( Throttle::OPTION, $budget, false );
		$marker = self::newest_mail_job();
		$result = NotificationHold::release( $order->get_id(), $basis );
		self::assertIsArray( $result );
		self::assertGreaterThan( 0, $result['job'] );
		self::assertTrue( ( new \Linker\Commerce\Mail\JobStore() )->critical( $result['job'] ) );
		self::assertSame( $result, NotificationHold::release( $order->get_id(), $basis ) );
		self::assertCount( 1, self::mail_jobs_after( $marker ) );
		self::assertSame( $budget, get_option( Throttle::OPTION ) );
		$order->read_meta_data( true );
		self::assertFalse( NotificationHold::held( $order ) );
		self::assertSame( array(), get_option( IntakeStore::OPTION )['entries'] );
		self::assertSame( 'staff_release', Queue::data( $order )['result']['reason'] );
		self::assertTrue( as_has_scheduled_action( Outbox::HOOK, array( $result['job'] ), Outbox::GROUP ) );
	}

	/** Native PII removal includes added registry and intake metadata. */
	public function test_native_erasure_removes_added_links_and_review_metadata(): void {
		$order = ( new Handler() )->process( $this->post() );
		self::assertInstanceOf( WC_Order::class, $order );
		\WC_Privacy_Erasers::remove_order_personal_data( $order );
		$order->read_meta_data( true );
		self::assertSame( '', $order->get_meta( Intake::META ) );
		self::assertSame( '[deleted]', $order->get_meta( BusinessRecord::REQUEST ) );
		self::assertSame( array(), get_option( IntakeStore::OPTION )['entries'] );
		self::assertStringNotContainsString( 'example.test', (string) wp_json_encode( get_option( IntakeStore::OPTION ) ) );
	}

	/** Public erasure cannot be undone by a later staff notification release. */
	public function test_erased_review_association_cannot_be_released(): void {
		$post  = $this->post();
		$order = ( new Handler() )->process( $post );
		self::assertInstanceOf( WC_Order::class, $order );
		self::assertTrue( ( new \Linker\Commerce\Protection\Privacy() )->erase( $post['email'] )['items_removed'] );
		$staff = $this->customer();
		$user  = get_userdata( $staff->get_id() );
		self::assertInstanceOf( \WP_User::class, $user );
		$user->set_role( 'shop_manager' );
		$this->as_user( $staff->get_id() );
		$marker = self::newest_mail_job();
		self::assertInstanceOf( WP_Error::class, NotificationHold::release( $order->get_id(), NotificationHold::reference( $order ) ) );
		self::assertSame( array(), self::mail_jobs_after( $marker ) );
		$order->read_meta_data( true );
		self::assertTrue( NotificationHold::held( $order ) );
	}

	/** Native erasure cannot pass an employee holding the record's release lock. */
	public function test_native_erasure_and_staff_release_serialize_across_connections(): void {
		$order = ( new Handler() )->process( $this->post() );
		self::assertInstanceOf( WC_Order::class, $order );
		$reference = NotificationHold::reference( $order );
		$erasure   = array();
		$released  = null;
		self::assertTrue(
			\Linker\Commerce\Inquiry\Assessment\Lock::run(
				'release-' . $order->get_id(),
				function () use ( $order, $reference, &$erasure, &$released ): void {
					// A retains its pre-erasure object; B attempts the entire native eraser.
					$erasure  = $this->erase_in_other_connection( $order->get_id() );
					$released = \Linker\Commerce\Protection\IntakeRelease::run( $order, $reference );
				}
			)
		);
		self::assertSame( 'intake_erasure_busy', $erasure['status'] );
		self::assertIsArray( $released );
		self::assertGreaterThan( 0, $released['job'] );
		$order->read_meta_data( true );
		self::assertSame( '', $order->get_meta( \Linker\Commerce\Inquiry\Assessment\Reviews::ERASED ) );
	}

	/** A completed erase wins even when staff retained a complete stale Woo object. */
	public function test_completed_native_erasure_cannot_be_resurrected_from_stale_object(): void {
		$post  = $this->post();
		$order = ( new Handler() )->process( $post );
		self::assertInstanceOf( WC_Order::class, $order );
		$reference = NotificationHold::reference( $order );
		$marker    = self::newest_mail_job();
		self::assertSame( 'erased', $this->erase_in_other_connection( $order->get_id() )['status'] );
		self::assertSame( $post['email'], $order->get_billing_email() );
		self::assertNotEmpty( $order->get_meta( Intake::META ) );
		$released = null;
		self::assertTrue(
			\Linker\Commerce\Inquiry\Assessment\Lock::run(
				'release-' . $order->get_id(),
				static function () use ( $order, $reference, &$released ): void {
					$released = \Linker\Commerce\Protection\IntakeRelease::run( $order, $reference );
				}
			)
		);
		self::assertInstanceOf( WP_Error::class, $released );
		self::assertSame( array(), self::mail_jobs_after( $marker ) );
		$order->read_meta_data( true );
		self::assertSame( 'yes', $order->get_meta( \Linker\Commerce\Inquiry\Assessment\Reviews::ERASED ) );
		self::assertSame( '', $order->get_meta( Intake::META ) );
		wp_cache_delete( IntakeStore::OPTION, 'options' );
		self::assertSame( array(), get_option( IntakeStore::OPTION )['entries'] );
	}

	/**
	 * Run Woo's real eraser while the caller keeps its own DB connection and cache.
	 *
	 * @param int $id Synthetic native inquiry.
	 * @return array<string,mixed>
	 */
	private function erase_in_other_connection( int $id ): array {
		return $this->run_native_worker( 'intake_privacy_worker.php', array( (string) $id ) );
	}

	/**
	 * Execute one local worker with its own native DB connection and object cache.
	 *
	 * @param string   $fixture Tracked fixture filename.
	 * @param string[] $arguments Fixture arguments.
	 * @phpstan-param list<string> $arguments
	 * @return array<string,mixed>
	 */
	private function run_native_worker( string $fixture, array $arguments ): array {
		$pipes = array();
		// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.system_calls_proc_open -- Independent local WordPress/DB connection, no external calls.
		$process = proc_open(
			array_merge( array( PHP_BINARY, '-d', 'memory_limit=2048M', dirname( __DIR__, 2 ) . '/fixtures/' . $fixture ), $arguments ),
			array(
				0 => array( 'pipe', 'r' ),
				1 => array( 'pipe', 'w' ),
				2 => array( 'pipe', 'w' ),
			),
			$pipes
		);
		self::assertIsResource( $process );
		fclose( $pipes[0] );
		$out = stream_get_contents( $pipes[1] );
		$err = stream_get_contents( $pipes[2] );
		fclose( $pipes[1] );
		fclose( $pipes[2] );
		self::assertSame( 0, proc_close( $process ), (string) $err );
		$result = json_decode( (string) $out, true );
		self::assertIsArray( $result, (string) $out );
		return $result;
	}

	/** First initialization must ignore another connection's stale negative option cache. */
	public function test_first_two_saves_preserve_both_records_after_negative_cache_warmup(): void {
		$barrier = tempnam( sys_get_temp_dir(), 'linker-542-init-' );
		self::assertIsString( $barrier );
		$this->later(
			static function () use ( $barrier ): void {
				unlink( $barrier );
			}
		);
		$pipes = array();
		// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.system_calls_proc_open -- B warms its native in-process negative cache before A's first DB save.
		$process = proc_open(
			array( PHP_BINARY, '-d', 'memory_limit=2048M', dirname( __DIR__, 2 ) . '/fixtures/safe_intake_worker.php', $barrier, 'initial-' . self::tag() . '@example.test', 'negative-cache' ),
			array(
				0 => array( 'pipe', 'r' ),
				1 => array( 'pipe', 'w' ),
				2 => array( 'pipe', 'w' ),
			),
			$pipes
		);
		self::assertIsResource( $process );
		fclose( $pipes[0] );
		$until = microtime( true ) + 5;
		while ( 'ready' !== file_get_contents( $barrier ) && microtime( true ) < $until ) {
			usleep( 10000 );
		}
		self::assertSame( 'ready', file_get_contents( $barrier ) );
		$first = ( new Handler() )->process( $this->post() );
		self::assertInstanceOf( WC_Order::class, $first );
		// B still has its real WordPress notoptions cache; do not reset it here.
		file_put_contents( $barrier, 'go' );
		$out = stream_get_contents( $pipes[1] );
		$err = stream_get_contents( $pipes[2] );
		fclose( $pipes[1] );
		fclose( $pipes[2] );
		self::assertSame( 0, proc_close( $process ), (string) $err );
		$second = json_decode( (string) $out, true );
		self::assertIsArray( $second );
		self::assertArrayHasKey( 'order', $second );
		$second_id = (int) $second['order'];
		$this->later(
			static function () use ( $second_id ): void {
				$order = wc_get_order( $second_id );
				if ( $order instanceof WC_Order ) {
					$order->delete( true );
				}
			}
		);
		wp_cache_delete( IntakeStore::OPTION, 'options' );
		$state = get_option( IntakeStore::OPTION );
		self::assertIsArray( $state );
		self::assertCount( 2, $state['entries'] );
		$ids = array_map( static fn ( array $entry ): int => (int) $entry['order'], $state['entries'] );
		self::assertContains( $first->get_id(), $ids );
		self::assertContains( $second_id, $ids );
	}

	/** A failed durable staff audit rolls back its job and preserves both budgets. */
	public function test_staff_release_rollback_preserves_existing_transport_history(): void {
		$order = ( new Handler() )->process( $this->post() );
		self::assertInstanceOf( WC_Order::class, $order );
		$staff = $this->customer();
		$user  = get_userdata( $staff->get_id() );
		self::assertInstanceOf( \WP_User::class, $user );
		$user->set_role( 'shop_manager' );
		$this->as_user( $staff->get_id() );
		$legacy = array( time() - 120 );
		$state  = wp_json_encode(
			array(
				'entries' => array(
					array(
						'time'      => time() - 120,
						'transport' => Throttle::PHP,
					),
				),
			)
		);
		update_option( Throttle::OPTION, $legacy, false );
		update_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION, $state, false );
		$marker = self::newest_mail_job();
		$fail   = static fn ( $check, $id, $key ) => NotificationHold::EVENT === $key ? false : $check;
		add_filter( 'add_comment_metadata', $fail, 10, 3 );
		try {
			self::assertInstanceOf( WP_Error::class, NotificationHold::release( $order->get_id(), NotificationHold::reference( $order ) ) );
		} finally {
			remove_filter( 'add_comment_metadata', $fail, 10 );
		}
		self::assertSame( array(), self::mail_jobs_after( $marker ) );
		wp_cache_delete( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION, 'options' );
		self::assertSame( $state, get_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION ) );
		self::assertSame( $legacy, get_option( Throttle::OPTION ) );
		$order->read_meta_data( true );
		self::assertTrue( NotificationHold::held( $order ) );
		self::assertCount( 1, get_option( IntakeStore::OPTION )['entries'] );
	}

	/** The contact adapter reports review rather than a sent-team notification. */
	public function test_contact_review_state_is_honest_and_retries_use_same_record(): void {
		$post = $this->post( false, 'contact' );
		self::assertSame( 'saved_review', ( new ContactHandler() )->process( $post ) );
		self::assertSame( 'saved_review', ( new ContactHandler() )->process( $post ) );
		$orders = wc_get_orders( array( 'billing_email' => $post['email'] ) );
		self::assertIsArray( $orders );
		self::assertCount( 1, $orders );
		self::assertStringContainsString( 'is saved and waiting for review', \Linker\Commerce\Protection\IntakeAdmin::saved_message() );
	}
	/** Two native DB connections admit exactly one final global review slot. */
	public function test_two_connections_cannot_overspend_the_last_review_slot(): void {
		$entries = array();
		for ( $i = 1; $i < IntakeStore::CAPACITY['verification']; ++$i ) {
			$entries[ wp_generate_uuid4() ] = array(
				'lane'  => 'verification',
				'order' => 0,
				'at'    => time(),
			);
		}
		update_option(
			IntakeStore::OPTION,
			array(
				'entries'        => $entries,
				'campaign_count' => 0,
			),
			false
		);
		$barrier = tempnam( sys_get_temp_dir(), 'linker-542-' );
		self::assertIsString( $barrier );
		$this->later(
			static function () use ( $barrier ): void {
				unlink( $barrier );
			}
		);
		$workers = array();
		$emails  = array( 'concurrent-one-' . self::tag() . '@example.test', 'concurrent-two-' . self::tag() . '@example.test' );
		foreach ( $emails as $email ) {
			$pipes = array();
			// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.system_calls_proc_open -- Independent native database connections, no external calls.
			$process = proc_open(
				array( PHP_BINARY, '-d', 'memory_limit=2048M', dirname( __DIR__, 2 ) . '/fixtures/safe_intake_worker.php', $barrier, $email ),
				array(
					0 => array( 'pipe', 'r' ),
					1 => array( 'pipe', 'w' ),
					2 => array( 'pipe', 'w' ),
				),
				$pipes
			);
			self::assertIsResource( $process );
			fclose( $pipes[0] );
			$workers[] = array( $process, $pipes );
		}
		file_put_contents( $barrier, 'go' );
		$accepted = 0;
		foreach ( $workers as [ $process, $pipes ] ) {
			$output = stream_get_contents( $pipes[1] );
			$error  = stream_get_contents( $pipes[2] );
			fclose( $pipes[1] );
			fclose( $pipes[2] );
			self::assertSame( 0, proc_close( $process ), $error );
			$result = json_decode( $output, true );
			self::assertIsArray( $result, $output . $error );
			if ( isset( $result['order'] ) ) {
				++$accepted;
				$order = wc_get_order( $result['order'] );
				self::assertInstanceOf( WC_Order::class, $order );
				$this->later(
					static function () use ( $order ): void {
						$order->delete( true );
					}
				);
			} else {
				self::assertContains( $result['error'], array( 'linker_intake_full', 'linker_intake_busy' ) );
			}
		}
		self::assertSame( 1, $accepted );
		wp_cache_delete( IntakeStore::OPTION, 'options' );
		self::assertCount( 128, get_option( IntakeStore::OPTION )['entries'] );
	}
	/** A crash after the first native save recovers the same full record. */
	public function test_interrupted_native_save_recovers_original_without_second_debit(): void {
		$post = $this->post( false, 'contact' );
		$fail = static function ( WC_Order $order ) use ( $post ): void {
			if ( $order->get_billing_email() === $post['email'] ) {
				throw new \Error( 'fixture_interrupted_save' );
			}
		};
		add_action( 'woocommerce_after_order_object_save', $fail );
		try {
			$result = ( new ContactHandler() )->process( $post );
		} finally {
			remove_action( 'woocommerce_after_order_object_save', $fail );
		}
		self::assertSame( 'pending', $result );
		$orders = wc_get_orders( array( 'billing_email' => $post['email'] ) );
		self::assertIsArray( $orders );
		self::assertCount( 1, $orders );
		$before = json_decode( (string) get_option( Ledger::OPTION ), true );
		self::assertSame( 'saved_review', ( new ContactHandler() )->process( $post ) );
		$recovered = wc_get_order( $orders[0]->get_id() );
		self::assertInstanceOf( WC_Order::class, $recovered );
		self::assertSame( $orders[0]->get_id(), $recovered->get_id() );
		self::assertSame( $post['message'], $recovered->get_customer_note() );
		self::assertTrue( NotificationHold::held( $recovered ) );
		$after = json_decode( (string) get_option( Ledger::OPTION ), true );
		self::assertSame( $before['buckets'], $after['buckets'] );
		self::assertSame( \Linker\Commerce\Inquiry\Statuses::RECEIVED, $recovered->get_status() );
	}
	/** Review keeps the complete native product draft for guest/pending/approved customers. */
	public function test_review_retains_products_for_all_customer_states(): void {
		$product = $this->product( '1800' );
		foreach ( array( 'guest', 'pending', 'approved' ) as $status ) {
			if ( 'guest' === $status ) {
				$this->as_user( 0 );
			} else {
				$customer = $this->customer();
				update_user_meta( $customer->get_id(), \Linker\Commerce\Registration\Approval::STATUS_META, $status );
				$this->as_user( $customer->get_id() );
			}
			self::assertIsString( WC()->cart->add_to_cart( $product->get_id(), 2 ) );
			$post            = $this->post();
			$post['message'] = '';
			$order           = ( new Handler() )->process( $post );
			self::assertInstanceOf( WC_Order::class, $order );
			self::assertTrue( NotificationHold::held( $order ) );
			self::assertCount( 1, $order->get_items() );
			$line = current( $order->get_items() );
			self::assertInstanceOf( \WC_Order_Item_Product::class, $line );
			self::assertSame( $product->get_id(), $line->get_product_id() );
			self::assertSame( 2, $line->get_quantity() );
			self::assertTrue( WC()->cart->is_empty() );
		}
	}
	/** A private verification configuration outage still preserves business input. */
	public function test_verification_configuration_outage_is_a_review_save_even_with_old_proof(): void {
		$post = $this->post( true );
		$old  = getenv( 'LINKER_TURNSTILE_SECRET_KEY' );
		putenv( 'LINKER_TURNSTILE_SECRET_KEY' );
		try {
			$order = ( new Handler() )->process( $post );
		} finally {
			putenv( false === $old ? 'LINKER_TURNSTILE_SECRET_KEY' : 'LINKER_TURNSTILE_SECRET_KEY=' . $old );
		}
		self::assertInstanceOf( WC_Order::class, $order );
		self::assertTrue( NotificationHold::held( $order ) );
		self::assertSame( $post['message'], $order->get_customer_note() );
	}

	/** Confirmation uses its actual record rather than a later form's session number. */
	public function test_review_confirmation_uses_authorized_record_and_no_duplicate_receipt_notice(): void {
		$order = ( new Handler() )->process( $this->post() );
		self::assertInstanceOf( WC_Order::class, $order );
		WC()->session->set( 'linker_review_saved', 'a-different-later-record' );
		ob_start();
		( new \Linker\Commerce\Inquiry\Checkout() )->next_steps( $order->get_id() );
		$html = (string) ob_get_clean();
		self::assertStringContainsString( '#' . $order->get_order_number(), $html );
		self::assertStringNotContainsString( 'a-different-later-record', $html );
		self::assertSame( 1, substr_count( $html, 'We have not sent a confirmation email.' ) );
		self::assertStringContainsString( 'quote this inquiry number', $html );
	}
	/** Erasure can find a crash before the first Woo ID, without refunding its slot. */
	public function test_privacy_erases_unwritten_reservation_and_prevents_resurrection(): void {
		$post = $this->post( false, 'contact' );
		$fail = static function ( WC_Order $order ) use ( $post ): void {
			if ( $order->get_billing_email() === $post['email'] ) {
				throw new \Error( 'fixture_before_first_write' );
			}
		};
		add_action( 'woocommerce_before_order_object_save', $fail, 99 );
		try {
			self::assertSame( 'pending', ( new ContactHandler() )->process( $post ) );
		} finally {
			remove_action( 'woocommerce_before_order_object_save', $fail, 99 );
		}
		self::assertSame( array(), wc_get_orders( array( 'billing_email' => $post['email'] ) ) );
		$privacy = new \Linker\Commerce\Protection\Privacy();
		$export  = $privacy->export( $post['email'] );
		self::assertNotEmpty( array_filter( $export['data'], static fn ( array $row ): bool => str_starts_with( $row['item_id'], 'review-capacity-' ) ) );
		$erased = $privacy->erase( $post['email'] );
		self::assertTrue( $erased['items_removed'] );
		$state = get_option( IntakeStore::OPTION );
		self::assertCount( 1, $state['entries'] );
		$entry = $state['entries'][ $post['linker_request_id'] ];
		self::assertSame( array(), $entry['owners'] );
		self::assertSame( '', $entry['fingerprint'] );
		self::assertSame( '', $entry['binding'] );
		self::assertSame( 'verification_failed', ( new ContactHandler() )->process( $post ) );
		self::assertSame(
			array(),
			wc_get_orders(
				array(
					'billing_email' => $post['email'],
					'limit'         => 10,
				)
			)
		);
	}
	/** The operational summary includes genuine review requests, not campaign samples. */
	public function test_pending_summary_excludes_confirmed_campaign_and_normal_jev_requests(): void {
		$review = ( new Handler() )->process( $this->post() );
		self::assertInstanceOf( WC_Order::class, $review );
		$historical = function ( string $lane ): WC_Order {
			$post  = $this->post();
			$order = new WC_Order();
			$order->set_billing_email( $post['email'] );
			$order->set_customer_note( 'Вам перевод 100 руб. забрать тут https://fredmer.buzz/synthetic-history' );
			$order->update_meta_data( Intake::META, array( 'lane' => $lane ) );
			$order->update_meta_data( Intake::LANE_META, $lane );
			$order->update_meta_data( NotificationHold::META, array( 'reason' => 'historical_fixture' ) );
			$order->save();
			$result = IntakeStore::edit(
				static function ( array &$state ) use ( $lane, $post, $order ): array {
					$state['entries'][ $post['linker_request_id'] ] = array(
						'lane'  => $lane,
						'order' => $order->get_id(),
						'at'    => time(),
					);
					IntakeStore::save( $state );
					return array();
				}
			);
			self::assertIsArray( $result );
			return $order;
		};
		$campaign   = $historical( 'campaign' );
		$summary    = Intake::pending_summary();
		self::assertIsArray( $summary );
		self::assertSame( 1, $summary['count'] );
		self::assertGreaterThan( 0, $summary['oldest'] );
		self::assertStringContainsString( 'linker_intake_review=1', $summary['url'] );
		// phpcs:ignore WooCommerce.Commenting.CommentHooks.MissingHookComment -- Trusted read-only producer seam for aggregate operational alerts.
		self::assertSame( $summary, apply_filters( 'linker_commerce_pending_review_summary', null ) );
		$individual = $historical( 'individual' );
		self::assertInstanceOf( WC_Order::class, ( new Handler() )->process( $this->post( true ) ) );
		$summary = Intake::pending_summary();
		self::assertIsArray( $summary );
		self::assertSame( 2, $summary['count'] );
		foreach ( array( $campaign, $individual ) as $old ) {
			$old->read_meta_data( true );
			self::assertTrue( NotificationHold::held( $old ) );
			self::assertSame( 'Вам перевод 100 руб. забрать тут https://fredmer.buzz/synthetic-history', $old->get_customer_note() );
		}

		\WC_Privacy_Erasers::remove_order_personal_data( $review );
		$summary = Intake::pending_summary();
		self::assertIsArray( $summary );
		self::assertSame( 1, $summary['count'] );
	}
}
