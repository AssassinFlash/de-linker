<?php
/**
 * Tests for sorting without prices.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Gating;

use Linker\Commerce\Gating\ProductSorting;
use Linker\Commerce\Gating\CommerceState;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Tests for ProductSorting.
 *
 * @covers \Linker\Commerce\Gating\ProductSorting
 */
final class ProductSortingTest extends TestCase {

	/**
	 * Whether a customer is logged in, in the current step.
	 *
	 * @var bool
	 */
	private bool $logged_in = false;

	/**
	 * Login state follows $logged_in.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => fn (): bool => $this->logged_in ) );
	}

	/**
	 * Guests get no price sort options; customers keep them.
	 */
	public function test_options(): void {
		$options = array(
			'menu_order' => 'Default',
			'date'       => 'Latest',
			'price'      => 'Price: low to high',
			'price-desc' => 'Price: high to low',
		);
		$sorting = new ProductSorting( $this->approved_state() );

		$this->assertSame( array( 'menu_order', 'date' ), array_keys( $sorting->options( $options ) ) );
		$this->logged_in = true;
		$this->assertSame( $options, $sorting->options( $options ) );
	}

	/**
	 * A price order asked for in the address falls back to the default order for guests.
	 */
	public function test_ordering(): void {
		$price   = array(
			'orderby'  => 'price',
			'order'    => 'ASC',
			'meta_key' => '_price', // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_key -- WooCommerce's price order.
		);
		$sorting = new ProductSorting( $this->approved_state() );

		$this->assertSame( 'menu_order title', $sorting->ordering( $price, 'price' )['orderby'] );
		$this->assertSame( array( 'orderby' => 'date' ), $sorting->ordering( array( 'orderby' => 'date' ), 'date' ) );
		$this->logged_in = true;
		$this->assertSame( $price, $sorting->ordering( $price, 'price-desc' ) );
	}
}
