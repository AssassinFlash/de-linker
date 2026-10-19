<?php
/**
 * Tests for the company website field.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Registration;

use Linker\Commerce\Registration\Website;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * The website is one of the two verification values (#224); it is stored as a
 * URL so the team's "Company website" link opens it.
 *
 * @covers \Linker\Commerce\Registration\Website
 */
final class WebsiteTest extends TestCase {

	/**
	 * WordPress's URL parser is PHP's.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
		WP_Mock::userFunction(
			'wp_parse_url',
			array(
				'return' => static fn ( string $url, int $component = -1 ) => parse_url( $url, $component ),
			)
		);
	}

	/**
	 * A bare domain gets https://; a pasted URL keeps its own scheme.
	 */
	public function test_normalize_adds_https_to_a_bare_domain(): void {
		$this->assertSame( 'https://example.com', Website::normalize( 'example.com' ) );
		$this->assertSame( 'https://example.com/legal', Website::normalize( 'https://example.com/legal' ) );
		$this->assertSame( 'http://example.com', Website::normalize( 'http://example.com' ) );
		$this->assertSame( '', Website::normalize( '   ' ) );
	}

	/**
	 * Only an http(s) address with a dotted host is a website the team can open.
	 */
	public function test_valid_requires_a_dotted_http_host(): void {
		$this->assertTrue( Website::valid( 'example.com' ) );
		$this->assertTrue( Website::valid( 'https://sub.example.co.uk/path?q=1' ) );
		$this->assertFalse( Website::valid( 'not a site' ) );
		$this->assertFalse( Website::valid( 'ftp://example.com' ) );
		$this->assertFalse( Website::valid( 'https://example' ) );
		$this->assertFalse( Website::valid( 'https://user:pass@example.com' ) );
		$this->assertFalse( Website::valid( '' ) );
	}
}
