<?php
/**
 * Engine-owned planning handoffs keep their canonical hash.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Planning;

use Linker\Commerce\Planning\Context;
use Linker\Commerce\Planning\DraftTransfer;
use Linker\Commerce\Products\Publication;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * The authenticated transport owns the cross-language hash, not PHP.
 *
 * @covers \Linker\Commerce\Planning\DraftTransfer
 */
final class DraftTransferEnvelopeTest extends TestCase {

	/** A valid envelope remains valid when its engine hash is not PHP's encoding. */
	public function test_engine_snapshot_hash_is_not_recomputed_by_php(): void {
		$handoff = $this->handoff();

		$this->assertTrue( DraftTransfer::envelope_valid( $handoff, $this->project(), $this->runId(), 4 ) );
		$this->assertFalse( DraftTransfer::envelope_valid( $handoff, str_repeat( 'b', 32 ), $this->runId(), 4 ) );
		$this->assertFalse( DraftTransfer::envelope_valid( $handoff, $this->project(), str_repeat( 'd', 32 ), 4 ) );
		$this->assertFalse( DraftTransfer::envelope_valid( $handoff, $this->project(), $this->runId(), 5 ) );
	}

	/** Malformed identities cannot enter the native Woo writer. */
	public function test_envelope_identities_are_required(): void {
		$handoff       = $this->handoff();
		$handoff['id'] = 'not-a-handoff';
		$this->assertFalse( DraftTransfer::envelope_valid( $handoff ) );

		$handoff                    = $this->handoff();
		$handoff['snapshot_sha256'] = str_repeat( 'a', 63 );
		$this->assertFalse( DraftTransfer::envelope_valid( $handoff ) );

		$handoff                     = $this->handoff();
		$handoff['snapshot']['kind'] = 'another_contract';
		$this->assertFalse( DraftTransfer::envelope_valid( $handoff ) );
	}

	/** Retained native cart context accepts the same engine-owned envelope. */
	public function test_context_keeps_the_engine_envelope_identity(): void {
		WP_Mock::userFunction( 'wp_json_encode', array( 'return' => static fn ( mixed $value ): string => (string) json_encode( $value, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE ) ) );
		$handoff = DraftTransfer::native_context( $this->handoff() );
		$method  = new \ReflectionMethod( Context::class, 'valid' );

		$this->assertTrue( $method->invoke( null, $handoff, $handoff['id'] ) );
		$this->assertFalse( $method->invoke( null, $handoff, str_repeat( 'd', 32 ) ) );
		$handoff['snapshot']['items'][0]['quantity'] = 2;
		$this->assertFalse( DraftTransfer::native_context_valid( $handoff, $handoff['id'] ) );

		$engine_only = $this->handoff();
		$this->assertFalse( $method->invoke( null, $engine_only, $engine_only['id'] ) );

		$legacy                    = $this->handoff();
		$legacy['snapshot_sha256'] = Publication::revision( $legacy['snapshot'] );
		$this->assertTrue( $method->invoke( null, $legacy, $legacy['id'] ) );
	}

