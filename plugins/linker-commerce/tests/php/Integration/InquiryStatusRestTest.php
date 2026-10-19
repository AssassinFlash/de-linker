<?php
/**
 * Inquiry totals on the abilities REST route follow the account page.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Abilities\InquiryStatus;
use Linker\Commerce\Gating\PriceDisplay;
use Linker\Commerce\Registration\Approval;
use Linker\Tools\Genie\UserContext;
use WC_Customer;
use WC_Order;
use WC_Order_Item_Product;
use WP_REST_Request;

/**
 * A priced inquiry of 1680.00 is this account's own. A guest is refused
 * (401). Pending and restricted accounts get the inquiry and no amount, in
 * English and in German, on the cookie session and on X-Linker-User-Context.
 * An approved account keeps the stored amount of a priced inquiry, and omits
 * it for a contact message or an unpriced line — the account page's rule.
 *
 * @coversNothing
 */
final class InquiryStatusRestTest extends IntegrationTestCase {

	/**
	 * Decimal amounts, grouped amounts and currency marks. A bare order id
	 * does not match, so the scan does not depend on stripping that id.
	 */
	private const MONEY = '/(?:€|\bEUR\b|\d+[.,]\d{2}|\d{1,3}(?:[.,]\d{3})+)/';

	/**
	 * The four account states, on the HTTP route, in both languages.
	 */
	public function test_inquiry_totals_follow_the_account_in_both_languages(): void {
		$customer = $this->customer();
		$order    = $this->priced_inquiry( $customer );
		$this->assertMatchesRegularExpression( self::MONEY, (string) $order->get_total() );

		foreach ( array( 'en_US', 'de_DE_formal' ) as $locale ) {
			$this->in_locale(
				$locale,
				function () use ( $customer, $order, $locale ): void {
					$this->as_user( 0 );
					$guest = $this->status_response();
					$this->assertSame( 401, $guest['status'], $locale );
					$this->assert_no_amount_in( $guest['raw'], $locale );

					foreach ( array( Approval::PENDING, Approval::RESTRICTED ) as $status ) {
						$this->decide( $customer, $status );
						$this->as_user( $customer->get_id() );
						$hidden  = $this->status_response();
						$inquiry = $this->only_inquiry( $hidden['data'] );
						$this->assertSame( 200, $hidden['status'], $locale . ' ' . $status );
						$this->assertSame( $order->get_id(), $inquiry['id'] );
						$this->assert_no_amount( $inquiry, $hidden['raw'], $locale . ' ' . $status );
					}

					$this->decide( $customer, Approval::APPROVED );
					$this->as_user( $customer->get_id() );
					$open    = $this->status_response();
					$inquiry = $this->only_inquiry( $open['data'] );
					$this->assertSame( 200, $open['status'], $locale );
					$this->assertSame( (string) $order->get_total(), $inquiry['total'], $locale );
					$this->assertMatchesRegularExpression( self::MONEY, (string) $inquiry['total'], $locale );
				}
			);
		}
	}

	/**
	 * Pending and restricted through the header Genie sends, with no cookie
	 * session. The raw JSON and the decoded inquiry have no amount.
	 */
	public function test_the_token_path_hides_the_amount(): void {
		$customer = $this->customer();
		$order    = $this->priced_inquiry( $customer );

		foreach ( array( 'en_US', 'de_DE_formal' ) as $locale ) {
			$this->in_locale(
				$locale,
				function () use ( $customer, $order, $locale ): void {
					foreach ( array( Approval::PENDING, Approval::RESTRICTED ) as $status ) {
						$this->decide( $customer, $status );
						$hidden  = $this->status_response( $this->token( $customer ) );
						$inquiry = $this->only_inquiry( $hidden['data'] );
						$this->assertSame( 200, $hidden['status'], $locale . ' ' . $status );
						$this->assertSame( $order->get_id(), $inquiry['id'], $locale . ' ' . $status );
						$this->assert_no_amount( $inquiry, $hidden['raw'], $locale . ' ' . $status );
					}
				}
			);
		}
	}

