<?php
/**
 * Tests for the entries: dock, chips, prompts and disclosure.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Genie\Entries;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for Entries.
 *
 * @covers \Linker\Tools\Genie\Entries
 */
final class EntriesTest extends TestCase {

	/**
	 * The dock prints the open button, the hidden mount with its config, and
	 * the boot payload with the built script's URLs.
	 */
	public function test_dock_prints_button_mount_and_boot_payload(): void {
		$this->frontend(
			'en',
			array(
				'type'       => 'product',
				'product_id' => 3555,
			)
		);
		WP_Mock::userFunction(
			'wp_scripts',
			array(
				'return' => static function () {
					return new FakeScripts();
				},
			)
		);

		$GLOBALS['linker_tools_test_inline_scripts'] = array();
		$html                                        = $this->capture( array( new Entries( '/plugin/linker-tools.php' ), 'dock' ) );

		$this->assertStringContainsString( 'data-linker-genie-open', $html );
		$this->assertStringContainsString( 'Ask Genie', $html );
		$this->assertStringContainsString( 'data-linker-app="genie"', $html );
		$this->assertStringContainsString( 'data-page-type="product"', $html );
		$this->assertStringContainsString( "I'm Genie, Linker's AI assistant", $html );
		$inline = $GLOBALS['linker_tools_test_inline_scripts'][0][1] ?? array();
		$this->assertArrayHasKey( 'data-linker-genie-loader', $inline );
		$this->assertStringContainsString( 'genie.js', (string) $inline['data-linker-genie-boot-payload'] );
		$payload = json_decode( (string) $inline['data-linker-genie-boot-payload'], true );
		$this->assertSame( 'Genie could not load.', $payload['error'] );
		$this->assertSame( 'Try again', $payload['retry'] );
		$this->assertConditionsMet();
	}

	/**
	 * German pages get the German disclosure and the German prompts.
	 */
	public function test_dock_localizes_disclosure_and_prompts(): void {
		$this->frontend( 'de_DE_formal', array( 'type' => 'account' ) );
		WP_Mock::userFunction(
			'wp_scripts',
			array(
				'return' => static fn() => new FakeScripts(),
			)
		);

		$html = $this->capture( array( new Entries( '/plugin/linker-tools.php' ), 'dock' ) );

		$this->assertStringContainsString( 'der KI-Assistent von Linker', $html );
		$this->assertStringContainsString( 'Wo steht meine Proforma?', $html );
		$this->assertStringContainsString( 'data-page-type="account"', $html );
		$this->assertConditionsMet();
	}

	/**
	 * Each page type gets its own opening prompts, two or three of them.
	 */
	public function test_prompts_per_page_type(): void {
		WP_Mock::passthruFunction( '__' );
		$entries = new Entries( '/plugin/linker-tools.php' );
		$page    = static fn( string $type ): array => array( 'type' => $type );

		$product = $entries->prompts( $page( 'product' ), 'en' );
		$this->assertSame( 'What pairs with this model?', $product[0] );
		$this->assertCount( 3, $product );

		$this->assertSame( 'Check my draft', $entries->prompts( $page( 'draft' ), 'en' )[0] );
		$this->assertSame( 'Where is my Proforma?', $entries->prompts( $page( 'account' ), 'en' )[0] );
		$this->assertSame(
			'I need a three-phase hybrid inverter for a home with 10 kWp PV.',
			$entries->prompts( $page( 'category' ), 'en' )[1]
		);
		$this->assertCount( 2, $entries->prompts( $page( 'other' ), 'en' ) );
		$this->assertSame( 'Was passt zu diesem Modell?', $entries->prompts( $page( 'product' ), 'de' )[0] );
	}

