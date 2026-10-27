<?php
/**
 * Tests for the language-aware page addresses.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Presentation;

use Linker\Commerce\Presentation\PageUrls;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;
use WP_Post;

/**
 * Tests for PageUrls.
 *
 * @covers \Linker\Commerce\Presentation\PageUrls
 */
final class PageUrlsTest extends TestCase {

	/** A German REST turn must not inherit the request's English default. */
	public function test_explicit_language_resolves_the_native_twin(): void {
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'en' ) );
		WP_Mock::userFunction(
			'get_page_by_path',
			array(
				'args'   => array( 'solution-configurator' ),
				'return' => new WP_Post( (object) array( 'ID' => 33 ) ),
			)
		);
		WP_Mock::userFunction(
			'pll_get_post',
			array(
				'args'   => array( 33, 'de' ),
				'return' => 58,
			)
		);
		WP_Mock::userFunction(
			'get_permalink',
			array(
				'args'   => array( 58 ),
				'return' => 'http://linker.test/de/loesungskonfigurator/',
			)
		);
		$this->assertSame( 'http://linker.test/de/loesungskonfigurator/', PageUrls::translated( 'solution-configurator', 'de' ) );
	}

	/**
	 * German is the current language: home and pages are the German twins.
	 */
	public function test_home_and_page_in_german(): void {
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'de' ) );
		WP_Mock::userFunction(
			'pll_home_url',
			array(
				'args'   => array( 'de' ),
				'return' => 'http://linker.test/de/',
			)
		);
		WP_Mock::userFunction( 'trailingslashit', array( 'return' => static fn( string $url ): string => rtrim( $url, '/' ) . '/' ) );
		WP_Mock::userFunction(
			'get_page_by_path',
			array(
				'args'   => array( 'contact' ),
				'return' => new WP_Post( (object) array( 'ID' => 33 ) ),
			)
		);
		WP_Mock::userFunction(
			'pll_get_post',
			array(
				'args'   => array( 33, 'de' ),
				'return' => 58,
			)
		);
		WP_Mock::userFunction(
			'get_permalink',
			array(
				'args'   => array( 58 ),
				'return' => 'http://linker.test/de/kontakt/',
			)
		);

		$this->assertSame( 'http://linker.test/de/', PageUrls::home() );
		$this->assertSame( 'http://linker.test/de/kontakt/', PageUrls::translated( 'contact' ) );
		$this->assertSame( 'http://linker.test/de/kontakt/', PageUrls::page( 'contact' ) );
	}

	/**
	 * English is the current language: the English page itself.
	 */
	public function test_home_and_page_in_english(): void {
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'en' ) );
		WP_Mock::userFunction(
			'pll_home_url',
			array(
				'args'   => array( 'en' ),
				'return' => 'http://linker.test/',
			)
		);
		WP_Mock::userFunction( 'trailingslashit', array( 'return' => static fn( string $url ): string => rtrim( $url, '/' ) . '/' ) );
		WP_Mock::userFunction(
			'get_page_by_path',
			array(
				'args'   => array( 'contact' ),
				'return' => new WP_Post( (object) array( 'ID' => 33 ) ),
			)
		);
		WP_Mock::userFunction(
			'get_permalink',
			array(
				'args'   => array( 33 ),
				'return' => 'http://linker.test/contact/',
			)
		);

		$this->assertSame( 'http://linker.test/', PageUrls::home() );
		$this->assertSame( 'http://linker.test/contact/', PageUrls::translated( 'contact' ) );
		$this->assertSame( 'http://linker.test/contact/', PageUrls::page( 'contact' ) );
	}

	/**
	 * A missing page answers the language's home, never an English path the
	 * caller wrote out itself.
	 */
	public function test_a_missing_page_falls_back_to_its_language_home(): void {
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'de' ) );
		WP_Mock::userFunction(
			'pll_home_url',
			array(
				'args'   => array( 'de' ),
				'return' => 'http://linker.test/de/',
			)
		);
		WP_Mock::userFunction( 'trailingslashit', array( 'return' => static fn( string $url ): string => rtrim( $url, '/' ) . '/' ) );
		WP_Mock::userFunction(
			'get_page_by_path',
			array(
				'args'   => array( 'missing' ),
				'return' => null,
			)
		);

		$this->assertSame( '', PageUrls::translated( 'missing' ) );
		$this->assertSame( 'http://linker.test/de/', PageUrls::page( 'missing' ) );
	}

	/**
	 * Without Polylang the site has one language: WordPress's home.
	 */
	public function test_without_a_language_layer(): void {
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => false ) );
		WP_Mock::userFunction( 'pll_home_url', array( 'return' => '' ) );
		WP_Mock::userFunction(
			'home_url',
			array(
				'args'   => array( '/' ),
				'return' => 'http://linker.test/',
			)
		);

		$this->assertSame( 'http://linker.test/', PageUrls::home() );
	}
}
