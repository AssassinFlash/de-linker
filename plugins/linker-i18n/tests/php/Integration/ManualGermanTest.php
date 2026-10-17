<?php
/**
 * Existing human German survives scans and unsafe structural changes.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Integration;

/**
 * The About page fixture is content from the live snapshot, never executable code.
 * All posts and scheduled actions created here are removed in finally.
 *
 * @coversNothing
 */
final class ManualGermanTest extends SiteTestCase {

	/**
	 * The first real English edit works even before any baseline scan was run.
	 */
	public function test_first_post_and_term_edits_capture_the_previous_english(): void {
		$result = self::php(
			'
			$result = array(); $posts = array(); $terms = array(); $calls = 0;
			add_filter( "pre_http_request", static function ( $pre, $args, $url ) use ( &$calls ) { if ( str_starts_with( $url, (string) getenv( "LINKER_I18N_STUB" ) ) ) { ++$calls; } return $pre; }, 1, 3 );
			try {
				$old = "<p>First sentence. Second sentence.</p>"; $german = "<p>Manuell eins. Manuell zwei.</p>"; $new = "<p>First sentence. Updated second sentence.</p>";
				$en = wp_insert_post( array( "post_type" => "page", "post_status" => "private", "post_title" => "i253 first edit", "post_content" => $old ) ); $posts[] = $en;
				$de = wp_insert_post( array( "post_type" => "page", "post_status" => "private", "post_title" => "i253 erste Änderung", "post_content" => $german ) ); $posts[] = $de;
				pll_set_post_language( $en, "en" ); pll_set_post_language( $de, "de" ); pll_save_post_translations( array( "en" => $en, "de" => $de ) );
				wp_update_post( array( "ID" => $en, "post_content" => $new ) );
				do_action( "linker_i18n_translate", "post", $en, false, 1 );
				$result[] = array( get_post_meta( $en, "_linker_i18n_status", true ), get_post( $de )->post_content, $calls );
				$en = wp_insert_term( "i253 first term", "category", array( "description" => $old ) )["term_id"]; $terms[] = $en;
				$de = wp_insert_term( "i253 erster Begriff", "category", array( "description" => $german ) )["term_id"]; $terms[] = $de;
				pll_set_term_language( $en, "en" ); pll_set_term_language( $de, "de" ); pll_save_term_translations( array( "en" => $en, "de" => $de ) );
				wp_update_term( $en, "category", array( "description" => $new ) );
				do_action( "linker_i18n_translate", "term", $en, false, 1 );
				$result[] = array( get_term_meta( $en, "_linker_i18n_status", true ), get_term( $de )->description, $calls );
				return $result;
			} finally {
				foreach ( as_get_scheduled_actions( array( "hook" => "linker_i18n_translate", "group" => "linker-i18n", "status" => "pending", "per_page" => -1 ), "ids" ) as $action ) { $args = ActionScheduler::store()->fetch_action( $action )->get_args(); $ids = "post" === $args[0] ? $posts : $terms; if ( in_array( (int) $args[1], $ids, true ) ) { ActionScheduler::store()->cancel_action( $action ); } }
				foreach ( $posts as $id ) { wp_delete_post( $id, true ); } foreach ( $terms as $id ) { wp_delete_term( $id, "category" ); }
			}
			',
			array(),
			true
		);
		$this->assertSame( array( 'synced', '<p>Manuell eins. [de] Updated second sentence.</p>', 1 ), $result[0] );
		$this->assertSame( array( 'synced', 'Manuell eins. [de] Updated second sentence.', 2 ), $result[1] );
	}

