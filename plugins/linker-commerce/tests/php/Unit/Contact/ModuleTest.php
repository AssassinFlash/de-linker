<?php
/**
 * Tests for mounting the contact form on the contact pages.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Contact;

use Linker\Commerce\Contact\Form;
use Linker\Commerce\Contact\Module;
use Linker\Commerce\Settings\Options;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;
use WP_Post;

/**
 * The deployed contact pages still carry the previous runtime's fallback
 * mount (measured 2026-10-14: form=0, the fallback line visible). The module
 * replaces that mount while the form shortcode can render, and leaves the
 * fallback when it cannot.
 *
 * @covers \Linker\Commerce\Contact\Module
 */
final class ModuleTest extends TestCase {

	/**
	 * The English page as the deploy renders it, before this mount.
	 */
	private const FIXTURE = __DIR__ . '/../../Fixtures/contact-page.html';

	/**
	 * The old mount becomes the form shortcode, and the fallback line goes.
	 */
	public function test_mounts_the_form_in_place_of_the_fallback(): void {
		$this->on_contact_page();
		WP_Mock::userFunction( 'shortcode_exists', array( 'return' => true ) );

		$html = $this->module()->mount_form( $this->fixture() );

		$this->assertStringContainsString(
			'<div data-linker-contact-mount="">[' . Form::SHORTCODE . ']</div>',
			$html
		);
		$this->assertStringNotContainsString( 'cp-contact-fallback', $html );
		$this->assertStringNotContainsString( '<noscript>', $html );
		$this->assertStringNotContainsString( 'If the form is unavailable', $html );
		$this->assertStringContainsString( 'id="contact-form"', $html );
	}

	/**
	 * A page that already carries the shortcode keeps it, and still loses the
	 * previous runtime's fallback line.
	 */
	public function test_leaves_a_page_that_already_mounts_the_shortcode(): void {
		$this->on_contact_page();
		$content = str_replace(
			'<div class="cp-contact-fallback" data-contact-fallback="">' . "\n"
			. '<p>Tell us what you need. If the form is unavailable, email <a href="mailto:sales@de-linker.com">sales@de-linker.com</a>.</p>' . "\n"
			. '</div>',
			'[' . Form::SHORTCODE . ']',
			$this->fixture()
		);

		$html = $this->module()->mount_form( $content );

		$this->assertSame( 1, substr_count( $html, '[' . Form::SHORTCODE . ']' ) );
		$this->assertStringNotContainsString( 'cp-contact-fallback', $html );
		$this->assertStringNotContainsString( '<noscript>', $html );
	}

	/**
	 * The fallback line is what a visitor sees when the form cannot render.
	 */
	public function test_keeps_the_fallback_when_the_form_is_not_registered(): void {
		$this->on_contact_page();
		WP_Mock::userFunction( 'shortcode_exists', array( 'return' => false ) );

		$html = $this->module()->mount_form( $this->fixture() );

		$this->assertStringNotContainsString( '[' . Form::SHORTCODE . ']', $html );
		$this->assertStringContainsString( 'cp-contact-fallback', $html );
		$this->assertStringContainsString( 'If the form is unavailable', $html );
		$this->assertStringContainsString( '<noscript>', $html );
	}

	/**
	 * The German twin is the same page, resolved through Polylang, not a slug.
	 */
	public function test_mounts_the_form_on_the_german_twin(): void {
			$this->on_contact_page( 6917, 6917 );
		WP_Mock::userFunction( 'shortcode_exists', array( 'return' => true ) );

		$html = $this->module()->mount_form( $this->fixture() );

		$this->assertStringContainsString( '[' . Form::SHORTCODE . ']', $html );
		$this->assertStringNotContainsString( 'cp-contact-fallback', $html );
	}

	/**
	 * A mount marker on any other page is not this form's.
	 */
	public function test_leaves_every_other_page_alone(): void {
		$this->on_page( 99, 'about', null );
		$fixture = $this->fixture();

		$this->assertSame( $fixture, $this->module()->mount_form( $fixture ) );
	}

	/**
	 * A contact page whose region is not the old mount is not guessed at.
	 */
	public function test_leaves_an_unrecognised_region_alone(): void {
		$this->on_contact_page();
		WP_Mock::userFunction( 'shortcode_exists', array( 'return' => true ) );
		$content = '<div data-linker-contact-mount="">something else</div>';

		$this->assertSame( $content, $this->module()->mount_form( $content ) );
	}

	/**
	 * The fixture is the deployed page's form region.
	 */
	private function fixture(): string {
		$fixture = file_get_contents( self::FIXTURE );
		$this->assertIsString( $fixture );
		return $fixture;
	}

	/**
	 * The module under test. Its other hooks are not what these tests call.
	 */
	private function module(): Module {
		return new Module( '/plugin/linker-commerce.php', new Options() );
	}

	/**
	 * The request is the English contact page, or its German twin.
	 *
	 * @param int      $page_id The queried page.
	 * @param int|null $twin    The German twin id Polylang answers, null when absent.
	 */
	private function on_contact_page( int $page_id = 28, ?int $twin = null ): void {
		$this->on_page( $page_id, 'contact', $twin );
	}

	/**
	 * One queried page, plus the English contact page and its twin.
	 *
	 * @param int      $page_id The queried page.
	 * @param string   $slug    Its slug.
	 * @param int|null $twin    The German twin of the English contact page.
	 */
	private function on_page( int $page_id, string $slug, ?int $twin ): void {
		WP_Mock::userFunction( 'is_page', array( 'return' => true ) );
		WP_Mock::userFunction( 'get_queried_object', array( 'return' => $this->page( $page_id, $slug ) ) );
		WP_Mock::userFunction( 'get_page_by_path', array( 'return' => $this->page( 28, 'contact' ) ) );
		WP_Mock::userFunction(
			'pll_get_post',
			array(
				'return' => static function ( int $id, string $language ) use ( $twin ): int {
					unset( $id );
					// Polylang 3.4 answers 0 when the page has no translation.
					return ( 'de' === $language && is_int( $twin ) ) ? $twin : 0;
				},
			)
		);
	}

	/**
	 * A page post.
	 *
	 * @param int    $id   Post id.
	 * @param string $slug Post slug.
	 */
	private function page( int $id, string $slug ): WP_Post {
		return new WP_Post(
			(object) array(
				'ID'        => $id,
				'post_type' => 'page',
				'post_name' => $slug,
			)
		);
	}
}
