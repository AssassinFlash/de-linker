<?php
/**
 * Complete design writes and historical snapshots against real WooCommerce.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Account\AtomicSolutionDraft;
use Linker\Commerce\Account\PrivateFiles;
use Linker\Commerce\Account\SavedSolutions;
use Linker\Commerce\Products\Publication;
use WC_Product_Simple;
use WP_Error;

/**
 * Native writes preserve the complete confirmed design or the prior draft.
 *
 * @coversNothing
 */
final class PublicationSolutionActionsTest extends IntegrationTestCase {
	/** A refused later line restores existing lines and their prior quantities. */
	public function test_native_failure_rolls_back_the_complete_operation(): void {
		[ $a, $b, $kept ] = $this->draft();
		$result           = $this->result( $a, $b );
		$before           = $this->quantities();
		$refuse           = static fn ( bool $passed, int $id ): bool => $b->get_id() !== $id && $passed;
		add_filter( 'woocommerce_add_to_cart_validation', $refuse, 99, 2 );
		try {
			$answer = ( new AtomicSolutionDraft() )->add( $result );
		} finally {
			remove_filter( 'woocommerce_add_to_cart_validation', $refuse, 99 );
		}
		$this->assertInstanceOf( WP_Error::class, $answer );
		$this->assertSame( $before, $this->quantities() );
		$this->assertSame( 1, $this->quantities()[ $a->get_id() ] );
		$this->assertSame( 3, $this->quantities()[ $kept->get_id() ] );
	}

	/** A product withdrawn after confirmation refuses the complete original BOM. */
	public function test_withdrawn_product_refuses_every_new_line(): void {
		[ $a, $b ] = $this->draft();
		$result    = $this->result( $a, $b );
		$before    = $this->quantities();
		$b->set_status( 'draft' );
		$b->save();
		$this->assertInstanceOf( WP_Error::class, ( new AtomicSolutionDraft() )->add( $result ) );
		$this->assertSame( $before, $this->quantities() );
	}

	/** An in-flight withdrawal cannot leave the first newly added line behind. */
	public function test_withdrawal_during_native_add_rolls_back(): void {
		[ $a, $b ] = $this->draft();
		$result    = $this->result( $a, $b );
		$before    = $this->quantities();
		$withdraw  = static function ( string $key, int $id ) use ( $a, $b ): void {
			unset( $key );
			if ( $a->get_id() === $id ) {
				wp_update_post(
					array(
						'ID'          => $b->get_id(),
						'post_status' => 'draft',
					)
				);
			}
		};
		add_action( 'woocommerce_add_to_cart', $withdraw, 99, 2 );
		try {
			$answer = ( new AtomicSolutionDraft() )->add( $result );
		} finally {
			remove_action( 'woocommerce_add_to_cart', $withdraw, 99 );
		}
		$this->assertInstanceOf( WP_Error::class, $answer );
		$this->assertSame( $before, $this->quantities() );
	}

	/** Success is complete and a second click preserves the already held quantities. */
	public function test_complete_write_is_idempotent_by_quantity(): void {
		[ $a, $b, $kept ] = $this->draft();
		$result           = $this->result( $a, $b );
		$writer           = new AtomicSolutionDraft();
		$this->assertIsArray( $writer->add( $result ) );
		$this->assertIsArray( $writer->add( $result ) );
		$this->assertSame( 2, $this->quantities()[ $a->get_id() ] );
		$this->assertSame( 1, $this->quantities()[ $b->get_id() ] );
		$this->assertSame( 3, $this->quantities()[ $kept->get_id() ] );
	}

	/** Historical names come from the snapshot even after today's product changed. */
	public function test_historical_labels_never_read_todays_product(): void {
		[ $a, $b ] = $this->draft();
		$result    = $this->result( $a, $b );
		$store     = new SavedSolutions( new PrivateFiles( SavedSolutions::REPORTS_DIRECTORY ), '' );
		$id        = $store->save(
			get_current_user_id(),
			'Recorded design',
			array(
				array(
					'product_id' => $b->get_id(),
					'quantity'   => 1,
				),
			),
			array(
				'kind'     => 'residential',
				'snapshot' => $result,
			)
		);
		$this->later(
			static function () use ( $id ): void {
				wp_delete_post( $id, true );
			}
		);
		$b->set_name( 'Changed after the customer saved' );
		$b->set_status( 'draft' );
		$b->save();
		$this->assertSame( 'Fixture Recorded battery', $store->historical_items( $id )[0]['label'] );
		$this->assertSame( $result, $store->snapshot( $id ) );
	}

	/**
	 * A real existing draft and three independent published fixtures.
	 *
	 * @return array{WC_Product_Simple,WC_Product_Simple,WC_Product_Simple}
	 */
	private function draft(): array {
		$owner = $this->customer();
		$this->as_user( $owner->get_id() );
		wc_load_cart();
		WC()->customer = new \WC_Customer( $owner->get_id(), true );
		WC()->cart->empty_cart();
		$this->later( static fn () => WC()->cart->empty_cart() );
		$a    = $this->product( '100' );
		$b    = $this->product( '200' );
		$kept = $this->product( '300' );
		$this->assertNotFalse( WC()->cart->add_to_cart( $a->get_id(), 1 ) );
		$this->assertNotFalse( WC()->cart->add_to_cart( $kept->get_id(), 3 ) );
		return array( $a, $b, $kept );
	}

	/**
	 * Scope comes from the current real Woo authority, never fake revision values.
	 *
	 * @param WC_Product_Simple $a Inverter fixture.
	 * @param WC_Product_Simple $b Battery fixture.
	 * @return array<string,mixed>
	 */
	private function result( WC_Product_Simple $a, WC_Product_Simple $b ): array {
		$manifest = Publication::manifest();
		$products = array_column( $manifest['products'], null, 'product_id' );
		return array(
			'selection_fingerprint' => str_repeat( 'a', 64 ),
			'publication'           => array(
				'engineering_contract'   => 2,
				'reference_inputs'       => array(),
				'products'               => array_map(
					static fn ( int $id ): array => array(
						'product_id'       => $id,
						'product_revision' => $products[ $id ]['product_revision'],
					),
					array( $a->get_id(), $b->get_id() )
				),
				'documents'              => array(),
				'compatibility_revision' => $manifest['compatibility_revision'],
			),
			'selected'              => array(
				'lines' => array(
					array(
						'product'  => array(
							'id'    => $a->get_id(),
							'brand' => 'Fixture',
							'model' => 'Recorded inverter',
						),
						'quantity' => 2,
					),
					array(
						'product'  => array(
							'id'    => $b->get_id(),
							'brand' => 'Fixture',
							'model' => 'Recorded battery',
						),
						'quantity' => 1,
					),
				),
			),
		);
	}

	/**
	 * The actual native Woo draft.
	 *
	 * @return array<int,int>
	 */
	private function quantities(): array {
		$quantities = array();
		foreach ( WC()->cart->get_cart() as $line ) {
			$quantities[ (int) $line['product_id'] ] = (int) $line['quantity'];
		}
		ksort( $quantities );
		return $quantities;
	}
}