	/**
	 * Scan, sentence update, then a structural exception on the real marketing HTML.
	 */
	public function test_manual_marketing_german_is_preserved_and_only_changed_sentences_translate(): void {
		$result = self::php(
			'
			$fixture = json_decode( file_get_contents( WP_PLUGIN_DIR . "/linker-i18n/tests/php/Integration/fixtures/about-manual.json" ), true );
			$ids = array(); $calls = array();
			add_filter( "pre_http_request", static function ( $pre, $args, $url ) use ( &$calls ) { if ( str_starts_with( $url, (string) getenv( "LINKER_I18N_STUB" ) ) ) { $calls[] = json_decode( $args["body"], true ); } return $pre; }, 1, 3 );
			try {
				$en = wp_insert_post( wp_slash( array( "post_type" => "page", "post_status" => "private", "post_title" => "i253 human marketing", "post_content" => $fixture["english"] ) ) ); $ids[] = $en;
				$de = wp_insert_post( wp_slash( array( "post_type" => "page", "post_status" => "private", "post_title" => "i253 manuelles Deutsch", "post_content" => $fixture["german"] ) ) ); $ids[] = $de;
				pll_set_post_language( $en, "en" ); pll_set_post_language( $de, "de" ); pll_save_post_translations( array( "en" => $en, "de" => $de ) );
				update_post_meta( $de, "_linker_i18n_reviewed", wp_slash( $fixture["reviewed"] ) );
				update_post_meta( $en, "_seopress_titles_desc", "An existing English SEO description without German metadata." );
				update_post_meta( $en, "_linker_i18n_status", "needs_review" );
				// A legacy forced job is also required to adopt rather than erase German.
				do_action( "linker_i18n_translate", "post", $en, true, 1 );
				$first = array( "same" => $fixture["german"] === get_post( $de )->post_content, "calls" => count( $calls ), "baseline" => get_post_meta( $de, "_linker_i18n_source_hash", true ), "reviewed" => get_post_meta( $de, "_linker_i18n_reviewed", true ), "status" => get_post_meta( $en, "_linker_i18n_status", true ) );
				do_action( "linker_i18n_translate", "post", $en, false, 1 );
				$first["repeat_calls"] = count( $calls );
				$old = "We work alongside installers and EPCs across Europe to take the friction out of storage.";
				$new = "We work alongside installers and EPCs across Europe to simplify storage projects.";
				$source = preg_replace( "/" . preg_quote( $old, "/" ) . "/", $new, $fixture["english"], 1, $replaced );
				wp_update_post( wp_slash( array( "ID" => $en, "post_content" => $source ) ) );
				do_action( "linker_i18n_translate", "post", $en, false, 1 );
				$expected = preg_replace( "/" . preg_quote( "Wir arbeiten mit Installateuren und EPCs in ganz Europa zusammen, um den Aufwand bei Speichern zu reduzieren.", "/" ) . "/", "[de] " . $new, $fixture["german"], 1 );
				$second = array( "replaced" => $replaced, "exact" => $expected === get_post( $de )->post_content, "calls" => count( $calls ), "status" => get_post_meta( $en, "_linker_i18n_status", true ) );
				$before = get_post( $de )->post_content; $hash = get_post_meta( $de, "_linker_i18n_source_hash", true );
				wp_update_post( wp_slash( array( "ID" => $en, "post_content" => $source . "<p>Another sentence with no German slot.</p>" ) ) );
				do_action( "linker_i18n_translate", "post", $en, true, 1 );
				do_action( "linker_i18n_translate", "post", $en, true, 3 );
				$column = new Linker\I18n\Admin\StatusColumn( new Linker\I18n\Languages(), new Linker\I18n\Translation\State(), ( new ReflectionClass( Linker\I18n\Jobs::class ) )->newInstanceWithoutConstructor() );
				$status = get_post_meta( $en, "_linker_i18n_status", true );
				$report = array_values( array_filter( ( new Linker\I18n\Translation\StatusReport() )->issues(), static fn( $row ) => $en === $row["id"] && "post" === $row["kind"] ) );
				$third = array( "same" => $before === get_post( $de )->post_content, "baseline_kept" => $hash === get_post_meta( $de, "_linker_i18n_source_hash", true ), "calls" => count( $calls ), "status" => $status, "label" => $column->label( true, $status ), "report" => $report );
				return array( $first, $second, $third, $fixture["reviewed"] );
			} finally {
				foreach ( as_get_scheduled_actions( array( "hook" => "linker_i18n_translate", "group" => "linker-i18n", "status" => "pending", "per_page" => -1 ), "ids" ) as $action ) { $args = ActionScheduler::store()->fetch_action( $action )->get_args(); if ( "post" === $args[0] && in_array( (int) $args[1], $ids, true ) ) { ActionScheduler::store()->cancel_action( $action ); } }
				foreach ( $ids as $id ) { wp_delete_post( $id, true ); }
			}
			',
			array(),
			true
		);
		$this->assertTrue( $result[0]['same'] );
		$this->assertSame( 0, $result[0]['calls'] );
		$this->assertSame( 0, $result[0]['repeat_calls'] );
		$this->assertNotSame( '', $result[0]['baseline'] );
		$this->assertSame( $result[3], $result[0]['reviewed'] );
		$this->assertSame( 'synced', $result[0]['status'] );
		$this->assertSame( 1, $result[1]['replaced'] );
		$this->assertTrue( $result[1]['exact'] );
		$this->assertSame( 1, $result[1]['calls'] );
		$this->assertSame( 'synced', $result[1]['status'] );
		$this->assertTrue( $result[2]['same'] );
		$this->assertTrue( $result[2]['baseline_kept'] );
		$this->assertSame( 1, $result[2]['calls'] );
		$this->assertSame( 'structure_mismatch', $result[2]['status'] );
		$this->assertSame( 'German out of date: structure differs', $result[2]['label'] );
		$this->assertCount( 1, $result[2]['report'] );
		$this->assertSame( $result[2]['label'], $result[2]['report'][0]['reason'] );
	}
}
