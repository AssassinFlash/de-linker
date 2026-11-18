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
		$guest = 'guest' === $outcome;
		$ok    = $guest || in_array( $outcome, array( 'admitted', 'lost_lock' ), true );
		$this->as_user( $guest ? 0 : $this->customer()->get_id() );
		wc_load_cart();
		WC()->cart->empty_cart();
		if ( $guest ) {
			$session = WC()->session;
			$this->assertInstanceOf( \WC_Session_Handler::class, $session );
			$cookies = $_COOKIE;
			$present = static function ( $enabled, $name, $value ) {
				$_COOKIE[ $name ] = $value;
				return false;
			};
			add_filter( 'woocommerce_set_cookie_enabled', $present, 10, 3 );
			$session->set_customer_session_cookie( true );
			remove_filter( 'woocommerce_set_cookie_enabled', $present );
			$session->set( 'linker_planner_seen', true );
			$session->save_data();
			$this->later(
				static function () use ( $cookies ) {
					$_COOKIE = $cookies;
				}
			);
		}
		$subject                         = $guest ? \Linker\Tools\Planner\NativeIdentity::guest_subject( WC()->session->get_customer_id() ) : \Linker\Tools\Planner\NativeIdentity::user_subject( get_current_user_id() );
		$handoff                         = $this->planning_report();
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
		$this->later(
			static function () use ( $base ): void {
				remove_filter( 'pre_option_linker_planner_url', $base );
			}
		);
		global $wpdb;
		$peer = new \wpdb( (string) constant( 'DB_USER' ), (string) constant( 'DB_PASSWORD' ), (string) constant( 'DB_NAME' ), (string) constant( 'DB_HOST' ) );
		$peer->set_prefix( $wpdb->prefix );
		$this->later(
			static function () use ( $peer ): void {
				$peer->close();
			}
		);
		$delete = static function () use ( $peer, $handoff, $guest, $subject ) {
			global $wpdb;
			$writer = $wpdb;
			$wpdb   = $peer;
			try {
				return \Linker\Tools\Planner\ProjectDelete::prepared(
					new \Linker\Tools\Planner\Principal( $guest ? 'guest' : 'user', $subject ),
					array( 'project_id' => $handoff['snapshot']['project_id'] ),
					new \Linker\Tools\Planner\Transport()
				);
			} finally {
				$wpdb = $writer;
			}
		};
		$locks  = array_map( static fn ( $entry ) => 'linker-assessment-' . md5( $wpdb->dbname . '/' . $wpdb->prefix . '/planning-project:' . $entry['snapshot']['project_id'] ), $draft );
		$held   = static function () use ( $locks, $wpdb ): array {
			return array_values( array_map( static fn ( $name ) => (int) $wpdb->get_var( $wpdb->prepare( 'SELECT IS_USED_LOCK(%s) = CONNECTION_ID()', $name ) ), $locks ) );
		};
		$calls  = array();
		$engine = static function ( $previous, $args, $url ) use ( $ok, $outcome, $held, $delete, $wpdb, $locks, &$calls ) {
			if ( 'https://planner.example.test/projects/prepared-handoffs' === $url ) {
				return array(
					'response' => array( 'code' => 200 ),
					'headers'  => array( 'content-type' => 'application/json' ),
					'body'     => '{"has_handoffs":true,"inquiry_generation":1}',
				);
			}
			if ( 'https://planner.example.test/handoffs/admit-inquiry' !== $url ) {
				return $previous;
			}
			$blocked = $delete();
			self::assertInstanceOf( \WP_Error::class, $blocked );
			$calls[] = array( json_decode( $args['body'], true ), $args['headers']['X-Linker-Planner-Principal-Kind'], $args['headers']['X-Linker-Planner-Principal-Subject'], \Linker\Commerce\Mail\Capacity::transaction_active(), $held(), $blocked->get_error_code() );
			if ( 'lost_lock' === $outcome && 2 === count( $calls ) ) {
				$wpdb->get_var( $wpdb->prepare( 'SELECT RELEASE_LOCK(%s)', reset( $locks ) ) );
			}

			return array(
				'response' => array( 'code' => $ok ? 200 : 404 ),
				'headers'  => array( 'content-type' => 'application/json' ),
				'body'     => $ok ? '{"admitted":true}' : wp_json_encode( array( 'error' => array( 'code' => $outcome ) ) ),
			);
		};
		add_filter( 'pre_http_request', $engine, 10, 3 );
		$this->later(
			static function () use ( $engine ): void {
				remove_filter( 'pre_http_request', $engine, 10 );
			}
		);
		$received    = false;
		$on_received = static function () use ( &$received ): void {
			$received = true;
		};
		add_action( 'woocommerce_order_status_' . Statuses::RECEIVED, $on_received );
		$this->later(
			static function () use ( $on_received ): void {
				remove_action( 'woocommerce_order_status_' . Statuses::RECEIVED, $on_received );
			}
		);
		$at_commit      = null;
		$observe_commit = static function ( $sql ) use ( &$at_commit, $held, &$received ) {
			if ( 'COMMIT' === $sql && $received && null === $at_commit ) {
				$at_commit = $held();
			}
			return $sql;
		};
		add_filter( 'query', $observe_commit );
		$this->later(
			static function () use ( $observe_commit ): void {
				remove_filter( 'query', $observe_commit );
			}
		);
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
			$this->assertSame( 'planning_admission_unavailable', $result->get_error_code() );
			$this->assertSame( array(), $calls );
			$this->assertSame( $draft, WC()->session->get( \Linker\Commerce\Planning\DraftTransfer::CONTEXTS ) );
			return;
		}
		$result = $submit();
		if ( $result instanceof \WC_Order ) {
			$this->later(
				static function () use ( $result ): void {
					$result->delete( true );
				}
			);
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
				$guest ? 'guest' : 'user',
				$subject,
				false,
				array( 1, 1 ),
				'linker_planner_inquiry_unavailable',
			);
			if ( ! $ok ) {
				break;
			}
		}
		$this->assertSame( $expected, $calls );
		if ( 'lost_lock' === $outcome ) {
			$this->assertInstanceOf( \WP_Error::class, $result );
			$this->assertFalse( \Linker\Commerce\Planning\ProjectReferences::contains( $handoff['snapshot']['project_id'] ), 'A submitter that lost a project lock must not commit an inquiry.' );
			$this->assertSame( 'planning_admission_unavailable', $result->get_error_code() );
			\Linker\Commerce\Protection\FormRecovery::save( 'inquiry', $post + array( 'linker_request_id' => wp_generate_uuid4() ), $result );
			$fields = \Linker\Commerce\Protection\FormRecovery::consume( 'inquiry', true );
			$this->assertSame( '', $fields['linker_request_id'] );
			$this->assertSame( $post['email'], $fields['email'] );
			$retry = $submit();
			$this->assertInstanceOf( \WC_Order::class, $retry );
			$this->later(
				static function () use ( $retry ): void {
					$retry->delete( true );
				}
			);
			$this->assertSame( Statuses::RECEIVED, $retry->get_status() );
			$this->assertSame( array_keys( $draft ), array_keys( \Linker\Commerce\Planning\Context::stored( $retry ) ) );
			return;
		}
		if ( $ok ) {
			$this->assertInstanceOf( \WC_Order::class, $result );
			$this->assertSame( Statuses::RECEIVED, $result->get_status() );
			$this->assertSame( array_keys( $draft ), array_keys( \Linker\Commerce\Planning\Context::stored( $result ) ) );
			$this->assertSame( array( 1, 1 ), $at_commit );
			$after = $delete();
			$this->assertIsArray( $after );
			$this->assertSame( 409, $after['status'] );
			$this->assertSame( 'inquiry_linked', json_decode( $after['body'], true )['error']['code'] );
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
			'guest reports'  => array( 'guest' ),
			'lost lock'      => array( 'lost_lock' ),
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
