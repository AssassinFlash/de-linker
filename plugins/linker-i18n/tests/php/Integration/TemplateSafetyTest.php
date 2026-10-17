<?php
/**
 * Repository-owned templates stay paired without entering the translator.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Integration;

/**
 * Real saves, CLI entry points and stale Action Scheduler jobs.
 *
 * @coversNothing
 */
final class TemplateSafetyTest extends SiteTestCase {

	/**
	 * Each case uses its own disposable language pair.
	 *
	 * @dataProvider templates
	 * @param string $type Template post type.
	 * @param string $slug Template role.
	 */
	public function test_template_content_and_language_pair_survive_every_translation_entry( string $type, string $slug ): void {
		$result = self::php(
			'
			$ids = array();
			try {
				foreach ( array( "en", "de" ) as $lang ) {
					$ids[$lang] = wp_insert_post( array( "post_type" => $input["type"], "post_status" => "publish", "post_title" => "Safety " . $input["slug"] . " " . $lang, "post_name" => "i253-safety-" . $input["slug"] . "-" . $lang, "post_content" => "<p>" . $lang . " template owned by present</p>" ) );
					pll_set_post_language( $ids[$lang], $lang );
				}
				pll_save_post_translations( $ids );
				$before = get_post( $ids["de"] )->post_content;
				wp_update_post( array( "ID" => $ids["en"], "post_content" => "<p>English template changed</p>" ) );
				WP_CLI::runcommand( "linker-i18n translate " . $ids["en"] . " --force", array( "launch" => false, "return" => true ) );
				WP_CLI::runcommand( "linker-i18n translate " . $ids["en"] . " --force --now", array( "launch" => false, "return" => true ) );
				$save_queued = as_has_scheduled_action( "linker_i18n_translate", array( "post", $ids["en"], false, 1 ), "linker-i18n" );
				$job = as_enqueue_async_action( "linker_i18n_translate", array( "post", $ids["en"], true, 1 ), "linker-i18n" );
				ActionScheduler_QueueRunner::instance()->process_action( $job, "WP CLI" );
				do_action( "linker_i18n_translate", "post", $ids["en"], false, 3 );
				$check = array( "before" => $before, "after" => get_post( $ids["de"] )->post_content, "save_queued" => $save_queued, "status" => get_post_meta( $ids["en"], "_linker_i18n_status", true ), "pair" => pll_get_post( $ids["en"], "de" ) === $ids["de"], "de_language" => pll_get_post_language( $ids["de"] ), "registered" => pll_is_translated_post_type( $input["type"] ) );
				return $check;
			} finally {
				foreach ( $ids as $id ) { wp_delete_post( $id, true ); }
			}
			',
			array(
				'type' => $type,
				'slug' => $slug,
			)
		);
		$this->assertIsArray( $result );
		$this->assertSame( $result['before'], $result['after'] );
		$this->assertFalse( $result['save_queued'] );
		$this->assertSame( '', $result['status'] );
		$this->assertTrue( $result['pair'] );
		$this->assertTrue( $result['registered'] );
		$this->assertSame( 'de', $result['de_language'] );
	}

	/**
	 * Retirement is idempotent and preserves unrelated content jobs and templates.
	 */
	public function test_retirement_cleans_only_present_owned_jobs_and_status(): void {
		$ids = self::php( '$template = wp_insert_post( array( "post_type" => "lc_partial", "post_status" => "publish", "post_title" => "i253 retirement", "post_content" => "Template must remain" ) ); pll_set_post_language( $template, "en" ); update_post_meta( $template, "_linker_i18n_status", "pending" ); update_post_meta( $template, "_linker_i18n_note", "old failure" ); as_enqueue_async_action( "linker_i18n_translate", array( "post", $template, true, 3 ), "linker-i18n" ); $page = wp_insert_post( array( "post_type" => "page", "post_status" => "publish", "post_title" => "i253 unrelated job" ) ); pll_set_post_language( $page, "en" ); as_enqueue_async_action( "linker_i18n_translate", array( "post", $page, false, 1 ), "linker-i18n" ); return array( "template" => $template, "page" => $page );' );
		try {
			self::wp( array( 'linker-i18n', 'retire-template-jobs' ) );
			$result = self::php( 'return array( get_post_meta( $input["template"], "_linker_i18n_status", true ), get_post_meta( $input["template"], "_linker_i18n_note", true ), get_post( $input["template"] )->post_content, as_has_scheduled_action( "linker_i18n_translate", array( "post", $input["template"], true, 3 ), "linker-i18n" ), as_has_scheduled_action( "linker_i18n_translate", array( "post", $input["page"], false, 1 ), "linker-i18n" ) );', $ids );
			$this->assertSame( array( '', '', 'Template must remain', false, true ), $result );
			$this->assertStringContainsString( '0 template jobs cancelled; 0 template statuses cleared.', self::wp( array( 'linker-i18n', 'retire-template-jobs' ) ) );
		} finally {
			self::php( 'as_unschedule_all_actions( "linker_i18n_translate", array( "post", $input["page"], false, 1 ), "linker-i18n" ); wp_delete_post( $input["template"], true ); wp_delete_post( $input["page"], true ); return true;', $ids );
		}
	}

	/**
	 * Present owns every partial and dynamic template, not only the header.
	 *
	 * @return array<string, array{string, string}>
	 */
	public function templates(): array {
		return array(
			'header'  => array( 'lc_partial', 'header' ),
			'footer'  => array( 'lc_partial', 'footer' ),
			'dynamic' => array( 'lc_dynamic_template', 'product' ),
		);
	}
}
