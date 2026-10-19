<?php
/**
 * Inquiry totals on the abilities REST route follow the account.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Abilities\InquiryStatus;
use Linker\Commerce\Registration\Approval;
use WC_Customer;
use WC_Order;
use WP_REST_Request;

/**
 * A priced inquiry of 1680.00 is this account's own. A guest is refused
 * (401). Pending and restricted accounts get the inquiry and no amount, in
 * English and in German. An approved account keeps the stored amount.
 *
 * @coversNothing
 */
final class InquiryStatusRestTest extends IntegrationTestCase {

	/**
	 * The four account states, on the HTTP route, in both languages.
	 */
	public function test_inquiry_totals_follow_the_account_in_both_languages(): void {
		$customer = $this->customer();
		$order    = $this->priced_inquiry( $customer );
		$amount   = '1680.00';
		$this->assertSame( $amount, $order->get_total() );

		foreach ( array( 'en_US', 'de_DE_formal' ) as $locale ) {
			$this->in_locale(
				$locale,
				function () use ( $customer, $order, $amount, $locale ): void {
					$this->as_user( 0 );
					$guest = $this->status_response();
					$this->assertSame( 401, $guest['status'], $locale );
					$this->assertStringNotContainsString( $amount, $guest['raw'], $locale );

					foreach ( array( Approval::PENDING, Approval::RESTRICTED ) as $status ) {
						$this->set_approval( $customer, $status );
						$hidden  = $this->status_response();
						$inquiry = $this->only_inquiry( $hidden['data'] );
						$this->assertSame( 200, $hidden['status'], $locale . ' ' . $status );
						$this->assertSame( $order->get_id(), $inquiry['id'] );
						$this->assertArrayNotHasKey( 'total', $inquiry );
						$without_id = str_replace( (string) $order->get_id(), '', $hidden['raw'] );
						$this->assertStringNotContainsString( '1680', $without_id, $locale . ' ' . $status );
						$this->assertStringNotContainsString( '1.680', $hidden['raw'], $locale . ' ' . $status );
						$this->assertStringNotContainsString( '1,680', $hidden['raw'], $locale . ' ' . $status );
						$this->assertStringNotContainsString( '€', $hidden['raw'], $locale . ' ' . $status );
					}

					$this->set_approval( $customer, Approval::APPROVED );
					$open    = $this->status_response();
					$inquiry = $this->only_inquiry( $open['data'] );
					$this->assertSame( 200, $open['status'], $locale );
					$this->assertSame( $amount, $inquiry['total'], $locale );
					$this->assertStringContainsString( $amount, $open['raw'], $locale );
				}
			);
		}
	}

	/**
	 * Runs the check in $locale. German must actually switch; English may
	 * already be the site language.
	 *
	 * @param string           $locale Locale.
	 * @param callable(): void $check  Assertions.
	 */
	private function in_locale( string $locale, callable $check ): void {
		$switched = switch_to_locale( $locale );
		if ( 'de_DE_formal' === $locale ) {
			$this->assertTrue( $switched );
		}
		try {
			$check();
		} finally {
			if ( $switched ) {
				restore_previous_locale();
			}
		}
	}

	/**
	 * The customer's one priced inquiry, stored at 1680.00.
	 *
	 * @param WC_Customer $customer Account that owns it. Approved while it is sent.
	 */
	private function priced_inquiry( WC_Customer $customer ): WC_Order {
		$this->as_user( $customer->get_id() );
		$order = $this->send_inquiry( $customer, array( array( $this->product( '1680' ), 1 ) ) );
		$order->set_total( '1680' );
		$order->save();
		$stored = wc_get_order( $order->get_id() );
		$this->assertInstanceOf( WC_Order::class, $stored );

		return $stored;
	}

	/**
	 * Writes an approval state and signs that account back in.
	 *
	 * @param WC_Customer $customer Account.
	 * @param string      $status   Approval state.
	 */
	private function set_approval( WC_Customer $customer, string $status ): void {
		$reason = Approval::RESTRICTED === $status ? 'Net prices are for businesses.' : '';
		$this->assertTrue( ( new Approval() )->set( $customer->get_id(), $status, $reason ) );
		$this->as_user( $customer->get_id() );
	}

	/**
	 * The raw JSON body of GET linker/inquiry-status, as the route sends it.
	 *
	 * @return array{status: int, raw: string, data: array<string, mixed>}
	 */
	private function status_response(): array {
		$server   = rest_get_server();
		$response = $server->dispatch( new WP_REST_Request( 'GET', '/wp-abilities/v1/abilities/' . InquiryStatus::NAME . '/run' ) );
		$data     = $response->get_data();
		$raw      = wp_json_encode( $server->response_to_data( $response, false ) );
		$this->assertIsArray( $data );
		$this->assertIsString( $raw );

		return array(
			'status' => $response->get_status(),
			'raw'    => $raw,
			'data'   => $data,
		);
	}

	/**
	 * The one inquiry in a successful payload.
	 *
	 * @param array<string, mixed> $data Response data.
	 * @return array<string, mixed>
	 */
	private function only_inquiry( array $data ): array {
		$this->assertArrayHasKey( 'inquiries', $data );
		$this->assertIsArray( $data['inquiries'] );
		$this->assertCount( 1, $data['inquiries'] );
		$inquiry = $data['inquiries'][0];
		$this->assertIsArray( $inquiry );

		return $inquiry;
	}
}
