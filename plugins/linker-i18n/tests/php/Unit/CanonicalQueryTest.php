<?php
/**
 * Tests for query values surviving the language canonical redirect.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Unit;

use Linker\I18n\CanonicalQuery;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for CanonicalQuery.
 *
 * @covers \Linker\I18n\CanonicalQuery
 */
final class CanonicalQueryTest extends TestCase {

	/**
	 * The WordPress address helpers, reduced to what the filter reads.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::userFunction( 'wp_parse_url', array( 'return' => static fn( string $url, int $component = -1 ) => -1 === $component ? parse_url( $url ) : parse_url( $url, $component ) ) ); // phpcs:ignore WordPress.WP.AlternativeFunctions.parse_url_parse_url -- stands in for wp_parse_url.
		WP_Mock::userFunction( 'home_url', array( 'return' => 'http://example.test/' ) );
	}

	/**
	 * Polylang's remove_language_from_link() strips "/de" from every match in
	 * the string, the query's URL value included; the value is restored.
	 */
	public function test_a_same_site_url_value_keeps_its_language_segment(): void {
		$requested = 'http://example.test/de/kontakt/?intent=product&source=https%3A%2F%2Fexample.test%2Fde%2Fprodukt%2Fsaj-b2-10-0-hv1%2F';
		$redirect  = 'http://example.test/de/kontakt/?intent=product&source=https%3A%2F%2Fexample.test%2Fprodukt%2Fsaj-b2-10-0-hv1%2F';

		$this->assertSame( $requested, ( new CanonicalQuery() )->restore( $redirect, $requested ) );
	}

	/**
	 * A relative same-site URL value is restored the same way.
	 */
	public function test_a_relative_url_value_keeps_its_language_segment(): void {
		$requested = 'http://example.test/de/kontakt/?source=%2Fde%2Fprodukt%2Fsaj%2F';
		$redirect  = 'http://example.test/de/kontakt/?source=%2Fprodukt%2Fsaj%2F';

		$this->assertSame( $requested, ( new CanonicalQuery() )->restore( $redirect, $requested ) );
	}

	/**
	 * A query WordPress itself rewrites stays rewritten: only the language
	 * removal is undone.
	 */
	public function test_other_query_changes_are_kept(): void {
		$requested = 'http://example.test/de/kontakt/?paged=2&source=%2Fde%2Fprodukt%2Fsaj%2F';
		$redirect  = 'http://example.test/de/kontakt/?paged=3&source=%2Fprodukt%2Fsaj%2F';

		$restored = ( new CanonicalQuery() )->restore( $redirect, $requested );
		$this->assertIsString( $restored );

		$this->assertStringContainsString( 'paged=3', $restored );
		$this->assertStringContainsString( 'source=%2Fde%2Fprodukt%2Fsaj%2F', $restored );
	}

	/**
	 * An external value is not this site's address and is left alone.
	 */
	public function test_an_external_value_is_left_alone(): void {
		$requested = 'http://example.test/de/kontakt/?source=https%3A%2F%2Fother.test%2Fde%2Fx%2F';
		$redirect  = 'http://example.test/de/kontakt/?source=https%3A%2F%2Fother.test%2Fx%2F';

		$this->assertSame( $redirect, ( new CanonicalQuery() )->restore( $redirect, $requested ) );
	}

	/**
	 * Polylang answers false when it redirects nowhere; it stays false.
	 */
	public function test_no_redirect_stays_no_redirect(): void {
		$this->assertFalse( ( new CanonicalQuery() )->restore( false, 'http://example.test/de/kontakt/' ) );
	}
}
