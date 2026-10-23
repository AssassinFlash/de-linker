<?php
/**
 * Signed Genie lists use the same native atomic writes and immutable history.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Account\PrivateFiles;
use Linker\Commerce\Account\SavedSolutions;
use Linker\Commerce\Protection\Identity;
use Linker\Tools\Genie\DraftActions;
use Linker\Tools\Genie\DraftProof;
use Linker\Tools\Genie\PublicationGuard;
use WC_Product_Simple;
use WP_Error;
use WP_REST_Request;
use WP_REST_Response;

/** Signed current whole-list writes against real Woo.
 *
 * @coversNothing
 */
final class GeniePublicationActionsTest extends IntegrationTestCase {
	/** Original native cookies.
	 *
	 * @var array<string,mixed>
	 */
	private array $cookies = array();

	/** Every fixture has the existing private browser identity and native session. */
	protected function setUp(): void {
		parent::setUp();
		$this->cookies               = $_COOKIE;
		$_COOKIE[ Identity::COOKIE ] = str_repeat( 'a', 32 );
		$owner                       = $this->customer();
		$this->as_user( $owner->get_id() );
		wc_load_cart();
		WC()->customer = new \WC_Customer( $owner->get_id(), true );
		WC()->cart->empty_cart();
		$this->later( static fn() => WC()->cart->empty_cart() );
	}

	/** Restore only this fixture's browser state. */
	protected function tearDown(): void {
		$_COOKIE = $this->cookies;
		parent::tearDown();
	}

	/** Browser-supplied subsets/quantities never define the exact native write. */
	public function test_complete_signed_parts_list_is_added_without_engine_recalculation(): void {
		$a       = $this->product( '100' );
		$b       = $this->product( '200' );
		$request = $this->request( $this->token( $a, $b ) );
		$request->set_param(
			'items',
			array(
				array(
					'product_id' => $a->get_id(),
					'quantity'   => 100,
				),
			)
		);
		$answer = ( new DraftActions() )->draft( $request );
		$this->assertInstanceOf( WP_REST_Response::class, $answer );
		$this->assertSame(
			array(
				$a->get_id() => 2,
				$b->get_id() => 1,
			),
			$this->quantities()
		);
		$this->assertArrayHasKey( 'publication', $answer->get_data() );
	}

	/** A stale second row refuses the whole list before any new writes. */
	public function test_withdrawn_row_and_other_browser_refuse_the_complete_action(): void {
		$a                           = $this->product( '100' );
		$b                           = $this->product( '200' );
		$token                       = $this->token( $a, $b );
		$_COOKIE[ Identity::COOKIE ] = str_repeat( 'b', 32 );
		$this->assertInstanceOf( WP_Error::class, ( new DraftActions() )->draft( $this->request( $token ) ) );
		$_COOKIE[ Identity::COOKIE ] = str_repeat( 'a', 32 );
		$b->set_status( 'draft' );
		$b->save();
		$this->assertInstanceOf( WP_Error::class, ( new DraftActions() )->draft( $this->request( $token ) ) );
		$this->assertSame( array(), $this->quantities() );
	}

	/** Native failure after A restores the prior draft and returns a Genie stale state. */
	public function test_native_failure_never_leaves_a_partial_list(): void {
		$a     = $this->product( '100' );
		$b     = $this->product( '200' );
		$token = $this->token( $a, $b );
		WC()->cart->add_to_cart( $a->get_id(), 1 );
		$before = $this->quantities();
		$refuse = static fn( bool $passed, int $id ): bool => $b->get_id() !== $id && $passed;
		add_filter( 'woocommerce_add_to_cart_validation', $refuse, 99, 2 );
		try {
			$answer = ( new DraftActions() )->draft( $this->request( $token ) );
		} finally {
			remove_filter( 'woocommerce_add_to_cart_validation', $refuse, 99 );
		}
		$this->assertInstanceOf( WP_Error::class, $answer );
		$this->assertSame( 'linker_solution_changed', $answer->get_error_code() );
		$this->assertSame( $before, $this->quantities() );
	}

