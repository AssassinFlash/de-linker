<?php
/**
 * An inquiry through WooCommerce's checkout.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Gating\PriceDisplay;
use Linker\Commerce\Contact\Submission;
use Linker\Commerce\Inquiry\OrderLocale;
use Linker\Commerce\Inquiry\Sender;
use Linker\Commerce\Inquiry\Statuses;
use WC_Order_Item_Product;

/**
 * A customer's solution draft becomes an inquiry: the Proforma gateway is the
 * only one, the inquiry is "received", stock stays, and lines without a price
 * remember why.
 *
 * @coversNothing
 */
final class InquiryTest extends IntegrationTestCase {

	/**
	 * Sending an inquiry with a priced and an unpriced product.
	 */
	public function test_sending(): void {
		$priced   = $this->product( '1680' );
		$unpriced = $this->product( '' );
		$customer = $this->customer();

		$order = $this->send_inquiry(
			$customer,
			array(
				array( $priced, 2 ),
				array( $unpriced, 1 ),
			)
		);

		$this->assertSame( array( 'linker_inquiry' ), array_keys( WC()->payment_gateways()->get_available_payment_gateways() ) );
		$this->assertSame( Statuses::RECEIVED, $order->get_status() );
		$this->assertSame( '', $order->get_payment_method_title() );
		$this->assertSame( determine_locale(), $order->get_meta( OrderLocale::META ) );
		$reasons = array();
		foreach ( $order->get_items() as $item ) {
			$this->assertInstanceOf( WC_Order_Item_Product::class, $item );
			$reasons[ $item->get_product_id() ] = $item->get_meta( PriceDisplay::ITEM_REASON_META );
		}
		$this->assertSame(
			array(
				$priced->get_id()   => '',
				$unpriced->get_id() => 'unpriced',
			),
			$reasons
		);
		$stocked = wc_get_product( $priced->get_id() );
		$this->assertInstanceOf( \WC_Product::class, $stocked );
		$this->assertSame( 10, $stocked->get_stock_quantity(), 'An inquiry reserves no stock.' );
		$this->assertTrue( WC()->cart->is_empty() );
	}

	/**
	 * Actual submission admits each frozen report under all project locks or retains the draft.
	 *
	 * @dataProvider report_admissions
	 * @param string $outcome Engine reply.
	 */
	public function test_planning_report_submission( string $outcome ): void {
		require_once dirname( __DIR__, 2 ) . '/fixtures/AssessmentFixtureEnvironment.php';
		\Linker\Commerce\Tests\Fixtures\AssessmentFixtureEnvironment::configure();
		wc_load_cart();
		WC()->cart->empty_cart();
		$handoff                         = array(
			'schema_version'  => 1,
			'id'              => str_repeat( 'b', 32 ),
			'snapshot_sha256' => str_repeat( 'c', 64 ),
			'snapshot'        => array(
				'schema_version'       => 1,
				'kind'                 => 'planning_report_only_v1',
				'project_id'           => str_repeat( 'a', 32 ),
				'title'                => 'Roof plan',
				'revision'             => 1,
				'report_run_id'        => str_repeat( 'd', 32 ),
				'input_sha256'         => str_repeat( '1', 64 ),
				'report_source_sha256' => str_repeat( '2', 64 ),
				'report_sha256'        => str_repeat( '3', 64 ),
				'pdf'                  => array(
					'asset_id'   => str_repeat( 'e', 32 ),
					'sha256'     => str_repeat( '4', 64 ),
					'media_type' => 'application/pdf',
				),
				'publication'          => null,
				'items'                => array(),
			),
		);
		$other                           = $handoff;
		$other['id']                     = str_repeat( 'd', 32 );
		$other['snapshot']['project_id'] = str_repeat( '1', 32 );
		$draft                           = array(
			$handoff['id'] => \Linker\Commerce\Planning\DraftTransfer::native_context( $handoff ),
			$other['id']   => \Linker\Commerce\Planning\DraftTransfer::native_context( $other ),
		);
		$product                         = $this->product( '100' );
		$this->assertNotFalse( WC()->cart->add_to_cart( $product->get_id() ) );
		$base = static fn () => 'https://planner.example.test';
		add_filter( 'pre_option_linker_planner_url', $base );
		$this->later( static fn () => remove_filter( 'pre_option_linker_planner_url', $base ) );
		global $wpdb;
		$locks  = array_map( static fn ( $entry ) => 'linker-assessment-' . md5( $wpdb->dbname . '/' . $wpdb->prefix . '/planning-project:' . $entry['snapshot']['project_id'] ), $draft );
		$held   = static function () use ( $locks, $wpdb ): array {
			return array_values( array_map( static fn ( $name ) => (int) $wpdb->get_var( $wpdb->prepare( 'SELECT IS_USED_LOCK(%s) = CONNECTION_ID()', $name ) ), $locks ) );
		};
		$calls  = array();
		$engine = static function ( $previous, $args, $url ) use ( $outcome, $held, &$calls ) {
			if ( 'https://planner.example.test/handoffs/admit-inquiry' !== $url ) {
				return $previous;
			}
			$calls[] = array( json_decode( $args['body'], true ), $args['headers']['X-Linker-Planner-Principal-Kind'], $held() );
			return array(
				'response' => array( 'code' => 'admitted' === $outcome ? 200 : 404 ),
				'headers'  => array( 'content-type' => 'application/json' ),
				'body'     => 'admitted' === $outcome ? '{"admitted":true}' : wp_json_encode( array( 'error' => array( 'code' => $outcome ) ) ),
			);
		};
		add_filter( 'pre_http_request', $engine, 10, 3 );
		$this->later( static fn () => remove_filter( 'pre_http_request', $engine, 10 ) );
		$at_commit      = null;
		$observe_commit = static function ( $sql ) use ( &$at_commit, $held, &$calls ) {
			if ( 'COMMIT' === $sql && $calls && null === $at_commit ) {
				$at_commit = $held();
			}
			return $sql;
		};
		add_filter( 'query', $observe_commit );
		$this->later( static fn () => remove_filter( 'query', $observe_commit ) );
		WC()->session->set( \Linker\Commerce\Planning\DraftTransfer::CONTEXTS, $draft );
		$post       = array(
			'name'    => 'Maria Weber',
			'email'   => 'maria@example.test',
			'consent' => '1',
			\Linker\Commerce\Planning\Context::PRESENT_FIELD => '1',
			\Linker\Commerce\Planning\Context::INCLUDE_FIELD => '1',
			\Linker\Commerce\Planning\Context::REVISIONS_FIELD => array_column( $draft, 'snapshot_sha256', 'id' ),
		);
		$submission = Submission::from_post( $post, false );
		$this->assertInstanceOf( Submission::class, $submission );
		\Linker\Commerce\Planning\Context::inquiry_notes_section();
		$this->assertSame( array(), $calls );
		$submit = static fn () => \Linker\Commerce\Planning\Context::with_submission( $post, static fn () => ( new Sender() )->request( $submission, array(), false ) );
		if ( 'outer_transaction' === $outcome ) {
			$result = \Linker\Commerce\Mail\NativeTransaction::run( $submit );
			$this->assertInstanceOf( \WP_Error::class, $result );
			$this->assertSame( 'checkout-error', $result->get_error_code() );
			$this->assertSame( array(), $calls );
			$this->assertSame( $draft, WC()->session->get( \Linker\Commerce\Planning\DraftTransfer::CONTEXTS ) );
			return;
		}
		$result = $submit();
		if ( $result instanceof \WC_Order ) {
			$this->later( static fn () => $result->delete( true ) );
		}
		$this->assertSame( array( 0, 0 ), $held() );
		$expected = array();
		foreach ( $draft as $entry ) {
			$expected[] = array(
				array(
					'schema_version'  => 1,
					'handoff_id'      => $entry['id'],
					'snapshot_sha256' => $entry['snapshot_sha256'],
				),
				'team',
				array( 1, 1 ),
			);
			if ( 'admitted' !== $outcome ) {
				break;
			}
		}
		$this->assertSame( $expected, $calls );
		if ( 'admitted' === $outcome ) {
			$this->assertInstanceOf( \WC_Order::class, $result );
			$this->assertSame( Statuses::RECEIVED, $result->get_status() );
			$this->assertSame( array_keys( $draft ), array_keys( \Linker\Commerce\Planning\Context::stored( $result ) ) );
			$this->assertSame( array( 1, 1 ), $at_commit );
			$this->assertTrue( WC()->cart->is_empty() );
		} else {
			$this->assertInstanceOf( \WP_Error::class, $result );
			$this->assertSame( 'handoff_not_found' === $outcome ? 'planning_project_deleted' : 'planning_admission_unavailable', $result->get_error_code() );
			$this->assertSame( $draft, WC()->session->get( \Linker\Commerce\Planning\DraftTransfer::CONTEXTS ) );
			$this->assertSame( 1, WC()->cart->get_cart_contents_count() );
			$this->assertNull( $at_commit );
		}
	}

