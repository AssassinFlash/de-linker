<?php
/**
 * Frozen local provenance in real Woo storage, without provider I/O.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Inquiry\Assessment\CustomerEvidence;
use Linker\Commerce\Inquiry\Assessment\Queue;
use Linker\Commerce\Contact\Submission;
use Linker\Commerce\Inquiry\Sender;
use Linker\Commerce\Registration\Approval;
use Linker\Commerce\Registration\VatProfile;
use WC_Order;

/**
 * The actual account and order store, not metadata doubles.
 *
 * @coversNothing
 */
final class CustomerEvidenceTest extends IntegrationTestCase {

	/** Submitted quoted text survives the actual received transition and capture. */
	public function test_sender_preserves_quoted_business_text_in_both_snapshots(): void {
		$previous = get_option( Queue::ENABLED );
		update_option( Queue::ENABLED, 'yes' );
		$this->later(
			static function () use ( $previous ): void {
				false === $previous ? delete_option( Queue::ENABLED ) : update_option( Queue::ENABLED, $previous );
			}
		);
		delete_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION );
		update_option( \Linker\Commerce\Mail\Throttle::OPTION, array_fill( 0, \Linker\Commerce\Mail\Throttle::PER_MINUTE, time() ), false );
		$message = 'Please review "project" C:\\docs\\project';
		$details = Submission::from_post(
			array(
				'name'    => 'Synthetic Alex',
				'email'   => self::TESTER,
				'message' => $message,
				'consent' => '1',
				'lang'    => 'en',
			)
		);
		$this->assertInstanceOf( Submission::class, $details );
		$order = ( new Sender() )->message( $details );
		$this->later(
			static function () use ( $order ): void {
				foreach ( array( Queue::PROCESS, Queue::EXPIRE ) as $hook ) {
					as_unschedule_all_actions( $hook, array( $order->get_id() ), \Linker\Commerce\Mail\Outbox::GROUP );
				}
				$order->delete( true );
			}
		);
		$this->assertSame( $message, Queue::data( $order )['snapshot']['submission']['message'] );
		$this->assertSame( $message, $order->get_meta( CustomerEvidence::META )['request']['message'] );
		$this->assertSame( 'inquiry-received', $order->get_status() );
	}

	/** A missing linked account cannot inherit the staff approval default. */
	public function test_missing_account_is_explicitly_unavailable(): void {
		$order = wc_create_order();
		$this->assertInstanceOf( WC_Order::class, $order );
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		$customer = $this->customer();
		$user     = $customer->get_id();
		require_once ABSPATH . 'wp-admin/includes/user.php';
		wp_delete_user( $user );
		$order->set_customer_id( $user );
		$evidence = CustomerEvidence::capture( $order, array(), microtime( true ) );
		$this->assertSame( 'unavailable', $evidence['account_record'] );
		$this->assertSame( array(), $evidence['account'] );
		$this->assertSame( '', $evidence['vat']['status'] );
	}

	/** Real account updates after submission must not change either snapshot. */
	public function test_frozen_local_evidence_does_not_expand_the_provider_input(): void {
		$customer = $this->customer();
		$user     = $customer->get_id();
		$checked  = 1600000000; // Intentionally old fixture; no invented age expiry.
		foreach ( array(
			VatProfile::VAT_META      => 'DE123456789',
			VatProfile::NUMBER_META   => 'DE123456789',
			VatProfile::STATUS_META   => VatProfile::VALID,
			VatProfile::CHECKED_META  => $checked,
			Approval::CHANGED_BY_META => 1,
			Approval::CHANGED_AT_META => 1600000001,
			Approval::REASON_META     => 'Synthetic staff-only review reason',
		) as $key => $value ) {
			update_user_meta( $user, $key, $value );
		}
		$previous = get_option( Queue::ENABLED );
		update_option( Queue::ENABLED, 'yes' );
		$this->later(
			static function () use ( $previous ): void {
				false === $previous ? delete_option( Queue::ENABLED ) : update_option( Queue::ENABLED, $previous );
			}
		);
		$order = wc_create_order( array( 'customer_id' => $user ) );
		$this->assertInstanceOf( WC_Order::class, $order );
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		$order->set_billing_company( 'Inquiry Company' );
		$order->update_meta_data( '_billing_vat_id', 'DE 123456789' );
		$marker = self::newest_mail_job();
		$calls  = 0;
		$guard  = static function () use ( &$calls ) {
			++$calls;
			return new \WP_Error( 'no_network_during_capture' );
		};
		add_filter( 'pre_http_request', $guard );
		try {
			Queue::prepare( $order );
			$order->save();
		} finally {
			remove_filter( 'pre_http_request', $guard );
		}
		$this->assertSame( 0, $calls );
		$this->assertSame( $marker, self::newest_mail_job() );
		update_user_meta( $user, VatProfile::VAT_META, 'FR99999999999' );
		update_user_meta( $user, VatProfile::STATUS_META, VatProfile::INVALID );
		update_user_meta( $user, Approval::REASON_META, 'Later reason' );
		Queue::prepare( $order );
		$order->save();
		$fresh = wc_get_order( $order->get_id() );
		$this->assertInstanceOf( WC_Order::class, $fresh );
		$local = $fresh->get_meta( CustomerEvidence::META );
		$this->assertSame( 'DE123456789', $local['vat']['account_number'] );
		$this->assertSame( $checked, $local['vat']['checked_at'] );
		$this->assertSame( 'Synthetic staff-only review reason', $local['account']['approval']['reason'] );
		$this->assertSame( 'valid_at_check', CustomerEvidence::vat_state( $local['vat'] ) );
		$this->assertSame( Queue::data( $fresh )['accepted_at'], $local['captured_at'] );
		$input = Queue::data( $fresh )['snapshot'];
		$this->assertArrayNotHasKey( 'approval', $input['account'] );
		$this->assertStringNotContainsString( 'Synthetic staff-only review reason', (string) wp_json_encode( $input ) );
		$this->assertSame( 'pending', $fresh->get_status() );
	}

	/**
	 * Missing and contradictory provenance cannot become a positive check.
	 *
	 * @dataProvider vat_cases
	 * @param array<string, mixed> $changes Evidence fields.
	 * @param string               $expected Exact evidence state.
	 */
	public function test_vat_provenance( array $changes, string $expected ): void {
		$vat = array_merge(
			array(
				'submitted'      => 'DE 123456789',
				'account_number' => 'DE123456789',
				'checked_number' => 'DE123456789',
				'checked_at'     => 1600000000,
				'status'         => VatProfile::VALID,
				'detail'         => '',
			),
			$changes
		);
		$this->assertSame( $expected, CustomerEvidence::vat_state( $vat ) );
	}

	/**
	 * Number-bound historical check fixtures.
	 *
	 * @return array<string, array{array<string, mixed>, string}>
	 */
	public static function vat_cases(): array {
		return array(
			'exact normalized old check'           => array( array(), 'valid_at_check' ),
			'optional guest number absent'         => array(
				array(
					'submitted'      => '',
					'account_number' => '',
					'checked_number' => '',
					'checked_at'     => 0,
				),
				'not_provided',
			),
			'account check without request number' => array( array( 'submitted' => '' ), 'valid_at_check' ),
			'changed account number'               => array( array( 'account_number' => 'FR99999999999' ), 'number_differs' ),
			'different checked number'             => array( array( 'checked_number' => 'DE999999999' ), 'number_differs' ),
			'no checked number'                    => array( array( 'checked_number' => '' ), 'provenance_incomplete' ),
			'no timestamp'                         => array( array( 'checked_at' => 0 ), 'provenance_incomplete' ),
			'service unavailable'                  => array(
				array(
					'status' => VatProfile::UNVERIFIED,
					'detail' => 'service unavailable',
				),
				'unverified',
			),
			'invalid official result'              => array( array( 'status' => VatProfile::INVALID ), 'invalid_at_check' ),
			'non EU scope'                         => array(
				array(
					'status' => VatProfile::UNVERIFIED,
					'detail' => VatProfile::NOT_EU,
				),
				'outside_scope',
			),
			'contradictory order result'           => array( array( 'order_status' => VatProfile::INVALID ), 'status_differs' ),
		);
	}
}