	/** Historical labels and the exact saved list remain after today's withdrawal. */
	public function test_product_list_save_records_a_real_snapshot_without_fake_engine_input(): void {
		$a      = $this->product( '100' );
		$b      = $this->product( '200' );
		$answer = ( new DraftActions() )->save( $this->request( $this->token( $a, $b ) ) );
		$this->assertInstanceOf( WP_REST_Response::class, $answer );
		$this->assertSame( 201, $answer->get_status() );
		$id = $answer->get_data()['id'];
		$this->later(
			static function () use ( $id ): void {
				wp_delete_post( $id, true );
			}
		);
		$store    = new SavedSolutions( new PrivateFiles( SavedSolutions::REPORTS_DIRECTORY ), '' );
		$snapshot = $store->snapshot( $id );
		$this->assertSame( 'genie', $snapshot['kind'] );
		$this->assertArrayNotHasKey( 'yield', $snapshot );
		$before = $store->historical_items( $id );
		$b->set_status( 'draft' );
		$b->set_name( 'Changed name after saving' );
		$b->save();
		$this->assertSame( $before, $store->historical_items( $id ) );
		$this->assertSame( $snapshot, $store->snapshot( $id ) );
	}

	/** A source change during saving removes only the new private record. */
	public function test_withdrawal_while_saving_compensates_the_new_record(): void {
		$a        = $this->product( '100' );
		$b        = $this->product( '200' );
		$token    = $this->token( $a, $b );
		$created  = 0;
		$withdraw = static function ( int $meta, int $id, string $key ) use ( $b, &$created ): void {
			unset( $meta );
			if ( SavedSolutions::DESIGN_META === $key ) {
				$created = $id;
				wp_update_post(
					array(
						'ID'          => $b->get_id(),
						'post_status' => 'draft',
					)
				);
			}
		};
		add_action( 'added_post_meta', $withdraw, 99, 3 );
		try {
			$answer = ( new DraftActions() )->save( $this->request( $token ) );
		} finally {
			remove_action( 'added_post_meta', $withdraw, 99 );
		}
		$this->assertInstanceOf( WP_Error::class, $answer );
		$this->assertGreaterThan( 0, $created );
		$this->assertNull( get_post( $created ) );
	}

	/** Native Woo nonce still owns session CSRF permission. */
	public function test_native_nonce_is_required(): void {
		$route   = new DraftActions();
		$request = $this->request( '' );
		$this->assertInstanceOf( WP_Error::class, $route->permission( $request ) );
		$request->set_header( 'Nonce', wp_create_nonce( 'wc_store_api' ) );
		$this->assertTrue( $route->permission( $request ) );
	}

	/** Read actual native cart quantities.
	 *
	 * @return array<int,int>
	 */
	private function quantities(): array {
		$out = array();
		foreach ( WC()->cart->get_cart() as $line ) {
			$id         = (int) $line['product_id'];
			$out[ $id ] = ( $out[ $id ] ?? 0 ) + (int) $line['quantity'];
		}
		ksort( $out );
		return $out;
	}

	/** A signed native action request.
	 *
	 * @param string $token Exact artifact proof.
	 */
	private function request( string $token ): WP_REST_Request {
		$request = new WP_REST_Request( 'POST', '/linker-ai/v1/genie/draft' );
		$request->set_param( 'proof', $token );
		return $request;
	}

	/** Sign the live normalized two-product list.
	 *
	 * @param WC_Product_Simple $a First published product.
	 * @param WC_Product_Simple $b Second published product.
	 */
	private function token( WC_Product_Simple $a, WC_Product_Simple $b ): string {
		$dependencies = ( new PublicationGuard() )->dependencies();
		$this->assertIsArray( $dependencies );
		$block  = array(
			'type' => 'parts',
			'add'  => array(
				'items' => array(
					array(
						'product_id' => $a->get_id(),
						'quantity'   => 2,
					),
					array(
						'product_id' => $b->get_id(),
						'quantity'   => 1,
					),
				),
			),
		);
		$stream = ( new DraftProof() )->stream( "event: block\ndata: " . wp_json_encode( $block ) . "\n\nevent: done\ndata: {}\n\n", $dependencies );
		$this->assertIsString( $stream );
		preg_match( '/^data: (.+)$/m', $stream, $data );
		return json_decode( $data[1], true )['add']['proof'];
	}
}