	/**
	 * An approved account follows the account page: a contact message and an
	 * inquiry that still has a line without a price carry a stored amount and
	 * return none.
	 */
	public function test_an_approved_account_omits_totals_the_account_page_omits(): void {
		$customer = $this->customer();
		$contact  = $this->with_stored_amount( $this->mark_contact( $this->priced_inquiry( $customer ) ) );
		$unpriced = $this->with_stored_amount( $this->mark_unpriced( $this->priced_inquiry( $customer ) ) );
		$this->as_user( $customer->get_id() );

		foreach ( array( 'en_US', 'de_DE_formal' ) as $locale ) {
			$this->in_locale(
				$locale,
				function () use ( $locale, $contact, $unpriced ): void {
					$open = $this->status_response();
					$this->assertSame( 200, $open['status'], $locale );
					$this->assertArrayHasKey( 'inquiries', $open['data'] );
					$this->assertIsArray( $open['data']['inquiries'] );
					$this->assertCount( 2, $open['data']['inquiries'], $locale );
					$ids = array();
					foreach ( $open['data']['inquiries'] as $inquiry ) {
						$this->assertIsArray( $inquiry );
						$ids[] = $inquiry['id'];
						$this->assert_no_amount( $inquiry, $open['raw'], $locale );
					}
					$this->assertEqualsCanonicalizing( array( $contact->get_id(), $unpriced->get_id() ), $ids, $locale );
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
	 * The customer's one priced inquiry. Its stored total is an amount.
	 *
	 * @param WC_Customer $customer Account that owns it. Approved while it is sent.
	 */
	private function priced_inquiry( WC_Customer $customer ): WC_Order {
		$this->as_user( $customer->get_id() );
		$order = $this->send_inquiry( $customer, array( array( $this->product( '1680' ), 1 ) ) );
		$order->set_total( '1680' );
		$order->save();
		return $this->reloaded( $order );
	}

	/**
	 * A contact message keeps the stored amount the account page does not print.
	 *
	 * @param WC_Order $order Inquiry.
	 */
	private function mark_contact( WC_Order $order ): WC_Order {
		$order->update_meta_data( '_linker_inquiry_source', 'contact' );
		$order->set_total( '1680' );
		$order->save();
		return $this->reloaded( $order );
	}

	/**
	 * One line still awaits a price. The order total stays an amount, which
	 * is what a sees_prices()-only gate would return.
	 *
	 * @param WC_Order $order Inquiry.
	 */
	private function mark_unpriced( WC_Order $order ): WC_Order {
		$marked = false;
		foreach ( $order->get_items() as $item ) {
			if ( $item instanceof WC_Order_Item_Product ) {
				$item->update_meta_data( PriceDisplay::ITEM_REASON_META, 'unpriced' );
				$item->set_total( '0' );
				$item->save();
				$marked = true;
			}
		}
		$this->assertTrue( $marked, 'The inquiry has a line to leave unpriced.' );
		$order->set_total( '1680' );
		$order->save();
		return $this->reloaded( $order );
	}

	/**
	 * The order still stores an amount after the mark.
	 *
	 * @param WC_Order $order Inquiry.
	 */
	private function with_stored_amount( WC_Order $order ): WC_Order {
		$total = (string) $order->get_total();
		$this->assertStringContainsString( '1680', $total );
		$this->assertMatchesRegularExpression( self::MONEY, $total );
		return $order;
	}

	/**
	 * The saved inquiry.
	 *
	 * @param WC_Order $order Inquiry just written.
	 */
	private function reloaded( WC_Order $order ): WC_Order {
		$stored = wc_get_order( $order->get_id() );
		$this->assertInstanceOf( WC_Order::class, $stored );
		return $stored;
	}

	/**
	 * Writes the state as staff (user 1) and checks that stamp.
	 *
	 * @param WC_Customer $customer Account.
	 * @param string      $status   Approval state.
	 */
	private function decide( WC_Customer $customer, string $status ): void {
		$reason = Approval::RESTRICTED === $status ? 'Net prices are for businesses.' : '';
		$this->set_state( $customer, $status, $reason );
		$this->assertSame( 1, ( new Approval() )->changed_by( $customer->get_id() )['by'], $status );
	}

	/**
	 * The customer's token, minted and then signed out so the header is the
	 * only identity on the next request.
	 *
	 * @param WC_Customer $customer Account.
	 */
	private function token( WC_Customer $customer ): string {
		$this->as_user( $customer->get_id() );
		$token = ( new UserContext() )->mint();
		$this->as_user( 0 );
		$this->assertNotSame( '', $token );
		return $token;
	}

	/**
	 * The raw JSON body of GET linker/inquiry-status, as the route sends it.
	 * A token is sent with no cookie session, which is how Genie calls.
	 *
	 * @param string|null $token Customer token, or null for the current session.
	 * @return array{status: int, raw: string, data: array<string, mixed>}
	 */
	private function status_response( ?string $token = null ): array {
		$request = new WP_REST_Request( 'GET', '/wp-abilities/v1/abilities/' . InquiryStatus::NAME . '/run' );
		if ( null !== $token ) {
			$this->assertFalse( is_user_logged_in(), 'A token is ignored while a cookie session exists.' );
			$request->set_header( UserContext::HEADER, $token );
		}
		$server   = rest_get_server();
		$response = $server->dispatch( $request );
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

	/**
	 * No amount field, no amount-shaped value, and none in the raw JSON.
	 *
	 * @param array<string, mixed> $inquiry One inquiry.
	 * @param string               $raw     Encoded response.
	 * @param string               $where   Assertion context.
	 */
	private function assert_no_amount( array $inquiry, string $raw, string $where ): void {
		$this->assertArrayNotHasKey( 'total', $inquiry, $where );
		$allowed = array( 'id', 'number', 'status', 'status_label', 'date', 'proforma_number' );
		$extra   = array_values( array_diff( array_keys( $inquiry ), $allowed ) );
		$this->assertSame( array(), $extra, $where );
		foreach ( $inquiry as $key => $value ) {
			if ( 'id' === $key ) {
				$this->assertIsInt( $value, $where );
				continue;
			}
			$this->assertIsString( $value, $where . ' ' . $key );
			$this->assertDoesNotMatchRegularExpression( self::MONEY, $value, $where . ' ' . $key );
		}
		$this->assert_no_amount_in( $raw, $where );
	}

	/**
	 * The encoded body has no amount shape.
	 *
	 * @param string $raw   Encoded response.
	 * @param string $where Assertion context.
	 */
	private function assert_no_amount_in( string $raw, string $where ): void {
		$this->assertDoesNotMatchRegularExpression( self::MONEY, $raw, $where );
	}
}
