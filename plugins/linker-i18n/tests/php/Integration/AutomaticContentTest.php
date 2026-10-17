<?php
/**
 * Real page/blog updates, historical recovery, queue races and exception reports.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Integration;

/**
 * All fixtures belong to this test and are removed afterwards.
 *
 * @coversNothing
 */
final class AutomaticContentTest extends SiteTestCase {

	/**
	 * Marketing pages and blog posts share the automatic translator.
	 *
	 * @dataProvider content_types
	 * @param string $type Post type.
	 */
	public function test_content_updates_and_recovers_historical_conflicts( string $type ): void {
		$id = self::php( '$id = wp_insert_post( array( "post_type" => $input["type"], "post_status" => "publish", "post_title" => "i253 automatic marketing content", "post_content" => "<p>Download the datasheet.</p><img src=\"/unchanged-image.png\" alt=\"Battery\">" ) ); pll_set_post_language( $id, "en" ); wp_update_post( array( "ID" => $id ) ); return $id;', array( 'type' => $type ) );
		try {
			$this->assertSame( 1, self::run_jobs( 'post', $id, true ) );
			$result = self::php(
				'
				$id = $input["id"];
				$de = pll_get_post( $id, "de" );
				$first = get_post( $de )->post_content;
				wp_update_post( array( "ID" => $de, "post_content" => "<p>Old manually protected German.</p>" ) );
				$units = json_decode( get_post_meta( $de, "_linker_i18n_units", true ), true );
				$units["post_content"]["conflict"] = true;
				update_post_meta( $de, "_linker_i18n_units", wp_slash( wp_json_encode( $units ) ) );
				update_post_meta( $de, "_linker_i18n_reviewed", wp_json_encode( array( "post_content" => "*" ) ) );
				update_post_meta( $id, "_linker_i18n_status", "needs_review" );
				do_action( "linker_i18n_translate", "post", $id, false, 1 );
				$state = get_post_meta( $id, "_linker_i18n_status", true );
				$after = get_post( $de )->post_content;
				return array( "first" => $first, "after" => $after, "status" => $state, "lock" => get_post_meta( $de, "_linker_i18n_reviewed", true ) );
				',
				array( 'id' => $id ),
				true
			);
			$this->assertSame( 'synced', $result['status'] );
			$this->assertStringContainsString( 'Datenblatt', $result['after'] );
			$this->assertStringContainsString( 'src="/unchanged-image.png"', $result['after'] );
			$this->assertStringNotContainsString( 'Old manually protected', $result['after'] );
			$this->assertSame( '', $result['lock'] );
		} finally {
			self::remove_pair( $id );
		}
	}

	/**
	 * A source edit during a running unique action gets a successor action.
	 */
	public function test_source_saved_during_translation_is_eventually_current(): void {
		$id = self::php( '$id = wp_insert_post( array( "post_type" => "page", "post_status" => "publish", "post_title" => "i253 concurrent edit", "post_content" => "<p>First version.</p>" ) ); pll_set_post_language( $id, "en" ); wp_update_post( array( "ID" => $id ) ); return $id;' );
		try {
			$ran = self::php(
				'
				$id = $input["id"];
				$changed = false;
				add_filter( "pre_http_request", static function ( $pre, $args, $url ) use ( $id, &$changed ) {
					if ( ! $changed && str_starts_with( $url, (string) getenv( "LINKER_I18N_STUB" ) ) ) {
						$changed = true;
						wp_update_post( array( "ID" => $id, "post_content" => "<p>Latest version.</p>" ) );
					}
					return $pre;
				}, 1, 3 );
				foreach ( as_get_scheduled_actions( array( "hook" => "linker_i18n_translate", "group" => "linker-i18n", "status" => "pending", "per_page" => -1 ), "ids" ) as $action ) {
					$args = ActionScheduler::store()->fetch_action( $action )->get_args();
					if ( "post" === $args[0] && $id === (int) $args[1] ) { ActionScheduler_QueueRunner::instance()->process_action( $action, "WP CLI" ); }
				}
				return $changed;
				',
				array( 'id' => $id ),
				true
			);
			$this->assertTrue( $ran );
			$this->assertSame( 1, self::run_jobs( 'post', $id, true ) );
			$result = self::php( '$de = pll_get_post( $input["id"], "de" ); return array( get_post_meta( $input["id"], "_linker_i18n_status", true ), get_post( $de )->post_content );', array( 'id' => $id ) );
			$this->assertSame( array( 'synced', '<p>[de] Latest version.</p>' ), $result );
		} finally {
			self::remove_pair( $id );
		}
	}

	/**
	 * The digest's projection lists failed English content once and clears on success.
	 */
	public function test_exception_report_excludes_templates_german_and_normal_queue(): void {
		$result = self::php(
			'
			$ids = array();
			try {
				foreach ( array( array( "page", "en", "failed" ), array( "page", "de", "failed" ), array( "lc_partial", "en", "failed" ), array( "post", "en", "pending" ) ) as $fixture ) {
					$id = wp_insert_post( array( "post_type" => $fixture[0], "post_status" => "publish", "post_title" => "i253 report fixture" ) );
					$ids[] = $id;
					pll_set_post_language( $id, $fixture[1] );
					update_post_meta( $id, "_linker_i18n_status", $fixture[2] );
					update_post_meta( $id, "_linker_i18n_note", "DeepSeek answered HTTP 402" );
				}
				$report = new Linker\I18n\Translation\StatusReport();
				$before = array_values( array_filter( $report->issues(), static fn( $row ) => in_array( $row["id"], $ids, true ) ) );
				update_post_meta( $ids[0], "_linker_i18n_status", "synced" );
				$after = array_values( array_filter( $report->issues(), static fn( $row ) => in_array( $row["id"], $ids, true ) ) );
				return array( "before" => $before, "after" => $after, "source" => $ids[0] );
			} finally {
				foreach ( $ids as $id ) { wp_delete_post( $id, true ); }
			}
			'
		);
		$this->assertCount( 1, $result['before'] );
		$this->assertSame( $result['source'], $result['before'][0]['id'] );
		$this->assertSame( 'DeepSeek answered HTTP 402', $result['before'][0]['reason'] );
		$this->assertStringContainsString( 'post.php?post=', $result['before'][0]['edit_url'] );
		$this->assertSame( array(), $result['after'] );
	}

	/**
	 * Removes a fixture's language pair and all queued attempts.
	 *
	 * @param int $id English source.
	 */
	private static function remove_pair( int $id ): void {
		self::php( '$de = pll_get_post( $input["id"], "de" ); foreach ( as_get_scheduled_actions( array( "hook" => "linker_i18n_translate", "group" => "linker-i18n", "status" => "pending", "per_page" => -1 ), "ids" ) as $action ) { $args = ActionScheduler::store()->fetch_action( $action )->get_args(); if ( "post" === $args[0] && $input["id"] === (int) $args[1] ) { ActionScheduler::store()->cancel_action( $action ); } } if ( $de ) { wp_delete_post( $de, true ); } wp_delete_post( $input["id"], true ); return true;', array( 'id' => $id ) );
	}

	/**
	 * All pages, including marketing content, and blog posts participate.
	 *
	 * @return array<string, array{string}>
	 */
	public function content_types(): array {
		return array(
			'marketing page' => array( 'page' ),
			'blog post'      => array( 'post' ),
		);
	}
}
