<?php
/**
 * Tests for the German dynamic template resolver.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Unit;

use Linker\I18n\DynamicTemplates;
use Linker\I18n\Languages;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for DynamicTemplates.
 *
 * @covers \Linker\I18n\DynamicTemplates
 */
final class DynamicTemplatesTest extends TestCase {

	/**
	 * The English cart template LiveCanvas's own lookup returns.
	 */
	private const TEMPLATE = 6565;

	/**
	 * Polylang with both languages, and the one WordPress function the
	 * resolver calls.
	 */
	private function wordpress(): void {
		PolylangDouble::mock();
	}

	/**
	 * A resolver that decides the page type itself: WooCommerce's
	 * conditionals are not loaded in a unit test.
	 *
	 * @param string|null $page_type The WooCommerce conditional that matches, or null.
	 */
	private function resolver( ?string $page_type ): DynamicTemplates {
		return new DynamicTemplates(
			new Languages(),
			static fn( string $conditional ): bool => $conditional === $page_type
		);
	}

	/**
	 * The slug of the language Polylang holds as current.
	 */
	private function current(): string {
		return (string) PolylangDouble::$polylang->curlang->get_prop( 'slug' );
	}

	/**
	 * A German cart request whose own lookup found nothing renders through
	 * the English cart template.
	 */
	public function test_a_german_cart_without_a_template_renders_through_the_english_one(): void {
		$this->wordpress();
		PolylangDouble::$polylang->curlang = PolylangDouble::language( Languages::TARGET );
		WP_Mock::userFunction( 'is_cart' )->andReturn( true );
		$seen = null;
		WP_Mock::userFunction(
			'get_posts',
			array(
				'return' => static function ( array $args ) use ( &$seen ) {
					$seen = $args;
					return array( PolylangDouble::post( self::TEMPLATE ) );
				},
			)
		);

		$resolved = $this->resolver( 'is_cart' )->template( false );

		$this->assertSame(
			array(
				'post_type'        => 'lc_dynamic_template',
				// phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_key -- the key the resolver must look up by.
				'meta_key'         => 'is_cart_page',
				'orderby'          => 'menu_order',
				'numberposts'      => 1,
				'post_status'      => 'publish',
				'suppress_filters' => false,
			),
			$seen
		);

		$this->assertSame( self::TEMPLATE, $resolved );
		$this->assertSame( Languages::TARGET, $this->current() );
	}

	/**
	 * A template LiveCanvas already resolved is never replaced, even on a
	 * German cart request.
	 */
	public function test_a_resolved_template_is_kept(): void {
		$this->wordpress();

		$resolved = $this->resolver( 'is_cart' )->template( 6915 );

		$this->assertSame( 6915, $resolved );
	}

	/**
	 * An English request keeps whatever LiveCanvas resolved: its lookup
	 * already sees the English templates.
	 */
	public function test_an_english_request_is_left_alone(): void {
		$this->wordpress();

		$resolved = $this->resolver( 'is_cart' )->template( false );

		$this->assertFalse( $resolved );
	}

	/**
	 * A German request that is not one of the four WooCommerce page types is
	 * left unresolved, so its own template path stands.
	 */
	public function test_a_german_page_that_is_not_a_woo_page_is_left_alone(): void {
		$this->wordpress();
		PolylangDouble::$polylang->curlang = PolylangDouble::language( Languages::TARGET );

		$resolved = $this->resolver( null )->template( false );

		$this->assertFalse( $resolved );
	}

	/**
	 * A German cart whose English template is also missing stays unresolved
	 * rather than being pointed at nothing.
	 */
	public function test_a_missing_english_template_stays_unresolved(): void {
		$this->wordpress();
		PolylangDouble::$polylang->curlang = PolylangDouble::language( Languages::TARGET );
		WP_Mock::userFunction( 'get_posts', array( 'return' => array() ) );

		$resolved = $this->resolver( 'is_cart' )->template( false );

		$this->assertFalse( $resolved );
		$this->assertSame( Languages::TARGET, $this->current() );
	}
}