	/**
	 * Without a registered build script the boot payload is not printed, so
	 * nothing on the page points at a missing file.
	 */
	public function test_dock_without_a_built_script_prints_no_boot_payload(): void {
		$GLOBALS['linker_tools_test_inline_scripts'] = array();
		$this->frontend( 'en', array( 'type' => 'other' ) );
		WP_Mock::userFunction(
			'wp_scripts',
			array(
				'return' => static fn() => new FakeScripts( false ),
			)
		);

		$html = $this->capture( array( new Entries( '/plugin/linker-tools.php' ), 'dock' ) );

		$this->assertSame( array(), $GLOBALS['linker_tools_test_inline_scripts'] );
		$this->assertConditionsMet();
	}

	/**
	 * The boot payload carries the script translations (what a regular
	 * enqueue would print), so the app speaks German on the first click even
	 * though it is never enqueued.
	 */
	public function test_dock_boot_payload_carries_the_translations(): void {
		$GLOBALS['linker_tools_test_inline_scripts'] = array();
		$this->frontend( 'de_DE_formal', array( 'type' => 'other' ) );
		WP_Mock::userFunction(
			'wp_scripts',
			array(
				'return' => static fn() => new FakeScripts( true, true ),
			)
		);

		$this->capture( array( new Entries( '/plugin/linker-tools.php' ), 'dock' ) );

		$inline  = $GLOBALS['linker_tools_test_inline_scripts'][0][1] ?? array();
		$payload = json_decode(
			(string) ( $inline['data-linker-genie-boot-payload'] ?? '' ),
			true
		);
		$this->assertIsArray( $payload );
		// WP_Mock passes `__` through, so the payload carries the source
		// strings here; the German wordings live in the hand-written .po.
		$this->assertSame( 'Genie could not load.', $payload['error'] );
		$this->assertSame( 'Try again', $payload['retry'] );
		$this->assertCount( 1, $payload['translations'] );
		$this->assertStringContainsString(
			'setLocaleData',
			(string) $payload['translations'][0]
		);
		$this->assertStringContainsString(
			'Ausblenden',
			(string) $payload['translations'][0]
		);
		$this->assertConditionsMet();
	}

	/**
	 * The chips carry their page type.
	 */
	public function test_chips_carry_their_page_type(): void {
		WP_Mock::passthruFunction( '__' );
		WP_Mock::passthruFunction( 'esc_html' );
		WP_Mock::passthruFunction( 'esc_attr' );
		$html = $this->capture(
			static fn() => ( new Entries( '/plugin/linker-tools.php' ) )->chip( 'Compare with…', 'product' )
		);
		$this->assertStringContainsString( 'data-linker-genie-open', $html );
		$this->assertStringContainsString( 'data-page-type="product"', $html );
		$this->assertConditionsMet();
	}

	/**
	 * The shortcode prints a page type's chip group: the LiveCanvas
	 * templates' entry surface, whose pages never fire the Woo hooks.
	 */
	public function test_chips_shortcode_prints_the_group_of_its_page_type(): void {
		WP_Mock::passthruFunction( '__' );
		WP_Mock::passthruFunction( 'esc_html' );
		WP_Mock::passthruFunction( 'esc_attr' );
		WP_Mock::userFunction(
			'shortcode_atts',
			array(
				'return' => static fn ( array $defaults, array $atts ): array => array_merge( $defaults, $atts ),
			)
		);

		$html = ( new Entries( '/plugin/linker-tools.php' ) )->chips_shortcode( array( 'page_type' => 'product' ) );

		$this->assertSame( 3, substr_count( $html, 'linker-genie-chip' ) );
		$this->assertSame( 3, substr_count( $html, 'data-page-type="product"' ) );

		// No attribute: the current query decides.
		$this->frontend( 'en', array( 'type' => 'category' ) );
		$html = ( new Entries( '/plugin/linker-tools.php' ) )->chips_shortcode( array( 'page_type' => '' ) );
		$this->assertSame( 1, substr_count( $html, 'linker-genie-chip' ) );
		$this->assertStringContainsString( 'data-page-type="category"', $html );
		$this->assertConditionsMet();
	}