	/**
	 * Private engine admission replies.
	 *
	 * @return array<string,array{string}>
	 */
	public function report_admissions(): array {
		return array(
			'frozen reports' => array( 'admitted' ),
			'deleted report' => array( 'handoff_not_found' ),
			'old endpoint'   => array( 'not_found' ),
			'external owner' => array( 'outer_transaction' ),
		);
	}

	/**
	 * The inquiry stores the conversation summary the team reads (#244).
	 */
	public function test_an_inquiry_carries_the_conversations_summary(): void {
		$product  = $this->product( '1000' );
		$customer = $this->customer();
		$this->as_user( $customer->get_id() );
		wc_load_cart();
		WC()->customer = new \WC_Customer( $customer->get_id(), true );
		WC()->cart->empty_cart();
		$this->assertNotFalse( WC()->cart->add_to_cart( $product->get_id(), 2 ) );
		WC()->cart->calculate_totals();

		$summary = array(
			'summary'    => 'Two inverters for a south-facing roof.',
			'quantities' => array(
				array(
					'product_id' => $product->get_id(),
					'quantity'   => 2,
				),
			),
			'conditions' => array( 'Three-phase connection' ),
			'note'       => 'We need them this quarter.',
			'source'     => 'model',
			'reason'     => null,
		);
		$filter  = static fn () => $summary;
		add_filter( 'linker_genie_inquiry_summary', $filter );
		$this->later(
			static function () use ( $filter ): void {
				remove_filter( 'linker_genie_inquiry_summary', $filter );
			}
		);

		$submission = Submission::from_post(
			array(
				'name'    => 'Maria Weber',
				'email'   => 'maria@example.test',
				'company' => 'Weber Solar',
				'message' => 'Please send a Proforma invoice.',
				'consent' => '1',
			),
			false
		);
		$this->assertInstanceOf( Submission::class, $submission );

		$order = ( new Sender() )->request( $submission );
		$this->assertInstanceOf( \WC_Order::class, $order );
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);

		$this->assertSame( $summary, $order->get_meta( Sender::SUMMARY_META ) );
		$this->assertSame( Statuses::RECEIVED, $order->get_status() );
	}
}
