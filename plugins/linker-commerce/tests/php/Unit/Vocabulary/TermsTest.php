<?php
/**
 * Tests for the site's words.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Vocabulary;

use Linker\Commerce\Tests\TestCase;
use Linker\Commerce\Vocabulary\Terms;
use WP_Mock;

/**
 * Tests for Terms.
 *
 * @covers \Linker\Commerce\Vocabulary\Terms
 */
final class TermsTest extends TestCase {

	/**
	 * Translations return their source string; _n_noop() builds WordPress's nooped array.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::passthruFunction( '__' );
		WP_Mock::userFunction(
			'_n_noop',
			array(
				'return' => static fn ( string $singular, string $plural, string $domain ): array => array(
					0          => $singular,
					1          => $plural,
					'singular' => $singular,
					'plural'   => $plural,
					'context'  => null,
					'domain'   => $domain,
				),
			)
		);
	}

	/**
	 * A replacement takes the same arguments as the string it replaces, so WooCommerce's sprintf() still fits.
	 */
	public function test_replacements_keep_the_placeholders(): void {
		$terms = new Terms();
		foreach ( $terms->singular() as $source => $replacement ) {
			$this->assertSame( self::placeholders( $source ), self::placeholders( $replacement ), $source );
		}
		foreach ( $terms->plural() as $source => $nooped ) {
			$this->assertSame( self::placeholders( $source ), self::placeholders( (string) $nooped['singular'] ), $source );
			$this->assertSame( self::placeholders( $source ), self::placeholders( (string) $nooped['plural'] ), $source );
			$this->assertSame( 'linker-commerce', $nooped['domain'] );
		}
	}

	/**
	 * No replacement speaks of carts, orders, checkout, payment or shipping (docs/specs/11-commerce.md, acceptance).
	 */
	public function test_replacements_avoid_the_banned_words(): void {
		$terms = new Terms();
		$texts = array_merge( array_values( $terms->singular() ), array_column( $terms->plural(), 'singular' ), array_column( $terms->plural(), 'plural' ) );
		foreach ( $texts as $text ) {
			$this->assertDoesNotMatchRegularExpression( '/\b(orders?|cart|checkout|payment|pay|shipping|basket)\b/i', (string) $text );
		}
	}

	/**
	 * The vocabulary of AGENTS.md §3 is used for WooCommerce's key strings.
	 */
	public function test_key_words(): void {
		$singular = ( new Terms() )->singular();

		$this->assertSame( 'Add to solution draft', $singular['Add to cart'] );
		$this->assertSame( 'Request Proforma', $singular['Place order'] );
		$this->assertSame( 'Request again', $singular['Order again'] );
		$this->assertSame( 'Inquiries', $singular['Orders'] );
		$this->assertSame( 'Your solution draft is empty.', $singular['Your cart is currently empty.'] );
		// The confirmation link of the email a guest opens names the inquiry, never an order (review 2026-10-10).
		$this->assertSame(
			'Please log in to your account to view this inquiry.',
			$singular['Please log in to your account to view this order.']
		);
	}

	/**
	 * The printf placeholders of a string, in order.
	 *
	 * @param string $text String.
	 * @return list<string>
	 */
	private static function placeholders( string $text ): array {
		preg_match_all( '/%(?:\d+\$)?[sd]/', $text, $matches );
		$found = $matches[0];
		sort( $found );
		return $found;
	}
}
