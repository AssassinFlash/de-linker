<?php
/**
 * Language drafts match the current native identity and paired public context.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Contact;

use Linker\Commerce\Contact\LanguageDraft;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Public comparisons use current identity and native translation pairs.
 *
 * @covers \Linker\Commerce\Contact\LanguageDraft
 */
final class LanguageDraftTest extends TestCase {

	/** The same generated entry runs in the head without reading form or session state. */
	public function test_enqueues_the_generated_classic_entry_in_the_head(): void {
		$root  = dirname( __DIR__, 4 );
		$asset = require $root . '/build/contact-language.asset.php';
		WP_Mock::userFunction(
			'plugins_url',
			array(
				'args'   => array( 'build/contact-language.js', $root . '/linker-commerce.php' ),
				'return' => 'https://linker.test/contact-language.js',
			)
		);
		WP_Mock::userFunction(
			'wp_enqueue_script',
			array(
				'args'  => array( 'linker-contact-language', 'https://linker.test/contact-language.js', $asset['dependencies'], $asset['version'], false ),
				'times' => 1,
			)
		);
		WP_Mock::userFunction( 'get_current_user_id', array( 'times' => 0 ) );
		WP_Mock::userFunction( 'wp_get_session_token', array( 'times' => 0 ) );
		WP_Mock::userFunction( 'WC', array( 'times' => 0 ) );

		LanguageDraft::enqueue();
		$this->assertConditionsMet();
	}

	/** Paired pages share context; a different source or selection does not. */
	public function test_pair_identity_is_independent_of_language_title_and_selection_order(): void {
		$this->environment();
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 5 ) );
		WP_Mock::userFunction( 'pll_get_post', array( 'return' => static fn ( int $id ): int => in_array( $id, array( 842, 6867 ), true ) ? 842 : $id ) );
		$context              = array(
			'type'      => 'page',
			'id'        => 842,
			'title'     => 'English',
			'selection' => array(
				'document' => 'Layout',
				'platform' => 'SAJ',
			),
		);
		$english              = LanguageDraft::attributes( false, $context );
		$context['id']        = 6867;
		$context['title']     = 'Deutsch';
		$context['selection'] = array(
			'platform' => 'SAJ',
			'document' => 'Layout',
		);
		$this->assertSame( $english, LanguageDraft::attributes( false, $context ) );
		$context['id'] = 862;
		$this->assertNotSame( $english, LanguageDraft::attributes( false, $context ) );
		$context['id']                    = 842;
		$context['selection']['document'] = 'Other';
		$this->assertNotSame( $english, LanguageDraft::attributes( false, $context ) );
		$this->assertStringNotContainsString( 'private-session-token', $english );
		$this->assertStringNotContainsString( 'Layout', $english );
		$this->assertStringContainsString( 'data-linker-contact-draft-lifetime="300000"', $english );
		$this->assertNotSame( $english, LanguageDraft::attributes( true, array() ) );
	}

	/** A current native guest session can be read without creating a new cookie. */
	public function test_guest_binding_reads_existing_signed_session_only(): void {
		$this->environment();
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 0 ) );
		$existing = false;
		$id       = 'guest-a';
		$session  = \Mockery::mock( \WC_Session_Handler::class );
		$session->shouldReceive( 'has_session' )->andReturnUsing(
			static function () use ( &$existing ): bool {
				return $existing;
			}
		);
		$session->shouldReceive( 'get_customer_id' )->andReturnUsing(
			static function () use ( &$id ): string {
				return $id;
			}
		);
		$session->shouldNotReceive( 'set_customer_session_cookie' );
		$session->shouldNotReceive( 'set' );
		WP_Mock::userFunction( 'WC', array( 'return' => (object) array( 'session' => $session ) ) );
		$without  = LanguageDraft::attributes( false, array() );
		$existing = true;
		$with     = LanguageDraft::attributes( false, array() );
		$this->assertNotSame( $without, $with );
		$id = 'guest-b';
		$this->assertNotSame( $with, LanguageDraft::attributes( false, array() ) );
	}

	/** Read-only native helpers; no WordPress session or business writes. */
	private function environment(): void {
		$this->plain_text();
		WP_Mock::userFunction( 'wp_get_session_token', array( 'return' => 'private-session-token' ) );
		WP_Mock::userFunction( 'wp_hash', array( 'return' => static fn ( string $value ): string => hash( 'sha256', $value ) ) );
		WP_Mock::userFunction( 'wp_json_encode', array( 'return' => static fn ( mixed $value ): string => (string) json_encode( $value ) ) );
	}
}
