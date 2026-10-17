<?php
/**
 * The real commerce digest consumes the translation projection without sending.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Integration;

/**
 * Uses the native Block, DigestEmail and Outbox queue with isolated fixtures.
 *
 * @coversNothing
 */
final class DigestBlockTest extends SiteTestCase {

	/**
	 * The registered block renders in the mail locale, with counts, links and routing.
	 */
	public function test_digest_queues_localized_exceptions_and_preserves_routing(): void {
		$result = self::php(
			'
			$options = array(); $ids = array(); $terms = array(); $mail_ids = array(); $wire = 0;
			foreach ( array( "WPLANG", "linker_commerce_mail_sends", "woocommerce_linker_digest_settings" ) as $key ) { $options[$key] = get_option( $key, null ); }
			$jobs = new Linker\Commerce\Mail\JobStore();
			$queued = static fn() => get_posts( array( "post_type" => Linker\Commerce\Mail\JobStore::POST_TYPE, "post_status" => "any", "numberposts" => -1, "fields" => "ids", "suppress_filters" => true ) );
			$baseline = $queued();
			add_filter( "pre_wp_mail", static function ( $pre ) use ( &$wire ) { if ( null === $pre ) { ++$wire; return false; } return $pre; }, PHP_INT_MAX );
			try {
				foreach ( array( array( "page", "en", "failed" ), array( "page", "en", "structure_mismatch" ), array( "page", "en", "synced" ), array( "page", "en", "pending" ), array( "page", "de", "failed" ), array( "lc_partial", "en", "failed" ) ) as $i => $case ) {
					$id = wp_insert_post( array( "post_type" => $case[0], "post_status" => "private", "post_title" => "i253 digest fixture " . $i ) ); $ids[] = $id;
					pll_set_post_language( $id, $case[1] ); update_post_meta( $id, "_linker_i18n_status", $case[2] ); update_post_meta( $id, "_linker_i18n_note", "DeepSeek unavailable" );
				}
				$term = wp_insert_term( "i253 digest term", "category" )["term_id"]; $terms[] = $term;
				pll_set_term_language( $term, "en" ); update_term_meta( $term, "_linker_i18n_status", "failed" ); update_term_meta( $term, "_linker_i18n_note", "DeepSeek unavailable" );
				update_option( "linker_commerce_mail_sends", array_fill( 0, Linker\Commerce\Mail\Throttle::PER_DAY, time() ) );
				update_option( "woocommerce_linker_digest_settings", array( "enabled" => "yes" ) );
				$settings = new Linker\Commerce\Settings\Options(); $result = array();
				foreach ( array( "en_US", "de_DE_formal" ) as $locale ) {
					update_option( "WPLANG", $locale );
					$blocks = ( new Linker\Commerce\Digest\Blocks( $jobs ) )->all();
					$matches = array_values( array_filter( $blocks, static fn( $block ) => "german_translation_exceptions" === $block->id() ) );
					$email = new Linker\Commerce\Digest\DigestEmail( WP_PLUGIN_DIR . "/linker-commerce/linker-commerce.php", $settings );
					$before = $queued(); $email->send_report( $blocks ); $created = array_values( array_diff( $queued(), $before ) ); array_push( $mail_ids, ...$created );
					if ( 1 !== count( $created ) ) { throw new \RuntimeException( "Expected one queued digest." ); }
					$message = $jobs->load( $created[0] )["message"];
					$body = html_entity_decode( $message->body, ENT_QUOTES | ENT_HTML5, "UTF-8" );
					$issues = ( new Linker\I18n\Translation\StatusReport() )->issues();
					$wanted = "en_US" === $locale ? "German translation exceptions (" . count( $issues ) . ")" : "Probleme bei deutschen Übersetzungen (" . count( $issues ) . ")";
					$reason = "en_US" === $locale ? "German out of date: structure differs" : "Deutsch nicht aktuell: abweichende Struktur";
					$link = "en_US" === $locale ? "Open English source" : "Englischen Inhalt öffnen";
					$result[$locale] = array( "blocks" => count( $matches ), "heading" => str_contains( $body, $wanted ), "reason" => str_contains( $body, $reason ), "link" => str_contains( $body, $link ), "failed" => str_contains( $body, "i253 digest fixture 0" ), "structural" => str_contains( $body, "i253 digest fixture 1" ), "term" => str_contains( $body, "i253 digest term" ), "source_url" => str_contains( $body, admin_url( "post.php?post=" . $ids[0] . "&action=edit" ) ), "excluded" => ! str_contains( $body, "i253 digest fixture 2" ) && ! str_contains( $body, "i253 digest fixture 3" ) && ! str_contains( $body, "i253 digest fixture 4" ) && ! str_contains( $body, "i253 digest fixture 5" ), "to" => $message->to === array( $settings->notify_to() ), "bcc" => array() === $settings->notify_bcc() || in_array( "Bcc: " . implode( ", ", $settings->notify_bcc() ), $message->headers, true ) );
				}
				$result["wire_attempts"] = $wire;
				return $result;
			} finally {
				$mail_ids = array_values( array_unique( array_merge( $mail_ids, array_diff( $queued(), $baseline ) ) ) );
				foreach ( array( "linker_i18n_translate", Linker\Commerce\Mail\Outbox::HOOK ) as $hook ) {
					foreach ( as_get_scheduled_actions( array( "hook" => $hook, "status" => "pending", "per_page" => -1 ), "ids" ) as $action ) { $a = ActionScheduler::store()->fetch_action( $action )->get_args(); if ( "linker_i18n_translate" === $hook ? in_array( (int) $a[1], array_merge( $ids, $terms ), true ) : in_array( (int) $a[0], $mail_ids, true ) ) { ActionScheduler::store()->cancel_action( $action ); } }
				}
				foreach ( array_merge( $ids, $mail_ids ) as $id ) { wp_delete_post( $id, true ); } foreach ( $terms as $id ) { wp_delete_term( $id, "category" ); }
				foreach ( $options as $key => $value ) { if ( null === $value ) { delete_option( $key ); } else { update_option( $key, $value ); } }
			}
			'
		);
		foreach ( array( 'en_US', 'de_DE_formal' ) as $locale ) {
			$this->assertSame( 1, $result[ $locale ]['blocks'] );
			foreach ( array( 'heading', 'reason', 'link', 'failed', 'structural', 'term', 'source_url', 'excluded', 'to', 'bcc' ) as $key ) {
				$this->assertTrue( $result[ $locale ][ $key ], $locale . ': ' . $key );
			}
		}
		$this->assertSame( 0, $result['wire_attempts'] );
	}
}