	/**
	 * A frontend page in `locale`, outside wp-admin.
	 *
	 * @param string               $locale determine_locale()'s answer.
	 * @param array<string, mixed> $page   Page context answer.
	 */
	private function frontend( string $locale, array $page ): void {
		WP_Mock::userFunction( 'is_admin', array( 'return' => false ) );
		WP_Mock::userFunction( 'determine_locale', array( 'return' => $locale ) );
		WP_Mock::userFunction(
			'is_product',
			array(
				'return' => 'product' === ( $page['type'] ?? '' ),
			)
		);
		WP_Mock::userFunction(
			'is_cart',
			array(
				'return' => 'draft' === ( $page['type'] ?? '' ),
			)
		);
		WP_Mock::userFunction(
			'is_account_page',
			array(
				'return' => 'account' === ( $page['type'] ?? '' ),
			)
		);
		WP_Mock::userFunction(
			'is_shop',
			array(
				'return' => 'category' === ( $page['type'] ?? '' ),
			)
		);
		WP_Mock::userFunction(
			'is_product_taxonomy',
			array(
				'return' => false,
			)
		);
		WP_Mock::userFunction(
			'get_queried_object_id',
			array(
				'return' => $page['product_id'] ?? 0,
			)
		);
		WP_Mock::userFunction(
			'rest_url',
			array(
				'return' => static fn( string $path = '' ): string => 'https://de-linker.test/wp-json/' . $path,
			)
		);
		WP_Mock::userFunction(
			'home_url',
			array(
				'return' => static fn( string $path = '' ): string => 'https://de-linker.test' . $path,
			)
		);
		WP_Mock::userFunction(
			'esc_url_raw',
			array(
				'return' => static fn( string $url ): string => $url,
			)
		);
		WP_Mock::userFunction(
			'wp_create_nonce',
			array(
				'return' => static fn( string $action ): string => 'nonce-' . $action,
			)
		);
		WP_Mock::userFunction(
			'wp_print_inline_script_tag',
			array(
				'return' => static function ( string $script, array $attrs = array() ): void {
					$GLOBALS['linker_tools_test_inline_scripts'][] = array( $script, $attrs );
				},
			)
		);
		WP_Mock::userFunction(
			'wp_json_encode',
			array(
				'return' => static fn( $value ): string => (string) json_encode( $value, JSON_UNESCAPED_UNICODE ), // phpcs:ignore WordPress.WP.AlternativeFunctions.json_encode_json_encode -- test double.
			)
		);
		WP_Mock::passthruFunction( 'esc_html__' );
		WP_Mock::passthruFunction( 'esc_attr' );
		WP_Mock::passthruFunction( 'esc_html' );
			WP_Mock::passthruFunction( '__' );
			WP_Mock::userFunction( 'get_post', array( 'return' => null ) );
	}

	/**
	 * The search box's chip: hidden until the script shows it, opening the
	 * dock on click, with the reviewed label (ticket #68).
	 */
	public function test_ask_chip_is_hidden_until_the_script_shows_it(): void {
		$this->frontend( 'en', array( 'type' => 'category' ) );

		$html = ( new Entries( '/plugin/linker-tools.php' ) )->ask_chip();

		$this->assertStringContainsString( 'data-linker-ask-genie', $html );
		$this->assertStringContainsString( 'data-linker-genie-open', $html );
		$this->assertStringContainsString( ' hidden>', $html );
		$this->assertStringContainsString( 'Ask Genie', $html );
		$this->assertConditionsMet();
	}

	/**
	 * The shortcode prints the same chip, so a LiveCanvas template mounts it
	 * where the search box stands.
	 */
	public function test_ask_shortcode_prints_the_chip(): void {
		$this->frontend( 'de', array( 'type' => 'category' ) );

		$html = ( new Entries( '/plugin/linker-tools.php' ) )->ask_shortcode( array( 'ignored' => 'yes' ) );

		$this->assertStringContainsString( 'data-linker-ask-genie', $html );
		$this->assertStringContainsString( 'Ask Genie', $html );
		$this->assertConditionsMet();
	}

	/**
	 * Output buffering around one call.
	 *
	 * @param callable $call The call.
	 */
	private function capture( callable $call ): string {
		ob_start();
		$call();
		return (string) ob_get_clean();
	}
}
