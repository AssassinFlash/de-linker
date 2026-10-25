<?php
/**
 * Tests for REST in one language.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Unit\Rest;

use Linker\I18n\Languages;
use Linker\I18n\Rest\RestLang;
use Linker\I18n\Tests\Unit\PolylangDouble;
use Mockery;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for RestLang and the language switch of Languages.
 *
 * @covers \Linker\I18n\Rest\RestLang
 * @covers \Linker\I18n\Languages
 */
final class RestLangTest extends TestCase {

	/**
	 * A REST request with a lang parameter.
	 *
	 * @param mixed $lang The parameter, null for none.
	 * @return \WP_REST_Request<array<string, mixed>>&\Mockery\MockInterface
	 */
	private function request( $lang ) {
		$request = Mockery::mock( 'WP_REST_Request' );
		$request->shouldReceive( 'get_param' )->with( 'lang' )->andReturn( $lang );
		return $request;
	}

	/**
	 * A query for posts of a type, with the variables it already has.
	 *
	 * @param array<string, mixed> $vars Query variables.
	 * @return \WP_Query&\Mockery\MockInterface
	 */
	private function query( array $vars ) {
		$query = Mockery::mock( \WP_Query::class );
		$query->shouldReceive( 'get' )->andReturnUsing( static fn( string $name ) => $vars[ $name ] ?? '' );
		return $query;
	}

	/**
	 * The language a request lists: the parameter, all, or the current language.
	 */
	public function test_language_of_request(): void {
		PolylangDouble::mock( array(), array(), array(), array(), 'en' );
		$rest = new RestLang( new Languages() );

		$this->assertSame( 'de', $rest->language_of( $this->request( 'de' ) ) );
		$this->assertNull( $rest->language_of( $this->request( 'all' ) ) );
		$this->assertSame( 'en', $rest->language_of( $this->request( 'fr' ) ) );
		$this->assertSame( 'en', $rest->language_of( $this->request( null ) ) );
	}

	/**
	 * Inside a German request, product lists are German and the locale is German;
	 * leaving the request restores both.
	 */
	public function test_lists_in_the_request_language(): void {
		PolylangDouble::mock( array(), array(), array(), array(), 'en' );
		WP_Mock::userFunction(
			'switch_to_locale',
			array(
				'times'  => 1,
				'args'   => array( 'de_DE_formal' ),
				'return' => true,
			)
		);
		WP_Mock::userFunction( 'restore_previous_locale', array( 'times' => 1 ) );
		WP_Mock::userFunction( 'determine_locale', array( 'return' => 'en_US' ) );
		$rest = new RestLang( new Languages() );

		$rest->enter( null, array(), $this->request( 'de' ) );
		$products = $this->query( array( 'post_type' => 'product' ) );
		$products->shouldReceive( 'set' )->once()->with( 'lang', 'de' );
		$rest->posts( $products );
		$this->assertSame(
			array(
				'taxonomy' => 'product_cat',
				'lang'     => 'de',
			),
			$rest->terms( array( 'taxonomy' => 'product_cat' ), array( 'product_cat' ) )
		);
		$this->assertSame( PolylangDouble::language( 'de' ), PolylangDouble::$polylang->curlang );

		$this->assertSame( 'response', $rest->leave( 'response' ) );
		$this->assertSame( PolylangDouble::language( 'en' ), PolylangDouble::$polylang->curlang );
		$this->assertSame( array( 'de_DE_formal', 'en_US' ), PolylangDouble::$polylang->loaded );
		$untouched = $this->query( array( 'post_type' => 'product' ) );
		$untouched->shouldNotReceive( 'set' );
		$rest->posts( $untouched );
	}

	/**
	 * Queries by ID, queries naming a language, untranslated types and
	 * ?lang=all are left alone.
	 */
	public function test_queries_left_alone(): void {
		PolylangDouble::mock( array(), array(), array(), array(), 'en', array( 'attachment' => false ) );
		WP_Mock::userFunction( 'switch_to_locale', array( 'return' => false ) );
		WP_Mock::userFunction( 'determine_locale', array( 'return' => 'en_US' ) );
		$rest = new RestLang( new Languages() );
		$rest->enter( null, array(), $this->request( 'en' ) );

		foreach ( array(
			array(
				'post_type' => 'product',
				'post__in'  => array( 1 ),
			),
			array(
				'post_type' => 'page',
				'lang'      => 'de',
			),
			array( 'post_type' => 'attachment' ),
		) as $vars ) {
			$query = $this->query( $vars );
			$query->shouldNotReceive( 'set' );
			$rest->posts( $query );
		}
		$this->assertSame( array( 'object_ids' => array( 3 ) ), $rest->terms( array( 'object_ids' => array( 3 ) ), array( 'product_cat' ) ) );

		$rest->enter( null, array(), $this->request( 'all' ) );
		$all = $this->query( array( 'post_type' => 'product' ) );
		$all->shouldNotReceive( 'set' );
		$rest->posts( $all );
	}

	/** Internal authority queries are all-language; public parameters grant no bypass. */
	public function test_publication_scope_is_a_server_query_marker(): void {
		PolylangDouble::mock( array(), array(), array(), array(), 'en' );
		WP_Mock::userFunction( 'switch_to_locale', array( 'return' => false ) );
		WP_Mock::userFunction( 'determine_locale', array( 'return' => 'en_US' ) );
		$rest    = new RestLang( new Languages() );
		$request = $this->request( 'de' );
		$request->shouldReceive( 'get_param' )->with( 'linker_publication_internal' )->never();
		$rest->enter( null, array(), $request );
		$internal = $this->query(
			array(
				'post_type'                   => 'product',
				'lang'                        => '',
				'linker_publication_internal' => true,
			)
		);
		$internal->shouldNotReceive( 'set' );
		$rest->posts( $internal );
		$public = $this->query( array( 'post_type' => 'product' ) );
		$public->shouldReceive( 'set' )->once()->with( 'lang', 'de' );
		$rest->posts( $public );
		$string_marker = $this->query(
			array(
				'post_type'                   => 'product',
				'linker_publication_internal' => '1',
			)
		);
		$string_marker->shouldReceive( 'set' )->once()->with( 'lang', 'de' );
		$rest->posts( $string_marker );
		$this->assertSame( PolylangDouble::language( 'de' ), PolylangDouble::$polylang->curlang );
	}
}
