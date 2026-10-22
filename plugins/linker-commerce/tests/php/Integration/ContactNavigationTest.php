<?php
/**
 * Actual public archive URLs, escaped markup and bilingual Contact consumers.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
namespace Linker\Commerce\Tests\Integration;

use DOMDocument;
use DOMElement;
use DOMXPath;
use Linker\Commerce\Contact\SelectionContext;

/** Native HTTP GET only: no form submission, model request or notification. @coversNothing */
final class ContactNavigationTest extends IntegrationTestCase {

	/**
	 * Native add_query_arg and esc_url must preserve actual selection bytes.
	 *
	 * @testWith ["en", "/products/", "/de/produkte/"]
	 *           ["de", "/de/produkte/", "/products/"]
	 *           ["en", "/brand/saj/", "/de/brand/saj/"]
	 *           ["de", "/de/brand/saj/", "/brand/saj/"]
	 *           ["en", "/product-category/inverters/", "/de/produkt-kategorie/wechselrichter/"]
	 *           ["de", "/de/produkt-kategorie/wechselrichter/", "/product-category/inverters/"]
	 * @param string $language Initial language.
	 * @param string $archive Current native shop path.
	 * @param string $other_archive Paired native shop path.
	 */
	public function test_archive_to_contact_and_native_language_switch_keep_the_selection( string $language, string $archive, string $other_archive ): void {
		$needle = 'SAJ & GoodWe "quoted" \\ Rückfrage + 100%';
		$query  = array(
			'q'      => $needle,
			'brand'  => 'saj',
			'phase'  => '3',
			'kw_min' => '5.5',
			'sort'   => 'name',
		);
		$root   = rtrim( home_url( '/' ), '/' );
		$shop   = $this->get( $root . $archive . '?' . http_build_query( $query ) );
		$other  = 'en' === $language ? 'de' : 'en';
		$switch = $this->element( $shop, '//a[@data-linker-language-choice="' . $other . '"]' )->getAttribute( 'href' );
		self::assertSame( $needle, $this->query( $switch )['q'] ?? null );
		if ( in_array( $archive, array( '/products/', '/de/produkte/' ), true ) ) {
			$facet = $this->element( $shop, '//aside//a[contains(@href,"brand=goodwe")]' )->getAttribute( 'href' );
			self::assertSame( $needle, $this->query( $facet )['q'] ?? null );
		}
		$href      = $this->element( $shop, '//a[contains(concat(" ",normalize-space(@class)," ")," linker-contact-primary ")]' )->getAttribute( 'href' );
		$transport = json_decode( (string) ( $this->query( $href )[ SelectionContext::FIELD ] ?? '' ), true );
		self::assertIsArray( $transport, 'The actual escaped native invitation must contain JSON, not stripped punctuation.' );
		self::assertSame( $needle, $transport['selection']['q'] );
		self::assertSame( 'product', $this->query( $href )['intent'] ?? null );
		$contact = $this->get( $href );
		$this->assert_contact( $contact, $needle, $archive );
		$switched = $this->element( $contact, '//a[@data-linker-language-choice="' . $other . '"]' )->getAttribute( 'href' );
		self::assertSame( 'product', $this->query( $switched )['intent'] ?? null );
		$next_context = json_decode( (string) ( $this->query( $switched )[ SelectionContext::FIELD ] ?? '' ), true );
		self::assertIsArray( $next_context );
		self::assertSame( $needle, $next_context['selection']['q'] );
		self::assertSame( $other_archive, wp_parse_url( $next_context['source'], PHP_URL_PATH ) );
		$this->assert_contact( $this->get( $switched ), $needle, $other_archive );
		// The out-of-range family alias normalizes through the same encoded archive base.
		$response = wp_remote_get( $root . $archive . '?' . http_build_query( array_merge( $query, array( 'product-page' => '2' ) ) ), array( 'redirection' => 0 ) );
		self::assertSame( 301, wp_remote_retrieve_response_code( $response ) );
		$location = wp_remote_retrieve_header( $response, 'location' );
		self::assertIsString( $location );
		self::assertSame( $needle, $this->query( $location )['q'] ?? null );
	}

	/**
	 * A native receiver exposes the same current selection, not an unavailable placeholder.
	 *
	 * @param DOMXPath $document Actual frontend DOM.
	 * @param string   $needle Expected search bytes.
	 * @param string   $archive Expected source path.
	 */
	private function assert_contact( DOMXPath $document, string $needle, string $archive ): void {
		$field   = $this->element( $document, '//fieldset[contains(@class,"linker-contact-selection")]//input[@name="' . SelectionContext::FIELD . '"]' );
		$context = json_decode( $field->getAttribute( 'value' ), true );
		self::assertIsArray( $context );
		self::assertSame( $needle, $context['selection']['q'] );
		self::assertTrue( $field->hasAttribute( 'checked' ) );
		$link = $this->element( $document, '//div[contains(@class,"linker-contact-selection__summary")]//a' )->getAttribute( 'href' );
		self::assertSame( $archive, wp_parse_url( $link, PHP_URL_PATH ) );
		self::assertSame(
			array(
				'brand'  => 'saj',
				'phase'  => '3',
				'kw_min' => '5.5',
				'q'      => $needle,
				'sort'   => 'name',
			),
			$this->query( $link )
		);
		self::assertSame( '', $this->element( $document, '//textarea[@name="message"]' )->textContent );
		self::assertSame( 'product', $this->element( $document, '//select[@name="intent"]/option[@selected]' )->getAttribute( 'value' ) );
	}

	/**
	 * Parse the rendered address once, as an ordinary browser request does.
	 *
	 * @param string $url Actual HTML-decoded href.
	 * @return array<array-key,mixed>
	 */
	private function query( string $url ): array {
		parse_str( (string) wp_parse_url( $url, PHP_URL_QUERY ), $query );
		return $query;
	}

	/**
	 * Exactly the intended native element must exist.
	 *
	 * @param DOMXPath $document Rendered frontend DOM.
	 * @param string   $path Target XPath.
	 */
	private function element( DOMXPath $document, string $path ): DOMElement {
		$nodes = $document->query( $path );
		self::assertNotFalse( $nodes );
		self::assertGreaterThan( 0, $nodes->length, $path );
		$node = $nodes->item( 0 );
		self::assertInstanceOf( DOMElement::class, $node );
		return $node;
	}

	/**
	 * Read the real native HTTP renderer; never rebuild an address in a mock.
	 *
	 * @param string $url Existing public frontend URL.
	 */
	private function get( string $url ): DOMXPath {
		$response = wp_remote_get( $url );
		self::assertSame( 200, wp_remote_retrieve_response_code( $response ), $url );
		$document = new DOMDocument();
		$errors   = libxml_use_internal_errors( true );
		try {
			self::assertTrue( $document->loadHTML( (string) wp_remote_retrieve_body( $response ) ) );
		} finally {
			libxml_clear_errors();
			libxml_use_internal_errors( $errors );
		}
		return new DOMXPath( $document );
	}
}
