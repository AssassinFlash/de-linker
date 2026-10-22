<?php
/**
 * Selection is readable and removable in the form and separate in native team records.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
namespace Linker\Commerce\Tests\Unit\Contact;

use Linker\Commerce\Contact\SelectionContext;
use Linker\Commerce\Contact\SelectionView;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WP_Mock;

/**
 * Real semantic view, with native escaping substitutes rather than passthrough.
 *
 * @covers \Linker\Commerce\Contact\SelectionView
 */
final class SelectionViewTest extends TestCase {
	/** Native escaping and translated labels. */
	public function setUp(): void {
		parent::setUp();
		foreach ( array( '__', 'wp_kses_post' ) as $function ) {
			WP_Mock::passthruFunction( $function );
		}
		foreach ( array( 'esc_html__', 'esc_html', 'esc_attr', 'esc_url' ) as $function ) {
			WP_Mock::userFunction( $function, array( 'return' => static fn ( string $value ): string => htmlspecialchars( $value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8' ) ) );
		}
		WP_Mock::userFunction( '_n', array( 'return' => static fn ( string $singular ): string => $singular ) );
		WP_Mock::userFunction( 'wp_json_encode', array( 'return' => static fn ( $value ) => json_encode( $value ) ) );
	}

	/** Native toggle has explicit include/exclude state and never turns search into HTML. */
	public function test_form_has_an_explicit_removable_selection(): void {
		$context = array(
			'source'    => 'https://site/products/',
			'url'       => 'https://site/products/?q=SAJ',
			'title'     => 'Products',
			'selection' => array(
				'q'     => '<img src=x onerror=alert(1)>',
				'sort'  => 'name',
				'phase' => '3',
				'power' => 'low',
			),
		);
		$html    = SelectionView::form( $context, '', true );
		$this->assertStringContainsString( 'name="' . SelectionContext::INCLUDE_FIELD . '" value="0"', $html );
		$this->assertStringContainsString( ' checked /><span>', $html );
		$this->assertStringNotContainsString( 'type="hidden" name="' . SelectionContext::FIELD . '"', $html );
		$this->assertStringContainsString( 'This selection will not be sent.', $html );
		$this->assertStringContainsString( '&lt;img src=x', $html );
		$this->assertStringNotContainsString( '<img', $html );
		$this->assertStringContainsString( '3-phase', $html );
		$this->assertStringContainsString( 'Up to 6 kW', $html );
		$this->assertStringNotContainsString( ' checked', SelectionView::form( $context, '', false ) );
		$this->assertStringContainsString( 'This selection could not be loaded.', SelectionView::form( array(), '{invalid', true ) );
	}

	/**
	 * The same data reaches native admin/team consumers; customer receipt remains fixed.
	 *
	 * @dataProvider storage_formats
	 * @param bool $json Native string format or compatible legacy array.
	 */
	public function test_native_team_and_admin_read_the_independent_meta_only( bool $json ): void {
		$needle  = 'A & B "quoted" \\ Rückfrage';
		$context = array(
			'title'     => 'Products',
			'url'       => 'https://site/products/?q=SAJ',
			'selection' => array(
				'q'    => $needle,
				'sort' => 'name',
			),
		);
		$order   = Mockery::mock( \WC_Order::class );
		$order->shouldReceive( 'get_meta' )->with( SelectionContext::META )->andReturn( $json ? json_encode( $context ) : $context );
		$view = new SelectionView();
		ob_start();
		$view->email( $order, false, false, null );
		$this->assertSame( '', ob_get_clean() );
		ob_start();
		$view->email( $order, true, true, null );
		$this->assertStringContainsString( 'Search: ' . $needle . "\nSort products: Name A-Z", (string) ob_get_clean() );
		ob_start();
		$view->admin( $order );
		$this->assertStringContainsString( 'https://site/products/?q=SAJ', (string) ob_get_clean() );
		$this->assertSame( array( SelectionContext::META => 'text' ), $view->erase( array() ) );
	}

	/**
	 * The new native string and the originally reviewed array remain readable.
	 *
	 * @return array<string,array{bool}>
	 */
	public function storage_formats(): array {
		return array(
			'native-json-string' => array( true ),
			'legacy-array'       => array( false ),
		);
	}
}
