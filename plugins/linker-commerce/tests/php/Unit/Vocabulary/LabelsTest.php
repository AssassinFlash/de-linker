<?php
/**
 * Tests for buttons and page titles.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Vocabulary;

use Linker\Commerce\Tests\TestCase;
use Linker\Commerce\Vocabulary\Labels;
use Mockery;
use WC_Product;
use WP_Mock;

/**
 * Tests for Labels.
 *
 * @covers \Linker\Commerce\Vocabulary\Labels
 */
final class LabelsTest extends TestCase {

	/**
	 * Translations return their source string; the solution draft is page 6, the Proforma request page 7.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::passthruFunction( '__' );
		WP_Mock::userFunction(
			'wc_get_page_id',
			array(
				'return' => static fn ( string $page ): int => array(
					'cart'     => 6,
					'checkout' => 7,
				)[ $page ] ?? -1,
			)
		);
	}

	/**
	 * A product the customer can add says "Add to solution draft"; one out of stock keeps WooCommerce's text.
	 */
	public function test_add_to_draft(): void {
		$addable = Mockery::mock( WC_Product::class );
		$addable->allows( 'is_purchasable' )->andReturn( true );
		$addable->allows( 'is_in_stock' )->andReturn( true );
		$addable->allows( 'is_type' )->andReturn( true );
		$sold_out = Mockery::mock( WC_Product::class );
		$sold_out->allows( 'is_purchasable' )->andReturn( true );
		$sold_out->allows( 'is_in_stock' )->andReturn( false );
		$labels = new Labels();

		$this->assertSame( 'Add to solution draft', $labels->add_to_draft( 'Add to cart', $addable ) );
		$this->assertSame( 'Add to solution draft', $labels->add_to_draft( 'Add to cart' ) );
		$this->assertSame( 'Read more', $labels->add_to_draft( 'Read more', $sold_out ) );
	}

	/**
	 * The fixed texts of the request page and the confirmation.
	 */
	public function test_request_texts(): void {
		$labels = new Labels();

		$this->assertSame( 'Request Proforma', $labels->send_inquiry() );
		$this->assertSame( 'Thank you. Your inquiry has been received.', $labels->inquiry_received() );
		$this->assertStringContainsString( 'request a Proforma invoice', $labels->log_in_to_send() );
	}

	/**
	 * The privacy texts of the request page and the registration form are the plugin's, in the visitor's language.
	 */
	public function test_privacy_text(): void {
		$labels = new Labels();

		$this->assertSame( 'We use your personal data to process your inquiry and for the other purposes described in our [privacy_policy].', $labels->privacy_text( 'process your order', 'checkout' ) );
		$this->assertSame( 'We use your personal data to manage your account and for the other purposes described in our [privacy_policy].', $labels->privacy_text( 'stored text', 'registration' ) );
		$this->assertSame( 'other', $labels->privacy_text( 'other', 'other' ) );
	}

	/**
	 * The solution draft and Proforma request pages carry their names in the page and the browser tab.
	 */
	public function test_page_titles(): void {
		$labels = new Labels();

		$this->assertSame( 'Solution draft', $labels->page_title( 'Cart', 6 ) );
		$this->assertSame( 'Proforma request', $labels->page_title( 'Checkout', 7 ) );
		$this->assertSame( 'About', $labels->page_title( 'About', 9 ) );

		WP_Mock::userFunction( 'is_page', array( 'return' => true ) );
		WP_Mock::userFunction( 'is_wc_endpoint_url', array( 'return' => false ) );
		WP_Mock::userFunction( 'get_queried_object_id', array( 'return' => 6 ) );
		$this->assertSame(
			array(
				'title' => 'Solution draft',
				'site'  => 'Linker',
			),
			$labels->document_title(
				array(
					'title' => 'Cart',
					'site'  => 'Linker',
				)
			)
		);
	}

	/**
	 * On the confirmation WooCommerce's crumb for the Proforma request page carries the stored title; it gets the page's name.
	 */
	public function test_breadcrumb(): void {
		WP_Mock::userFunction(
			'get_permalink',
			array(
				'return' => static fn ( int $page ): string => array(
					6 => 'https://example.test/cart/',
					7 => 'https://example.test/proforma-request/',
				)[ $page ] ?? '',
			)
		);

		$this->assertSame(
			array(
				array( 'Home', 'https://example.test/' ),
				array( 'Proforma request', 'https://example.test/proforma-request/' ),
				array( 'Inquiry received' ),
			),
			( new Labels() )->breadcrumb(
				array(
					array( 'Home', 'https://example.test/' ),
					array( 'Checkout', 'https://example.test/proforma-request/' ),
					array( 'Inquiry received' ),
				)
			)
		);
	}
}