	/** A committed request stays recoverable after its handoff leaves the live draft. */
	public function test_receipt_distinguishes_the_current_handoff_from_its_historical_commit(): void {
		if ( ! defined( 'WC_SESSION_CACHE_GROUP' ) ) {
			define( 'WC_SESSION_CACHE_GROUP', 'woocommerce_sessions' ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedConstantFound -- WooCommerce defines it on the running site.
		}
		WP_Mock::userFunction( 'wp_json_encode', array( 'return' => static fn ( mixed $value ): string => (string) json_encode( $value, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE ) ) );
		WP_Mock::userFunction( 'maybe_unserialize', array( 'return' => static fn ( mixed $value ): mixed => $value ) );
		WP_Mock::userFunction( 'wp_cache_delete', array( 'return' => true ) );
		WP_Mock::userFunction( 'get_option', array( 'return' => '1' ) );
		WP_Mock::userFunction( 'pll_get_post', array( 'return' => static fn ( int $id, string $lang ): int => 'de' === $lang ? 2 : $id ) );
		WP_Mock::userFunction( 'get_permalink', array( 'return' => static fn ( int $id ): string => 'https://fixture.invalid/' . $id ) );
		\Mockery::mock( 'alias:WC_Cache_Helper' )->shouldReceive( 'get_cache_prefix' )->andReturn( 'native:' );
		$session = \Mockery::mock( \WC_Session_Handler::class );
		$session->shouldReceive( 'get_customer_id' )->andReturn( 'owner' );
		$native = new class( $session ) {
			/**
			 * Bind the native session fixture.
			 *
			 * @param \WC_Session_Handler $session Store owned by WooCommerce.
			 */
			public function __construct( public \WC_Session_Handler $session ) {}

			/** The session is already ready in this fixture. */
			public function initialize_session(): void {}
		};
		WP_Mock::userFunction( 'WC', array( 'return' => $native ) );
		$command                     = array( 'key' => 'owned-intent' );
		$transfer                    = new DraftTransfer();
		$handoff                     = $this->handoff();
		$known                       = array(
			'intent_sha256' => Publication::revision( $command ),
			'handoff_id'    => $handoff['id'],
			'items'         => array(
				array(
					'id'       => 3556,
					'quantity' => 1,
				),
			),
		);
		$row                         = array( DraftTransfer::LINE_META => $handoff['id'] );
		$context                     = DraftTransfer::native_context( $handoff );
		$report                      = $handoff;
		$report['snapshot']['kind']  = 'planning_report_only_v1';
		$report['snapshot']['items'] = array();
		$receipts                    = array( $command['key'] => $known );
		$report_known                = array_replace( $known, array( 'items' => array() ) );
		$session->shouldReceive( 'get_session_data' )->andReturn(
			array(
				DraftTransfer::RECEIPTS => $receipts,
				DraftTransfer::CONTEXTS => array( $handoff['id'] => $context ),
				'cart'                  => array( $row ),
			),
			array(
				DraftTransfer::RECEIPTS => $receipts,
				DraftTransfer::CONTEXTS => array( $handoff['id'] => $context ),
				'cart'                  => array(),
			),
			array(
				DraftTransfer::RECEIPTS => $receipts,
				'cart'                  => array( $row ),
			),
			array(
				DraftTransfer::RECEIPTS => array( $command['key'] => $report_known ),
				DraftTransfer::CONTEXTS => array( $report['id'] => DraftTransfer::native_context( $report ) ),
			),
			array()
		);
		foreach ( array( true, false, false, true ) as $index => $active ) {
			$result = $transfer->receipt( null, $command, 3 === $index ? $report : $handoff );
			$this->assertIsArray( $result );
			$this->assertSame( 'applied', $result['state'] );
			$this->assertSame( $active, $result['active'] );
			$expected = 3 === $index ? $report_known : $known;
			$this->assertSame( $expected, array_intersect_key( $result['receipt'], $expected ) );
		}
		$this->assertSame(
			array(
				'schema_version' => 1,
				'state'          => 'not_applied',
			),
			$transfer->receipt( null, $command, $handoff )
		);
	}

	/** The owned project identity. */
	private function project(): string {
		return str_repeat( 'a', 32 );
	}

	/** The selected report run identity. */
	private function runId(): string {
		return str_repeat( 'b', 32 );
	}

	/**
	 * A minimal server-frozen product handoff with an engine-owned hash.
	 *
	 * @return array{schema_version:int,id:string,snapshot_sha256:string,snapshot:array{schema_version:int,kind:string,project_id:string,revision:int,report_run_id:string,items:list<array{product_id:int,quantity:int,label:string}>,publication:array{engineering_contract:int,compatibility_revision:string},valuation:float}}
	 */
	private function handoff(): array {
		return array(
			'schema_version'  => 1,
			'id'              => str_repeat( 'c', 32 ),
			'snapshot_sha256' => '32f21fcb2410bf650661ce1bb734133cc87d70222eab42021e0e86627dcd3251',
			'snapshot'        => array(
				'schema_version' => 1,
				'kind'           => 'planning_products_v1',
				'project_id'     => $this->project(),
				'revision'       => 4,
				'report_run_id'  => $this->runId(),
				'items'          => array(
					array(
						'product_id' => 3556,
						'quantity'   => 1,
						'label'      => 'GoodWe GW10K-ETA-G20',
					),
				),
				'publication'    => array(
					'engineering_contract'   => 2,
					'compatibility_revision' => str_repeat( 'e', 64 ),
				),
				'valuation'      => 10416.666666666666,
			),
		);
	}
}
