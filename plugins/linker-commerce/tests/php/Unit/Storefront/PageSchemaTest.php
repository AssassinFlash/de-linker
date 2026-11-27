<?php
/**
 * Public page graph contracts.
 *
 * @package Linker\Commerce
 */

namespace Linker\Commerce\Tests\Unit\Storefront;

use Linker\Commerce\Presentation\ContactChannels;
use Linker\Commerce\Storefront\PageSchema;
use WP_Mock;
use WP_Mock\Tools\TestCase;
use WP_Post;

/**
 * Keep translated navigation and visible labels in the structured data.
 *
 * @covers \Linker\Commerce\Storefront\PageSchema
 */
final class PageSchemaTest extends TestCase {

	/** Both languages identify one publisher and preserve both public team contacts. */
	public function test_organization_retains_the_graph_id_and_public_contacts(): void {
		WP_Mock::userFunction( 'is_front_page', array( 'return' => false ) );
		WP_Mock::userFunction( 'get_option' )->andReturnUsing(
			static fn( $key ) => match ( $key ) {
			'home' => 'https://example.org/',
			'seopress_social_option_name' => array( 'seopress_social_knowledge_img' => 'https://example.org/logo.png' ),
			default => 'sales@de-linker.com' }
		);
		WP_Mock::userFunction( 'attachment_url_to_postid' )->with( 'https://example.org/logo.png' )->andReturn( 17 );
		WP_Mock::userFunction( 'wp_get_attachment_metadata' )->with( 17 )->andReturn(
			array(
				'width'  => 717,
				'height' => 354,
			)
		);
		WP_Mock::userFunction( 'sanitize_email', array( 'return_arg' => 0 ) );
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'en' ) );
		WP_Mock::userFunction( 'pll_home_url', array( 'return' => 'https://example.org/' ) );
		WP_Mock::userFunction( 'trailingslashit', array( 'return_arg' => 0 ) );
		$node = ( new PageSchema() )->organization(
			array(
				'logo'  => '%%social_knowledge_image%%',
				'@id'   => 'https://example.org/de/#organization',
				'taxID' => 'DE367367711',
			)
		);
		$this->assertSame( 'https://example.org/#organization', $node['@id'] );
		$this->assertSame( '2024-01-24', $node['foundingDate'] );
		$this->assertArrayNotHasKey( 'taxID', $node );
		$this->assertSame( 'Sachsen-Anhalt', $node['address']['addressRegion'] );
		$this->assertSame( array( 'DE', 'AT', 'CH', 'EU' ), $node['areaServed'] );
		$this->assertContains( 'Battery Energy Storage Systems (BESS)', $node['knowsAbout'] );
		$this->assertSame( array( 'Linker Technology GmbH', 'de-linker.com' ), $node['alternateName'] );
		$this->assertSame(
			array(
				'@type'  => 'ImageObject',
				'url'    => 'https://example.org/logo.png',
				'width'  => 717,
				'height' => 354,
			),
			$node['logo']
		);
		$this->assertSame( 'DE367367711', $node['vatID'] );
		$this->assertSame( ContactChannels::company_same_as(), $node['sameAs'] );
		$this->assertStringNotContainsString( 'EcoFlow', $node['description'] );
		$this->assertSame( 'Amtsgericht Stendal HRB 33824', $node['identifier']['value'] );
		$this->assertSame( array( 'sales@de-linker.com', 'chester@de-linker.com' ), array_column( $node['contactPoint'], 'email' ) );
	}

	/**
	 * The journal's site, author and publisher belong to its published language.
	 *
	 * @dataProvider public_languages
	 * @param string $language Polylang slug.
	 * @param string $home Localized homepage.
	 * @param string $about Localized About page.
	 * @param string $role Localized job title.
	 */
	public function test_localized_journal_graph( string $language, string $home, string $about, string $role ): void {
		WP_Mock::userFunction( 'get_option' )->with( 'home' )->andReturn( 'https://example.org/' );
		WP_Mock::userFunction( 'pll_current_language' )->andReturn( $language );
		WP_Mock::userFunction( 'pll_home_url' )->andReturnUsing( static fn( $lang ) => 'de' === $lang ? 'https://example.org/de/' : 'https://example.org/' );
		WP_Mock::userFunction( 'plugins_url' )->andReturn( 'https://example.org/plugin/assets/chester-john.webp' );
		WP_Mock::userFunction( 'trailingslashit' )->andReturnArg( 0 );
		WP_Mock::userFunction( 'is_front_page' )->andReturn( false );
		WP_Mock::userFunction( 'get_page_by_path' )->with( 'about' )->andReturn( new WP_Post( (object) array( 'ID' => 10 ) ) );
		WP_Mock::userFunction( 'pll_get_post' )->with( 10, 'de' )->andReturn( 11 );
		WP_Mock::userFunction( 'get_permalink' )->with( 'de' === $language ? 11 : 10 )->andReturn( $about );
		$schema  = new PageSchema();
		$website = $schema->website( array( 'description' => 'EcoFlow' ) );
		$this->assertSame( $home, $website['url'] );
		$this->assertSame( array( '@id' => 'https://example.org/#organization' ), $website['publisher'] );
		$this->assertSame( 'Linker Technology GmbH', $website['alternateName'] );
		$this->assertSame( $language, $website['inLanguage'] );
		$this->assertStringContainsString( 'de' === $language ? 'PV- und Batteriespeichersysteme' : 'Residential and C&I', $website['description'] );
		$this->assertStringNotContainsString( 'EcoFlow', $website['description'] );
		$node = $schema->article_schema(
			array(
				'author'    => array( 'name' => 'Chester John' ),
				'publisher' => array( 'logo' => 'logo' ),
			)
		);
		$this->assertSame( $about, $node['author']['url'] );
		$this->assertSame( 'https://example.org/#chester-john', $node['author']['@id'] );
		$this->assertSame( $role, $node['author']['jobTitle'] );
		$this->assertSame( 'https://example.org/#organization', $node['author']['worksFor']['@id'] );
		$this->assertSame( ContactChannels::chester_same_as(), $node['author']['sameAs'] );
		$this->assertSame( ContactChannels::company_same_as(), $node['publisher']['sameAs'] );
		$this->assertSame( 'logo', $node['publisher']['logo'] );
		$template_author                = new \WP_User();
		$template_author->user_nicename = 'chester-john';
		$post                           = new WP_Post( (object) array( 'post_author' => '61' ) );
		WP_Mock::userFunction( 'get_userdata' )->with( 61 )->andReturn( $template_author );
		$person = $schema->author_schema( array( 'name' => '[[name]]' ), array( 'post' => $post ) );
		$this->assertSame( $node['author'], $person );
		$team = array( 'name' => 'Editorial team' );
		$this->assertSame( $team, $schema->author_schema( $team ) );
	}

	/** Woo's manufacturer and product facts survive the removal of its retail entity. */
	public function test_only_retail_entity_removed(): void {
		$this->assertSame( array( 'product', 'breadcrumblist' ), ( new PageSchema() )->strip_online_store_type( array( 'product', 'onlinestore', 'breadcrumblist' ) ) );
	}

	/**
	 * The configured English About and Contact templates reference the public graph.
	 *
	 * @dataProvider custom_page_types
	 * @param string $slug English page slug.
	 * @param string $type Page schema type.
	 * @param string $field Organization relation.
	 */
	public function test_custom_graph_nodes( string $slug, string $type, string $field ): void {
		WP_Mock::userFunction( 'is_page' )->andReturnUsing( static fn( $pages ) => in_array( $slug, (array) $pages, true ) );
		WP_Mock::userFunction( 'get_option' )->with( 'home' )->andReturn( 'https://example.org/' );
		WP_Mock::userFunction( 'trailingslashit' )->andReturnArg( 0 );
		WP_Mock::userFunction( 'pll_current_language' )->andReturn( 'en' );
		WP_Mock::userFunction( 'pll_home_url' )->andReturn( 'https://example.org/' );
		WP_Mock::userFunction( 'wp_json_encode' )->andReturnUsing( 'json_encode' );
		$input  = array(
			'@type' => array( $type, 'WebPage' ),
			$field  => array(
				'@type' => 'Organization',
				'name'  => 'Linker',
			),
		);
		$result = ( new PageSchema() )->about_publisher( '<script type="application/ld+json">' . json_encode( $input ) . '</script>' );
		$node   = json_decode( strip_tags( $result ), true, 512, JSON_THROW_ON_ERROR );
		$this->assertSame( array( '@id' => 'https://example.org/#organization' ), $node[ $field ] );
		$this->assertSame( array( '@id' => 'https://example.org/#website' ), $node['isPartOf'] );
		if ( 'about' === $slug ) {
			$this->assertSame( array( array( '@id' => 'https://example.org/#chester-john' ) ), $node['mentions'] );
		}
	}

	/**
	 * English custom page templates.
	 *
	 * @return list<list<string>>
	 */
	public static function custom_page_types(): array {
		return array( array( 'about', 'AboutPage', 'about' ), array( 'contact', 'ContactPage', 'mainEntity' ) );
	}

	/**
	 * Public journal languages.
	 *
	 * @return array<string,list<string>>
	 */
	public static function public_languages(): array {
		return array(
			'English' => array( 'en', 'https://example.org/', 'https://example.org/about/', 'Storage Solutions Specialist' ),
			'German'  => array( 'de', 'https://example.org/de/', 'https://example.org/de/ueber-uns/', 'Spezialist für Speicherlösungen' ),
		);
	}

	/**
	 * Resolved English and German public page graphs.
	 *
	 * @dataProvider page_graphs
	 * @param string $slug Page slug.
	 * @param string $lang Page language.
	 * @param string $type Expected local page schema type; blank for SEOPress-owned pages.
	 * @param int    $depth Breadcrumb depth.
	 */
	public function test_public_page_graphs( string $slug, string $lang, string $type, int $depth ): void {
		$root  = 'https://example.org/';
		$home  = 'de' === $lang ? $root . 'de/' : $root;
		$about = $home . ( 'de' === $lang ? 'ueber-uns/' : 'about/' );
		$url   = $home . $slug . '/';
		$post  = new WP_Post(
			(object) array(
				'ID'          => 5,
				'post_name'   => $slug,
				'post_type'   => 'page',
				'post_parent' => 10,
			)
		);
		WP_Mock::userFunction( 'get_queried_object' )->andReturn( $post );
		WP_Mock::userFunction( 'get_permalink' )->with( $post )->andReturn( $url );
		WP_Mock::userFunction( 'get_permalink' )->with( 10 )->andReturn( $about );
		WP_Mock::userFunction( 'get_the_title' )->with( $post )->andReturn( $slug );
		WP_Mock::userFunction( 'get_the_title' )->with( 10 )->andReturn( 'About' );
		WP_Mock::userFunction( 'get_option' )->with( 'home' )->andReturn( $root );
		WP_Mock::userFunction( 'get_page_by_path' )->with( 'about' )->andReturn( new WP_Post( (object) array( 'ID' => 10 ) ) );
		WP_Mock::userFunction( 'pll_get_post' )->with( 10, 'de' )->andReturn( 10 );
		WP_Mock::userFunction( 'pll_current_language' )->andReturn( $lang );
		WP_Mock::userFunction( 'pll_home_url' )->andReturn( $home );
		WP_Mock::userFunction( 'trailingslashit' )->andReturnArg( 0 );
		WP_Mock::userFunction( 'wp_strip_all_tags' )->andReturnArg( 0 );
		WP_Mock::userFunction( 'is_singular' )->andReturn( false );
		WP_Mock::userFunction( 'is_page' )->andReturnUsing( static fn( $set ) => in_array( $slug, (array) $set, true ) );
		WP_Mock::userFunction( 'get_post_meta' )->andReturn( 'Page description' );
		WP_Mock::userFunction( 'plugins_url' )->andReturn( $root . 'assets/chester-john.webp' );
		WP_Mock::userFunction( 'wp_json_encode' )->andReturnUsing( 'json_encode' );
		WP_Mock::userFunction( '_x' )->andReturn( 'Home' );
		ob_start();
		( new PageSchema() )->print_blocks();
		$html = (string) ob_get_clean();
		preg_match_all( '#<script[^>]+>(.*?)</script>#s', $html, $scripts );
		$nodes = array_map( static fn( $json ) => json_decode( $json, true, 512, JSON_THROW_ON_ERROR ), $scripts[1] );
		$crumb = array_pop( $nodes );
		$this->assertSame( 'BreadcrumbList', $crumb['@type'] );
		$this->assertCount( $depth, $crumb['itemListElement'] );
		$this->assertSame( $url, $crumb['itemListElement'][ $depth - 1 ]['item'] );
		if ( 3 === $depth ) {
			$this->assertSame( $about, $crumb['itemListElement'][1]['item'] );
		}
		if ( in_array( $slug, array( 'about', 'ueber-uns' ), true ) ) {
			$person = array_shift( $nodes );
			$this->assertSame( 'Person', $person['@type'] );
			$this->assertSame( $root . '#chester-john', $person['@id'] );
			$this->assertSame( $root . 'assets/chester-john.webp', $person['image'] );
			$this->assertContains( 'Inverter-Battery Pairing', $person['knowsAbout'] );
		}
		if ( '' === $type ) {
			$this->assertSame( array(), $nodes );
			return;
		}
		$this->assertCount( 1, $nodes );
		$this->assertContains( $type, (array) $nodes[0]['@type'] );
		$this->assertSame( $root . '#organization', $nodes[0]['publisher']['@id'] );
		$this->assertSame( $home . '#website', $nodes[0]['isPartOf']['@id'] );
	}

	/**
	 * Public pages and the template responsible for their top-level node.
	 *
	 * @return list<array{string,string,string,int}>
	 */
	public static function page_graphs(): array {
		$cases = array(
			array( 'contact', 'en', '', 2 ),
			array( 'kontakt', 'de', 'ContactPage', 2 ),
			array( 'about', 'en', '', 2 ),
			array( 'ueber-uns', 'de', 'AboutPage', 2 ),
			array( 'capability', 'en', 'WebPage', 3 ),
			array( 'leistungsfaehigkeit', 'de', 'WebPage', 3 ),
		);
		foreach ( array( 'imprint', 'privacy-policy', 'terms-of-sale', 'refund-returns' ) as $slug ) {
			$cases[] = array( $slug, 'en', 'WebPage', 2 );
		}
		foreach ( array( 'impressum', 'datenschutz', 'verkaufsbedingungen', 'rueckgabe-erstattung' ) as $slug ) {
			$cases[] = array( $slug, 'de', 'WebPage', 2 );
		}
		return $cases;
	}

	/**
	 * The public comparison landing is discoverable; shared selections keep their noindex contract.
	 *
	 * @dataProvider comparison_queries
	 * @param array<string,string> $query Selection query.
	 */
	public function test_comparison_schema_only_for_clean_landing( array $query ): void {
		$post = new WP_Post(
			(object) array(
				'ID'        => 25,
				'post_name' => 'produkte-vergleichen',
				'post_type' => 'page',
			)
		);
		$url  = 'https://example.org/de/produkte-vergleichen/';
		WP_Mock::userFunction( 'get_queried_object' )->andReturn( $post );
		WP_Mock::userFunction( 'get_permalink' )->andReturn( $url );
		WP_Mock::userFunction( 'get_the_title' )->andReturn( 'Produkte vergleichen' );
		WP_Mock::userFunction( 'wp_strip_all_tags' )->andReturnArg( 0 );
		WP_Mock::userFunction( 'pll_current_language' )->andReturn( 'de' );
		WP_Mock::userFunction( 'pll_home_url' )->andReturn( 'https://example.org/de/' );
		WP_Mock::userFunction( 'trailingslashit' )->andReturnArg( 0 );
		WP_Mock::userFunction( 'is_singular' )->andReturn( false );
		WP_Mock::userFunction( 'is_page' )->andReturnUsing( static fn( $names ): bool => in_array( $post->post_name, (array) $names, true ) );
		WP_Mock::userFunction( 'get_option' )->with( 'home' )->andReturn( 'https://example.org/' );
		WP_Mock::userFunction( 'get_post_meta' )->andReturn( 'Modelle vergleichen' );
		WP_Mock::userFunction( '_x' )->andReturn( 'Startseite' );
		WP_Mock::userFunction( 'wp_json_encode' )->andReturnUsing( 'json_encode' );
		$previous = $_GET; // phpcs:ignore WordPress.Security.NonceVerification.Recommended -- Restore the test’s query fixture.
		try {
			$_GET = $query;
			ob_start();
			( new PageSchema() )->print_blocks();
			$html = (string) ob_get_clean();
		} finally {
			$_GET = $previous;
		}
		if ( $query ) {
			$this->assertSame( '', $html );
			return;
		}
		$this->assertStringContainsString( '"@type":"WebPage"', $html );
		$this->assertStringContainsString( '"@type":"BreadcrumbList"', $html );
		$this->assertStringContainsString( '"name":"Startseite"', $html );
		$this->assertStringContainsString( '"name":"Produkte vergleichen"', $html );
	}

	/**
	 * Clean and shared comparison URLs.
	 *
	 * @return array<string,array{array<string,string>}>
	 */
	public static function comparison_queries(): array {
		return array(
			'landing'   => array( array() ),
			'selection' => array( array( 'ids' => '12,19' ) ),
			'empty cap' => array( array( 'capped' => '' ) ),
		);
	}

	/** A breadcrumb names what the browser displays, including decoded ampersands. */
	public function test_article_breadcrumb_follows_the_localized_journal(): void {
		$post = new WP_Post(
			(object) array(
				'ID'        => 20,
				'post_type' => 'post',
			)
		);
		$blog = new WP_Post(
			(object) array(
				'ID'        => 14,
				'post_type' => 'page',
			)
		);
		WP_Mock::userFunction( 'get_queried_object', array( 'return' => $post ) );
		WP_Mock::userFunction(
			'get_the_title',
			array(
				'args'   => array( $post ),
				'return' => 'C&#038;I-Speicher',
			)
		);
		WP_Mock::userFunction(
			'get_the_title',
			array(
				'args'   => array( 14 ),
				'return' => 'Blog',
			)
		);
		WP_Mock::userFunction(
			'get_permalink',
			array(
				'args'   => array( $post ),
				'return' => 'https://example.org/de/ci/',
			)
		);
		WP_Mock::userFunction(
			'get_permalink',
			array(
				'args'   => array( 15 ),
				'return' => 'https://example.org/de/blog/',
			)
		);
		WP_Mock::userFunction(
			'get_page_by_path',
			array(
				'args'   => array( 'blog' ),
				'return' => $blog,
			)
		);
		WP_Mock::userFunction(
			'get_option',
			array(
				'args'   => array( 'page_for_posts' ),
				'return' => 14,
			)
		);
		WP_Mock::userFunction(
			'is_singular',
			array(
				'args'   => array( 'product' ),
				'return' => false,
			)
		);
		WP_Mock::userFunction(
			'is_singular',
			array(
				'args'   => array( 'post' ),
				'return' => true,
			)
		);
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'de' ) );
		WP_Mock::userFunction(
			'pll_home_url',
			array(
				'args'   => array( 'de' ),
				'return' => 'https://example.org/de/',
			)
		);
		WP_Mock::userFunction(
			'pll_get_post',
			array(
				'args'   => array( 14, 'de' ),
				'return' => 15,
			)
		);
		WP_Mock::userFunction( 'trailingslashit', array( 'return_arg' => 0 ) );
		WP_Mock::userFunction( 'wp_strip_all_tags', array( 'return_arg' => 0 ) );
		WP_Mock::userFunction( '_x', array( 'return' => 'Startseite' ) );
		WP_Mock::userFunction( 'wp_json_encode', array( 'return' => static fn( $v, $flags ) => json_encode( $v, $flags ) ) );

		ob_start();
		( new PageSchema() )->print_blocks();
		$json  = trim( strip_tags( (string) ob_get_clean() ) );
		$trail = json_decode( $json, true, 512, JSON_THROW_ON_ERROR )['itemListElement'];
		$this->assertSame( array( 'Startseite', 'Blog', 'C&I-Speicher' ), array_column( $trail, 'name' ) );
		$this->assertSame( array( 'https://example.org/de/', 'https://example.org/de/blog/', 'https://example.org/de/ci/' ), array_column( $trail, 'item' ) );
	}
}
