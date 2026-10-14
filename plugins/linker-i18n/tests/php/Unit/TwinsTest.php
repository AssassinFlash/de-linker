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

	/**
	 * The live database has no category rows for posts 551–560. A repair
	 * that looks those rows up finds nothing, so the write has to come from
	 * the snapshot list (docs/debt/DE-PARITY-2026-10-13.md §2: 551 and 552
	 * on term 10, and the German twins 6893 and 6895), and it replaces what
	 * is on the post — append would leave 558 on Uncategorized as well.
	 */
	public function test_empty_english_relationships_are_restored_from_the_snapshot(): void {
		PolylangDouble::mock(
			array(
				551  => 'en',
				552  => 'en',
				6893 => 'de',
				6895 => 'de',
			),
			array(
				551 => 6893,
				552 => 6895,
			),
			array(
				10  => 'en',
				557 => 'de',
			),
			array( 10 => 557 ),
			'en',
			array(),
			array(
				551 => array( 'post_type' => 'post' ),
				552 => array( 'post_type' => 'post' ),
			),
			array( 10 => array( 'slug' => 'system-design' ) )
		);
		WP_Mock::userFunction( 'get_objects_in_term', array( 'times' => 0 ) );
		$assigned = array();
		WP_Mock::userFunction( 'wp_set_object_terms' )->andReturnUsing(
			static function ( int $object_id, array $terms, string $taxonomy, bool $append ) use ( &$assigned ): array {
				$assigned[] = array( $object_id, $terms, $taxonomy, $append );
				return $terms;
			}
		);

		$languages = new Languages();
		$twins     = new Twins( $languages, new LinkLocalizer( $languages, new HtmlTokenizer() ), new Projection( $languages ) );
		$restored  = $twins->restore_post_categories();

		$this->assertSame( 2, $restored );
		$this->assertSame(
			array(
				array( 551, array( 10 ), 'category', false ),
				array( 6893, array( 557 ), 'category', false ),
				array( 552, array( 10 ), 'category', false ),
				array( 6895, array( 557 ), 'category', false ),
			),
			$assigned
		);
		$this->assertConditionsMet();
	}

	/**
	 * Term ids 10–14 are the live snapshot's. A database that reused them
	 * for other categories (a different slug) must receive nothing, and the
	 * repair must not count it.
	 */
	public function test_a_snapshot_id_with_the_wrong_slug_is_not_attached(): void {
		PolylangDouble::mock(
			array( 551 => 'en' ),
			array(),
			array( 10 => 'en' ),
			array(),
			'en',
			array(),
			array( 551 => array( 'post_type' => 'post' ) ),
			array( 10 => array( 'slug' => 'news' ) )
		);
		WP_Mock::userFunction( 'wp_set_object_terms', array( 'times' => 0 ) );

		$languages = new Languages();
		$twins     = new Twins( $languages, new LinkLocalizer( $languages, new HtmlTokenizer() ), new Projection( $languages ) );

		$this->assertSame( 0, $twins->restore_post_categories() );
		$this->assertConditionsMet();
	}

	/**
	 * The same guard for the post: snapshot id 551 holding a page in this
	 * database is a different object, and the repair leaves it alone.
	 */
	public function test_a_snapshot_id_reused_by_a_page_is_not_attached(): void {
		PolylangDouble::mock(
			array( 551 => 'en' ),
			array(),
			array( 10 => 'en' ),
			array(),
			'en',
			array(),
			array( 551 => array( 'post_type' => 'page' ) ),
			array( 10 => array( 'slug' => 'system-design' ) )
		);
		WP_Mock::userFunction( 'wp_set_object_terms', array( 'times' => 0 ) );

		$languages = new Languages();
		$twins     = new Twins( $languages, new LinkLocalizer( $languages, new HtmlTokenizer() ), new Projection( $languages ) );

		$this->assertSame( 0, $twins->restore_post_categories() );
		$this->assertConditionsMet();
	}

	/**
	 * An existing German category is written again, not only when it is
	 * created. The English relationships are already gone, so the write
	 * still has to put 551 back on term 10 and 6893 on the German term,
	 * and a named slug must rename the German term (the live German
	 * archive is /de/category/system-design/, not
	 * /de/category/systemauslegung/; docs/debt/DE-PARITY-2026-10-13.md §4.1).
	 */
	public function test_an_existing_category_is_reassigned_from_empty_relationships(): void {
		PolylangDouble::mock(
			array(
				551  => 'en',
				6893 => 'de',
			),
			array( 551 => 6893 ),
			array(
				10  => 'en',
				557 => 'de',
			),
			array( 10 => 557 ),
			'en',
			array(),
			array( 551 => array( 'post_type' => 'post' ) ),
			array( 10 => array( 'slug' => 'system-design' ) )
		);
		$this->wordpress();
		WP_Mock::userFunction( 'get_term_meta', array( 'return' => '' ) );
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => false ) );
		WP_Mock::userFunction( 'get_objects_in_term', array( 'times' => 0 ) );
		WP_Mock::userFunction(
			'wp_update_term',
			array(
				'times'  => 1,
				'return' => array(
					'term_id'          => 557,
					'term_taxonomy_id' => 557,
				),
				'args'   => array(
					557,
					'category',
					Mockery::on(
						static fn( array $args ): bool => 'system-design' === ( $args['slug'] ?? '' )
							&& 'Systemauslegung' === ( $args['name'] ?? '' )
					),
				),
			)
		);
		$assigned = array();
		WP_Mock::userFunction( 'wp_set_object_terms' )->andReturnUsing(
			static function ( int $object_id, array $terms, string $taxonomy, bool $append ) use ( &$assigned ): array {
				$assigned[] = array( $object_id, $terms, $taxonomy, $append );
				return $terms;
			}
		);

		$languages = new Languages();
		$twins     = new Twins( $languages, new LinkLocalizer( $languages, new HtmlTokenizer() ), new Projection( $languages ) );
		$twin      = $twins->term(
			10,
			array(
				'name'        => 'Systemauslegung',
				'description' => '',
			),
			'system-design'
		);

		$this->assertSame( 557, $twin );
		$this->assertSame(
			array(
				array( 551, array( 10 ), 'category', false ),
				array( 6893, array( 557 ), 'category', false ),
			),
			$assigned
		);
		$this->assertConditionsMet();
	}

	/**
	 * A re-run writes the German post while the English post has no
	 * category. terms() must not copy that empty list onto the German post:
	 * the snapshot says 551 is on term 10, so 6893 is written the German
	 * term. get_object_taxonomies is registered once here — the shared
	 * helper also registers it, and WP_Mock keeps the first registration,
	 * so this test does not call that helper.
	 */
	public function test_an_empty_english_category_does_not_clear_the_german_post(): void {
		PolylangDouble::mock(
			array(
				551  => 'en',
				6893 => 'de',
			),
			array( 551 => 6893 ),
			array(
				10  => 'en',
				557 => 'de',
			),
			array( 10 => 557 ),
			'en',
			array(),
			array(
				551  => array(
					'post_type'      => 'post',
					'post_status'    => 'publish',
					'post_parent'    => 0,
					'post_author'    => 1,
					'menu_order'     => 0,
					'comment_status' => 'closed',
					'ping_status'    => 'closed',
					'post_password'  => '',
					'post_title'     => 'How to Choose',
				),
				6893 => array(
					'post_type'   => 'post',
					'post_status' => 'publish',
					'post_title'  => 'So wählen Sie',
				),
			),
			array( 10 => array( 'slug' => 'system-design' ) )
		);
		WP_Mock::passthruFunction( 'wp_slash' );
		WP_Mock::userFunction( 'has_filter', array( 'return' => false ) );
		WP_Mock::userFunction( 'remove_action', array( 'return' => false ) );
		WP_Mock::userFunction( 'get_post_meta', array( 'return' => array() ) );
		WP_Mock::userFunction( 'get_object_taxonomies', array( 'return' => array( 'category' ) ) );
		WP_Mock::userFunction( 'is_post_type_hierarchical', array( 'return' => false ) );
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => false ) );
		WP_Mock::userFunction(
			'wp_get_object_terms',
			array(
				'return' => array(),
				'args'   => array( 551, 'category', array( 'fields' => 'ids' ) ),
			)
		);
		WP_Mock::userFunction(
			'wp_update_post',
			array(
				'times' => 1,
				'args'  => array(
					Mockery::on( static fn( array $postarr ): bool => 6893 === $postarr['ID'] ),
					true,
				),
			)
		);
		$assigned = array();
		WP_Mock::userFunction( 'wp_set_object_terms' )->andReturnUsing(
			static function ( int $object_id, array $terms, string $taxonomy, bool $append = false ) use ( &$assigned ): array {
				$assigned[] = array( $object_id, $terms, $taxonomy, $append );
				return $terms;
			}
		);

		$languages = new Languages();
		$twins     = new Twins( $languages, new LinkLocalizer( $languages, new HtmlTokenizer() ), new Projection( $languages ) );
		$twins->post(
			551,
			array(
				'post_title'   => 'So wählen Sie',
				'post_excerpt' => '',
				'post_content' => '<p>Deutsch.</p>',
			),
			'hybridwechselrichter-vs-ac-speicher'
		);

		$this->assertSame(
			array(
				// restore_post_category() runs before the insert, so the
				// language sync copies the snapshot category instead of
				// clearing it (Twins::post()).
				array( 551, array( 10 ), 'category', false ),
				array( 6893, array( 557 ), 'category', false ),
				// terms() writes three arguments. The empty English list is
				// not copied: the German post keeps the snapshot term.
				array( 6893, array( 557 ), 'category', false ),
			),
			$assigned
		);
		$this->assertConditionsMet();
	}

	/**
	 * The German term of the snapshot category is not in this database (no
	 * 10 → de pair). terms() must leave the German post alone: writing the
	 * empty English list would clear the German post's category, and there
	 * is no German term to write instead. The English restore before the
	 * insert is the whole write — the German post 6893 receives no
	 * wp_set_object_terms call at all.
	 */
	public function test_a_missing_german_category_term_leaves_the_german_post_alone(): void {
		PolylangDouble::mock(
			array(
				551  => 'en',
				6893 => 'de',
			),
			array( 551 => 6893 ),
			array( 10 => 'en' ),
			array(),
			'en',
			array(),
			array(
				551  => array(
					'post_type'      => 'post',
					'post_status'    => 'publish',
					'post_parent'    => 0,
					'post_author'    => 1,
					'menu_order'     => 0,
					'comment_status' => 'closed',
					'ping_status'    => 'closed',
					'post_password'  => '',
					'post_title'     => 'How to Choose',
				),
				6893 => array(
					'post_type'   => 'post',
					'post_status' => 'publish',
					'post_title'  => 'So wählen Sie',
				),
			),
			array( 10 => array( 'slug' => 'system-design' ) )
		);
		WP_Mock::passthruFunction( 'wp_slash' );
		WP_Mock::userFunction( 'has_filter', array( 'return' => false ) );
		WP_Mock::userFunction( 'remove_action', array( 'return' => false ) );
		WP_Mock::userFunction( 'get_post_meta', array( 'return' => array() ) );
		WP_Mock::userFunction( 'get_object_taxonomies', array( 'return' => array( 'category' ) ) );
		WP_Mock::userFunction( 'is_post_type_hierarchical', array( 'return' => false ) );
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => false ) );
		WP_Mock::userFunction(
			'wp_get_object_terms',
			array(
				'return' => array(),
				'args'   => array( 551, 'category', array( 'fields' => 'ids' ) ),
			)
		);
		WP_Mock::userFunction(
			'wp_update_post',
			array(
				'times' => 1,
				'args'  => array(
					Mockery::on( static fn( array $postarr ): bool => 6893 === $postarr['ID'] ),
					true,
				),
			)
		);
		$assigned = array();
		WP_Mock::userFunction( 'wp_set_object_terms' )->andReturnUsing(
			static function ( int $object_id, array $terms, string $taxonomy, bool $append = false ) use ( &$assigned ): array {
				$assigned[] = array( $object_id, $terms, $taxonomy, $append );
				return $terms;
			}
		);

		$languages = new Languages();
		$twins     = new Twins( $languages, new LinkLocalizer( $languages, new HtmlTokenizer() ), new Projection( $languages ) );
		$twins->post(
			551,
			array(
				'post_title'   => 'So wählen Sie',
				'post_excerpt' => '',
				'post_content' => '<p>Deutsch.</p>',
			),
			'hybridwechselrichter-vs-ac-speicher'
		);

		$this->assertSame(
			array(
				// The English restore runs before the insert (Twins::post()).
				// With no German term in the database this is the whole write:
				// the empty English list never reaches the German post.
				array( 551, array( 10 ), 'category', false ),
			),
			$assigned
		);
		$this->assertConditionsMet();
	}
}
