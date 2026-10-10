<?php
/**
 * Tests for the German version writer.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Unit;

use Linker\I18n\Languages;
use Linker\I18n\LinkLocalizer;
use Linker\I18n\Translation\HtmlTokenizer;
use Linker\I18n\Twins;
use Linker\I18n\Woo\Projection;
use Mockery;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for Twins.
 *
 * @covers \Linker\I18n\Twins
 */
final class TwinsTest extends TestCase {

	/**
	 * The English page and its German version, with the structural fields
	 * Twins::post() reads off the source.
	 *
	 * @return array<int, array<string, mixed>> Posts for PolylangDouble::mock().
	 */
	private function posts(): array {
		$structural = array(
			'post_type'      => 'page',
			'post_status'    => 'publish',
			'post_parent'    => 0,
			'post_author'    => 1,
			'menu_order'     => 0,
			'comment_status' => 'closed',
			'ping_status'    => 'closed',
			'post_password'  => '',
		);
		return array(
			5 => $structural + array( 'post_title' => 'Application' ),
			9 => $structural + array( 'post_title' => 'Anwendung' ),
		);
	}

	/**
	 * The WordPress functions the update path of Twins::post() touches.
	 */
	private function wordpress(): void {
		WP_Mock::passthruFunction( 'wp_slash' );
		WP_Mock::userFunction( 'has_filter', array( 'return' => false ) );
		WP_Mock::userFunction( 'remove_action', array( 'return' => false ) );
		WP_Mock::userFunction( 'get_post_meta', array( 'return' => array() ) );
		WP_Mock::userFunction( 'get_object_taxonomies', array( 'return' => array() ) );
		WP_Mock::userFunction( 'is_post_type_hierarchical', array( 'return' => true ) );
		WP_Mock::userFunction( 'get_post_type', array( 'return' => 'page' ) );
		WP_Mock::userFunction( 'get_children', array( 'return' => array() ) );
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => false ) );
	}

	/**
	 * An adopt() that names a slug renames the German version that already
	 * exists: the migration is the authority for the slug, and a re-run
	 * after a slug correction must take (2026-10-10: about and solution were
	 * imported with the minted map's slugs and never renamed to the curated
	 * ones, so the old German URLs 404ed).
	 */
	public function test_a_named_slug_renames_an_existing_german_post(): void {
		PolylangDouble::mock(
			array(
				5 => 'en',
				9 => 'de',
			),
			array( 5 => 9 ),
			array(),
			array(),
			'en',
			array(),
			$this->posts()
		);
		$this->wordpress();
		WP_Mock::userFunction(
			'wp_update_post',
			array(
				'times' => 1,
				'args'  => array(
					Mockery::on(
						static fn( array $postarr ): bool => 9 === $postarr['ID']
							&& 'loesung' === ( $postarr['post_name'] ?? '' )
					),
					true,
				),
			)
		);

		$languages = new Languages();
		$twins     = new Twins( $languages, new LinkLocalizer( $languages, new HtmlTokenizer() ), new Projection( $languages ) );
		$twin      = $twins->post(
			5,
			array(
				'post_title'   => 'Anwendung',
				'post_excerpt' => '',
				'post_content' => '<p>Der Lösungsentwurf.</p>',
			),
			'loesung'
		);

		$this->assertSame( 9, $twin );
		$this->assertConditionsMet();
	}

	/**
	 * A call without a slug (translate()) leaves the German post's slug alone.
	 */
	public function test_an_unnamed_slug_keeps_an_existing_german_posts_slug(): void {
		PolylangDouble::mock(
			array(
				5 => 'en',
				9 => 'de',
			),
			array( 5 => 9 ),
			array(),
			array(),
			'en',
			array(),
			$this->posts()
		);
		$this->wordpress();
		WP_Mock::userFunction(
			'wp_update_post',
			array(
				'times' => 1,
				'args'  => array(
					Mockery::on(
						static fn( array $postarr ): bool => 9 === $postarr['ID']
							&& ! array_key_exists( 'post_name', $postarr )
					),
					true,
				),
			)
		);

		$languages = new Languages();
		$twins     = new Twins( $languages, new LinkLocalizer( $languages, new HtmlTokenizer() ), new Projection( $languages ) );
		$twins->post(
			5,
			array(
				'post_title'   => 'Anwendung',
				'post_excerpt' => '',
				'post_content' => '<p>Der Lösungsentwurf.</p>',
			)
		);

		$this->assertConditionsMet();
	}

	/**
	 * An update of an already-written pair repairs the twin's language: an
	 * instance imported before Twins ensured the languages can carry a German
	 * partial mislabelled English (t12's state before the repair); the update
	 * branch goes through the same ensure_post_pair().
	 */
	public function test_an_update_repairs_a_mislabelled_twin_language(): void {
		PolylangDouble::mock(
			array(
				5 => 'en',
				9 => 'en',
			),
			array( 5 => 9 ),
			array(),
			array(),
			'en',
			array(),
			$this->posts()
		);
		$this->wordpress();
		WP_Mock::userFunction(
			'wp_update_post',
			array(
				'times' => 1,
				'args'  => array(
					Mockery::on( static fn( array $postarr ): bool => 9 === $postarr['ID'] ),
					true,
				),
			)
		);

		$languages = new Languages();
		$twins     = new Twins( $languages, new LinkLocalizer( $languages, new HtmlTokenizer() ), new Projection( $languages ) );
		$twin      = $twins->post(
			5,
			array(
				'post_title'   => 'Anwendung',
				'post_excerpt' => '',
				'post_content' => '<p>Der Lösungsentwurf.</p>',
			)
		);

		$this->assertSame( 9, $twin );
		$this->assertSame( array( 9 => 'de' ), PolylangDouble::$set_post_language );
		$this->assertSame( array(), PolylangDouble::$saved_post_translations );
		$this->assertConditionsMet();
	}

	/**
	 * A languageless source — the snapshot's LiveCanvas partials arrive
	 * without a Polylang language — gets the source language and the pairing
	 * both: pll_save_post_translations() silently skips a languageless
	 * member, which left the German partial unpaired (2026-10-10, #11's
	 * forensics: LiveCanvas then grabbed the German partial for every
	 * language).
	 */
	public function test_a_languageless_source_gets_its_language_and_the_pairing(): void {
		$structural = array(
			'post_type'      => 'lc_partial',
			'post_status'    => 'publish',
			'post_parent'    => 0,
			'post_author'    => 1,
			'menu_order'     => 0,
			'comment_status' => 'closed',
			'ping_status'    => 'closed',
			'post_password'  => '',
			'post_date'      => '2026-07-01 00:00:00',
			'post_date_gmt'  => '2026-07-01 00:00:00',
		);
		PolylangDouble::mock( array(), array(), array(), array(), 'en', array(), array( 5 => $structural + array( 'post_title' => 'Header' ) ) );
		$this->wordpress();
		WP_Mock::userFunction(
			'wp_insert_post',
			array(
				'times'  => 1,
				'return' => 12,
			)
		);
		WP_Mock::userFunction(
			'wp_update_post',
			array(
				'times' => 1,
				'args'  => array(
					Mockery::on( static fn( array $postarr ): bool => 12 === $postarr['ID'] && 'kopfzeile' === $postarr['post_name'] ),
					true,
				),
			)
		);

		$languages = new Languages();
		$twins     = new Twins( $languages, new LinkLocalizer( $languages, new HtmlTokenizer() ), new Projection( $languages ) );
		$twin      = $twins->post(
			5,
			array(
				'post_title'   => 'Kopfzeile',
				'post_excerpt' => '',
				'post_content' => '<p>Deutscher Kopf.</p>',
			),
			'kopfzeile'
		);

		$this->assertSame( 12, $twin );
		$this->assertSame(
			array(
				5  => 'en',
				12 => 'de',
			),
			PolylangDouble::$set_post_language
		);
		$this->assertSame(
			array(
				array(
					'en' => 5,
					'de' => 12,
				),
			),
			PolylangDouble::$saved_post_translations
		);
		$this->assertConditionsMet();
	}
}
