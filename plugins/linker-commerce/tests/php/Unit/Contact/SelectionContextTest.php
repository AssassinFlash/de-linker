<?php
/**
 * Public source validation and the native Contact payload boundary.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
namespace Linker\Commerce\Tests\Unit\Contact;

use Linker\Commerce\Contact\SelectionContext;
use Linker\Commerce\Contact\Submission;
use Linker\Commerce\Protection\Fingerprint;
use Linker\Commerce\Protection\Identity;
use Linker\Commerce\Tests\TestCase;
use WP_Error;
use WP_Mock;
use WP_Post;
use WP_Term;

require_once dirname( __DIR__, 5 ) . '/linker-i18n/includes/Languages.php';

/**
 * Public selection normalization at the native Contact boundary.
 *
 * @covers \Linker\Commerce\Contact\SelectionContext
 */
final class SelectionContextTest extends TestCase {
	/**
	 * Native publication state may change before a POST.
	 *
	 * @var string
	 */
	private string $status = 'publish';
	/**
	 * Native password restriction.
	 *
	 * @var string
	 */
	private string $password = '';
	/**
	 * Native taxonomy public-view flag.
	 *
	 * @var bool
	 */
	private bool $viewable = true;
	/**
	 * Native static-front option; unrelated object tests keep their original fixture.
	 *
	 * @var bool
	 */
	private bool $static_front = false;
	/**
	 * The option may already be filtered to the request language.
	 *
	 * @var int
	 */
	private int $front_id = 14;
	/**
	 * Missing native home translation.
	 *
	 * @var bool
	 */
	private bool $missing_home = false;
	/** Current native public object answers, not a proposed browser title. */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
		WP_Mock::userFunction( 'home_url', array( 'return' => 'https://site.test/' ) );
		WP_Mock::userFunction( 'wp_parse_url', array( 'return' => static fn ( string $url, int $component = -1 ) => parse_url( $url, $component ) ) );
		WP_Mock::userFunction( 'url_to_postid', array( 'return' => static fn ( string $url ): int => str_contains( $url, '/products/' ) ? 12 : ( str_contains( $url, '/product/model/' ) ? 13 : 0 ) ) );
		WP_Mock::userFunction(
			'get_post',
			array(
				'return' => fn ( int $id ): WP_Post => new WP_Post(
					(object) array(
						'ID'            => $id,
						'post_type'     => in_array( $id, array( 12, 14, 15 ), true ) ? 'page' : 'product',
						'post_title'    => array(
							12 => 'Current products',
							14 => 'Home',
							15 => 'Startseite',
						)[ $id ] ?? 'Current model',
						'post_status'   => $this->status,
						'post_password' => $this->password,
					)
				),
			)
		);
		WP_Mock::userFunction( 'wc_get_page_id', array( 'return' => 12 ) );
		WP_Mock::userFunction(
			'get_permalink',
			array(
				'return' => static fn ( $post ): string => array(
					12 => 'https://site.test/products/',
					14 => 'https://site.test/',
					15 => 'https://site.test/de/home/',
				)[ $post instanceof WP_Post ? $post->ID : $post ] ?? 'https://site.test/product/model/',
			)
		);
		WP_Mock::userFunction( 'get_the_title', array( 'return' => static fn ( WP_Post $post ): string => $post->post_title ) );
		WP_Mock::userFunction( 'get_object_taxonomies', array( 'return' => array( 'product_cat', 'language' ) ) );
		WP_Mock::userFunction( 'is_taxonomy_viewable', array( 'return' => fn (): bool => $this->viewable ) );
		WP_Mock::userFunction(
			'get_term_by',
			array(
				'return' => static fn ( string $field, string $slug, string $taxonomy ) => in_array( $slug, array( 'batteries', 'de' ), true ) ? new WP_Term(
					(object) array(
						'term_id'  => 'de' === $slug ? 528 : 8,
						'name'     => 'de' === $slug ? 'Deutsch' : 'Battery systems',
						'slug'     => $slug,
						'taxonomy' => $taxonomy,
					)
				) : false,
			)
		);
		WP_Mock::userFunction( 'get_term_link', array( 'return' => static fn ( $term ): string => 528 === ( $term instanceof WP_Term ? $term->term_id : $term ) ? 'https://site.test/de/' : 'https://site.test/product-category/batteries/' ) );
		WP_Mock::userFunction( 'sanitize_key', array( 'return' => static fn ( string $value ): string => strtolower( preg_replace( '/[^a-z0-9_-]/i', '', $value ) ?? '' ) ) );
		WP_Mock::userFunction( 'sanitize_text_field', array( 'return' => static fn ( string $value ): string => trim( strip_tags( $value ) ) ) );
		WP_Mock::userFunction( 'sanitize_textarea_field', array( 'return' => static fn ( string $value ): string => trim( strip_tags( $value ) ) ) );
		// New native add_query_arg values arrive encoded, unlike http_build_query inputs.
		WP_Mock::userFunction( 'add_query_arg', array( 'return' => static fn ( array $query, string $url ): string => $url . ( array() === $query ? '' : '?' . implode( '&', array_map( static fn ( $key, $value ): string => $key . '=' . $value, array_keys( $query ), $query ) ) ) ) );
		WP_Mock::userFunction( 'wp_json_encode', array( 'return' => static fn ( $value ) => json_encode( $value ) ) );
		WP_Mock::userFunction( 'is_email', array( 'return' => static fn ( string $email ): bool => false !== filter_var( $email, FILTER_VALIDATE_EMAIL ) ) );
		WP_Mock::userFunction( 'determine_locale', array( 'return' => 'en_US' ) );
		WP_Mock::userFunction( 'get_option', array( 'return' => fn ( string $key ) => 'show_on_front' === $key ? ( $this->static_front ? 'page' : 'posts' ) : ( 'page_on_front' === $key ? $this->front_id : false ) ) );
		WP_Mock::userFunction( 'pll_languages_list', array( 'return' => array( 'en', 'de' ) ) );
		WP_Mock::userFunction( 'pll_get_post', array( 'return' => fn ( int $id, string $language ): int => ! $this->missing_home && in_array( $id, array( 14, 15 ), true ) ? ( 'de' === $language ? 15 : 14 ) : 0 ) );
		WP_Mock::userFunction( 'trailingslashit', array( 'return' => static fn ( string $url ): string => rtrim( $url, '/' ) . '/' ) );
		WP_Mock::userFunction(
			'PLL',
			array(
				'return' => (object) array(
					'links_model' => new class() {
						/**
						 * Native links-model home URLs do not depend on the current request.
						 *
						 * @param string $language Requested language slug.
						 */
						public function home_url( string $language ): string {
							return 'https://site.test/' . ( 'de' === $language ? 'de/' : '' );
						}
					},
				),
			)
		);
		WP_Mock::userFunction( 'wp_salt', array( 'return' => 'private-test-salt' ) );
	}

	/** All public object types keep canonical title and only selected navigation fields. */
	public function test_resolves_shop_product_and_category_and_strips_transport(): void {
		foreach ( array( 'products', 'product/model', 'product-category/batteries' ) as $path ) {
			$context = SelectionContext::normalize(
				array(
					'source'    => 'https://site.test/' . $path . '/?token=secret#x',
					'title'     => 'FORGED',
					'selection' => array(
						'q'           => 'SAJ',
						'brand'       => 'SAJ',
						'kw_min'      => '5,5',
						'sort'        => 'power-desc',
						'token'       => 'secret',
						'application' => array( 'bad' ),
						'kw_max'      => 'INF',
					),
				)
			);
			$this->assertNotEmpty( $context );
			$this->assertNotSame( 'FORGED', $context['title'] );
			$this->assertSame(
				array(
					'brand'  => 'saj',
					'kw_min' => 5.5,
					'q'      => 'SAJ',
					'sort'   => 'power-desc',
				),
				$context['selection']
			);
			$this->assertStringNotContainsString( 'secret', $context['url'] );
		}
	}

	/** Origin, canonical path and current public object are required on GET and POST. */
	public function test_rejects_foreign_or_noncanonical_sources(): void {
		foreach ( array( 'https://evil.test/products/', 'http://site.test/products/', 'https://site.test:444/products/', 'https://user@site.test/products/', '//site.test/products/', 'javascript:alert(1)', 'https://site.test/fake/products/', 'https://site.test/unknown/', array( 'https://site.test/products/' ) ) as $source ) {
			$this->assertSame( array(), SelectionContext::normalize( array( 'source' => $source ) ) );
		}
		$this->assertSame( array(), SelectionContext::query( array( SelectionContext::FIELD => '{broken' ) ) );
	}

	/** A formerly public object must still be public when the form is submitted. */
	public function test_no_longer_public_sources_are_rejected(): void {
		$this->status = 'private';
		$this->assertSame( array(), SelectionContext::normalize( array( 'source' => 'https://site.test/product/model/' ) ) );
		$this->status   = 'publish';
		$this->password = 'restricted';
		$this->assertSame( array(), SelectionContext::normalize( array( 'source' => 'https://site.test/product/model/' ) ) );
		$this->viewable = false;
		$this->assertSame( array(), SelectionContext::normalize( array( 'source' => 'https://site.test/product-category/batteries/' ) ) );
	}

	/** Long real searches retain their value; exceeding native recovery capacity is explicit invalidity. */
	public function test_search_is_not_silently_truncated_to_a_short_contact_field(): void {
		$q       = str_repeat( 'x', 250 );
		$context = SelectionContext::normalize(
			array(
				'source'    => 'https://site.test/products/',
				'selection' => array( 'q' => $q ),
			)
		);
		$this->assertSame( $q, $context['selection']['q'] );
		$this->assertSame(
			array(),
			SelectionContext::normalize(
				array(
					'source'    => 'https://site.test/products/',
					'selection' => array( 'q' => str_repeat( 'x', Submission::MAX_MESSAGE ) ),
				)
			)
		);
	}

	/** Existing links arrive, while their browser title is never authoritative. */
	public function test_existing_contact_link_shape_is_consumed(): void {
		$context = SelectionContext::query(
			array(
				'source'  => 'https://site.test/products/',
				'title'   => 'Forged title',
				'search'  => 'No matching model',
				'filters' => array( 'phase' => '3' ),
				'sort'    => 'name',
			)
		);
		$this->assertSame( 'Current products', $context['title'] );
		$this->assertSame(
			array(
				'phase' => '3',
				'q'     => 'No matching model',
				'sort'  => 'name',
			),
			$context['selection']
		);
	}

	/** A language-root collision must resolve the native static page and its actual title. */
	public function test_static_home_pair_precedes_url_to_postid_and_language_taxonomy(): void {
		$this->static_front = true;
		foreach ( array( 14, 15 ) as $front ) {
			$this->front_id = $front;
			foreach ( array( 'en', 'de' ) as $language ) {
				$url     = 'https://site.test/' . ( 'de' === $language ? 'de/' : '' );
				$context = SelectionContext::normalize(
					array(
						'source' => $url . '?token=discard#old',
						'title'  => 'Forged',
					)
				);
				$this->assertSame( 'page', $context['type'] );
				$this->assertSame( 'de' === $language ? 15 : 14, $context['id'] );
				$this->assertSame( 'de' === $language ? 'Startseite' : 'Home', $context['title'] );
				$this->assertSame( $url, $context['source'] );
			}
		}
	}

	/** Unpublished, protected and missing homes cannot fall back to the public language term. */
	public function test_unavailable_static_home_does_not_become_a_taxonomy_source(): void {
		$this->static_front = true;
		$this->status       = 'private';
		$this->assertSame( array(), SelectionContext::normalize( array( 'source' => 'https://site.test/de/' ) ) );
		$this->status   = 'publish';
		$this->password = 'restricted';
		$this->assertSame( array(), SelectionContext::normalize( array( 'source' => 'https://site.test/de/' ) ) );
		$this->password     = '';
		$this->missing_home = true;
		$this->assertSame( array(), SelectionContext::normalize( array( 'source' => 'https://site.test/de/' ) ) );
		$this->missing_home = false;
		$this->front_id     = 0;
		$this->assertSame( array(), SelectionContext::normalize( array( 'source' => 'https://site.test/de/' ) ) );
	}

	/** Contact language switching preserves a verified homepage and the selected search. */
	public function test_home_language_switch_uses_the_root_instead_of_the_front_page_slug(): void {
		$this->static_front = true;
		foreach ( array( 'en', 'de' ) as $language ) {
			$source = 'https://site.test/' . ( 'de' === $language ? 'de/' : '' );
			WP_Mock::expectFilter( 'pll_translation_url', $source, $language );
			$result = SelectionContext::language_query(
				array(
					'source' => 'https://site.test/',
					'intent' => 'offer',
					'search' => 'SAJ + 5',
				),
				$language
			);
			$this->assertSame( 'offer', $result['intent'] );
			$transport = json_decode( $result[ SelectionContext::FIELD ], true );
			$this->assertSame( $source, $transport['source'] );
			$this->assertSame( array( 'q' => 'SAJ + 5' ), $transport['selection'] );
			$this->assertSame( 'page', SelectionContext::normalize( $transport )['type'] );
		}
	}

	/** Message stays independent; exclusion changes the normalized protected fingerprint. */
	public function test_submission_separates_context_and_fingerprints_the_choice(): void {
		$post     = array(
			'name'                          => 'Maria',
			'email'                         => 'maria@example.test',
			'message'                       => "My own question\nWith a second line",
			'consent'                       => '1',
			SelectionContext::FIELD         => json_encode(
				array(
					'source'    => 'https://site.test/products/',
					'selection' => array(
						'q'    => 'SAJ',
						'sort' => 'name',
					),
				)
			),
			SelectionContext::INCLUDE_FIELD => '1',
		);
		$included = Submission::from_post( $post );
		$removed  = $post;
		unset( $removed[ SelectionContext::FIELD ] );
		$excluded = Submission::from_post( $removed );
		$this->assertInstanceOf( Submission::class, $included );
		$this->assertInstanceOf( Submission::class, $excluded );
		$this->assertSame( $post['message'], $included->message );
		$this->assertSame( $post['message'], $excluded->message );
		$this->assertSame( array(), $excluded->selection() );
		$this->assertArrayNotHasKey( 'selection', get_object_vars( $excluded ), 'Existing empty-context fingerprints retain their exact semantic shape.' );
		$this->assertSame( get_object_vars( $included ), get_object_vars( $excluded ) );
		$identity = new Identity( hash( 'sha256', 'synthetic-browser' ), '' );
		$this->assertNotSame( Fingerprint::make( $identity, 'contact', array_merge( get_object_vars( $included ), array( 'selection' => $included->selection() ) ) ), Fingerprint::make( $identity, 'contact', get_object_vars( $excluded ) ) );
		$this->assertInstanceOf( WP_Error::class, Submission::from_post( array_replace( $post, array( SelectionContext::FIELD => '{bad' ) ) ) );
		$this->assertInstanceOf( Submission::class, Submission::from_post( $removed ) );
		$inquiry = Submission::from_post( $post, false );
		$handoff = Submission::from_handoff( $post );
		$this->assertInstanceOf( Submission::class, $inquiry );
		$this->assertInstanceOf( Submission::class, $handoff );
		$this->assertSame( array(), $inquiry->selection(), 'The inquiry door does not import Contact context.' );
		$this->assertSame( array(), $handoff->selection(), 'The Genie door does not import Contact context.' );
	}
}
