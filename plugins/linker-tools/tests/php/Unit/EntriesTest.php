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

	use PageQuery;

	/**
	 * Whether the commerce account entry shortcode is active.
	 *
	 * @var bool
	 */
	private bool $account_entries = false;

	/** The LC guest entries sit beside the workspace's React mount. */
	public function test_workspace_includes_the_native_guest_account_entries(): void {
		$this->frontend( 'de', array( 'type' => 'other' ) );
		$this->account_entries = true;
		WP_Mock::userFunction(
			'do_shortcode',
			array(
				'args'   => array( '[linker_guest_account_links]' ),
				'return' => '<div class="linker-guest-account-links">Anmelden / Konto erstellen</div>',
			)
		);

		$html = ( new Entries( '/plugin/linker-tools.php' ) )->workspace_shortcode();

		$this->assertStringContainsString( 'linker-guest-account-links', $html );
		$this->assertStringContainsString( 'Anmelden / Konto erstellen', $html );
	}

	/**
	 * A previous test's shortcode must not mark this request as a workspace.
	 */
	public function setUp(): void {
		parent::setUp();
		Entries::reset_workspace_rendered();
	}

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
		// A guest's mount: an address field for the email, and the days a
		// guest's conversations are kept, from the retention rule (#235).
		$this->assertStringContainsString( 'data-signed-in="0"', $html );
		$this->assertStringContainsString( 'data-retention-days="90"', $html );
		$inline = $GLOBALS['linker_tools_test_inline_scripts'][0][1] ?? array();
		$this->assertArrayHasKey( 'data-linker-genie-loader', $inline );
		$this->assertStringContainsString( 'genie.js?ver=abc123', (string) $inline['data-linker-genie-boot-payload'], 'the loader busts the host cache with the registered version' );
		$payload = json_decode( (string) $inline['data-linker-genie-boot-payload'], true );
		$this->assertSame( 'Genie could not load.', $payload['error'] );
		$this->assertSame( 'Try again', $payload['retry'] );
		$this->assertConditionsMet();
	}

	/**
	 * German pages get the German disclosure; the prompts are translated
	 * through the German catalogue (msgids here, the catalogue's coverage is
	 * `just i18n-coverage`).
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
		$this->assertStringContainsString( 'Where is my Proforma?', $html );
			$this->assertStringContainsString( 'data-page-type="account"', $html );
			$this->assertStringContainsString( 'data-workspace-url="https://de-linker.test/genie/"', $html );
			$this->assertConditionsMet();
	}

	/**
	 * The advisor page prints the mount the loader handshake looks up, next
	 * to the app mount. Its loader opens on ready and stays open while the
	 * app loads: the page has no bubble that could reopen a hidden panel.
	 */
	public function test_workspace_page_enters_the_loader_handshake(): void {
		$GLOBALS['linker_tools_test_inline_scripts'] = array();
		$this->frontend( 'en', array( 'type' => 'other' ), 'genie' );
		WP_Mock::userFunction(
			'wp_scripts',
			array(
				'return' => static fn() => new FakeScripts(),
			)
		);

		$shortcode = ( new Entries( '/plugin/linker-tools.php' ) )->workspace_shortcode( array() );
		$html      = $this->capture( array( new Entries( '/plugin/linker-tools.php' ), 'dock' ) );

		$this->assertStringContainsString( 'data-linker-app="genie"', $shortcode );
		$this->assertStringContainsString( 'data-linker-genie-mount', $shortcode );
		$this->assertStringContainsString( 'data-surface="workspace"', $shortcode );
		$this->assertStringNotContainsString( 'data-linker-genie-open', $html );
		$inline  = $GLOBALS['linker_tools_test_inline_scripts'][0][1] ?? array();
		$payload = json_decode( (string) ( $inline['data-linker-genie-boot-payload'] ?? '' ), true );
		$this->assertTrue( $payload['open'] );
		$script = (string) ( $GLOBALS['linker_tools_test_inline_scripts'][0][0] ?? '' );
			$this->assertStringContainsString( 'if (!panel)', $script );
			$this->assertStringContainsString( 'shell(!!payload.open)', $script );
			$this->assertStringNotContainsString( 'shell(false)', $script );
			$this->assertStringContainsString( 'if (payload.open)', $script );
			$this->assertMatchesRegularExpression( '/if \(payload\.open\) \{\s*pendingOpen = true;\s*boot\(\);/', $script );
		$this->assertConditionsMet();
	}

	/**
	 * A renamed advisor page still printed the workspace shortcode. The
	 * slug no longer matches, but the shortcode already rendered the
	 * mount. The dock must boot that mount and must not print a second
	 * helper: two mounts are two apps on one cookie.
	 */
	public function test_a_rendered_workspace_is_not_printed_again_when_the_slug_differs(): void {
		$GLOBALS['linker_tools_test_inline_scripts'] = array();
		$this->frontend( 'en', array( 'type' => 'other' ), 'advisor-renamed' );
		WP_Mock::userFunction(
			'wp_scripts',
			array(
				'return' => static fn() => new FakeScripts(),
			)
		);

		$shortcode = ( new Entries( '/plugin/linker-tools.php' ) )->workspace_shortcode( array() );
		$html      = $this->capture( array( new Entries( '/plugin/linker-tools.php' ), 'dock' ) );

		$this->assertSame( 1, substr_count( $shortcode . $html, 'data-linker-app="genie"' ) );
		$this->assertStringNotContainsString( 'data-linker-genie-open', $html );
		$inline  = $GLOBALS['linker_tools_test_inline_scripts'][0][1] ?? array();
		$payload = json_decode( (string) ( $inline['data-linker-genie-boot-payload'] ?? '' ), true );
		$this->assertTrue( $payload['open'] );
		$this->assertConditionsMet();
	}

	/**
	 * The queried page is the workspace page's slug, but its template no
	 * longer prints the workspace. A dock that trusts the slug would boot an
	 * empty page and hide the helper. The helper is what a page without the
	 * mount gets.
	 */
	public function test_a_matching_slug_without_the_workspace_template_keeps_the_helper(): void {
		$GLOBALS['linker_tools_test_inline_scripts'] = array();
		$this->frontend( 'en', array( 'type' => 'other' ), 'genie' );
		WP_Mock::userFunction(
			'wp_scripts',
			array(
				'return' => static fn() => new FakeScripts(),
			)
		);

		$html = $this->capture( array( new Entries( '/plugin/linker-tools.php' ), 'dock' ) );

		$this->assertStringContainsString( 'data-linker-genie-open', $html );
		$this->assertStringContainsString( 'data-surface="helper"', $html );
		$this->assertStringNotContainsString( 'data-surface="workspace"', $html );
		$this->assertConditionsMet();
	}

	/**
	 * A German page links the full-page workspace to the German Genie
	 * page. The language layer, not the locale string, decides.
	 */
	public function test_german_page_links_the_german_workspace(): void {
		// The Genie page (41) and its German twin (42): PageQuery's site.
		$this->frontend( 'de_DE_formal', array( 'type' => 'other' ), '', 'de' );
		WP_Mock::userFunction(
			'get_permalink',
			array(
				'args'   => array( 42 ),
				'return' => 'https://de-linker.test/de/genie/',
			)
		);
		WP_Mock::userFunction(
			'wp_scripts',
			array(
				'return' => static fn() => new FakeScripts(),
			)
		);

		$html = $this->capture( array( new Entries( '/plugin/linker-tools.php' ), 'dock' ) );

		$this->assertStringContainsString(
			'data-workspace-url="https://de-linker.test/de/genie/"',
			$html
		);
		$this->assertConditionsMet();
	}

	/**
	 * Each of the eight kinds of page, and the rest, gets two or three
	 * opening prompts of its own; the product and the product category are
	 * named (目标 3: "打开即点名当前产品或分类"), and the pages with the
	 * preview card offer the card's questions.
	 *
	 * @dataProvider prompt_pages
	 *
	 * @param string $page  A page of PageQuery.
	 * @param string $first The first prompt.
	 */
	public function test_prompts_per_page( string $page, string $first ): void {
		$this->query( $page );
		WP_Mock::passthruFunction( '__' );
		WP_Mock::userFunction( 'get_terms', array( 'return' => array() ) );
		WP_Mock::userFunction( 'get_posts', array( 'return' => array() ) );
		$entries = new Entries( '/plugin/linker-tools.php' );

		$prompts = $entries->prompts( $entries->page_context() );

		$this->assertSame( $first, $prompts[0] );
		$this->assertGreaterThanOrEqual( 2, count( $prompts ) );
		$this->assertLessThanOrEqual( 3, count( $prompts ) );
		foreach ( $prompts as $prompt ) {
			$this->assertStringNotContainsString( '%s', $prompt );
		}
	}

	/**
	 * Pages and their first prompt.
	 *
	 * @return array<string, array{0: string, 1: string}>
	 */
	public function prompt_pages(): array {
		return array(
			'home'             => array( 'home', 'Which batteries work with my inverter?' ),
			'product'          => array( 'product', 'What pairs with the SAJ H2-10K-T3?' ),
			'product category' => array( 'category', 'EMS & Monitoring: which model fits my project?' ),
			'all products'     => array( 'shop', 'Which model fits my project?' ),
			'solution'         => array( 'solution', 'What do I need for a residential storage system?' ),
			'marketing page'   => array( 'about', 'Summarize this page' ),
			'blog post'        => array( 'post', 'Summarize this post' ),
			'blog index'       => array( 'blog', 'Which of these posts cover hybrid inverters?' ),
			'faq'              => array( 'faq', 'Is there a datasheet for my model?' ),
			'solution draft'   => array( 'cart', 'Check my draft' ),
			'account'          => array( 'account', 'Where is my Proforma?' ),
			'other'            => array( 'contact', 'Which model fits my project?' ),
		);
	}

	/**
	 * The mount carries the whole page context the app sends with each turn.
	 */
	public function test_mount_carries_the_page_context(): void {
		$this->frontend( 'en', array( 'type' => 'product' ) );
		WP_Mock::userFunction( 'wp_scripts', array( 'return' => static fn() => new FakeScripts() ) );

		$html = $this->capture( array( new Entries( '/plugin/linker-tools.php' ), 'dock' ) );

		preg_match( "/data-page='([^']*)'/", $html, $found );
		$this->assertSame(
			array(
				'type'       => 'product',
				'title'      => 'SAJ H2-10K-T3 (10 kW three-phase hybrid inverter)',
				'product_id' => 4107,
				'post_id'    => 4107,
				'url'        => 'https://de-linker.test/product/saj-h2-10k-t3/',
			),
			json_decode( html_entity_decode( $found[1] ?? '' ), true )
		);
		$this->assertConditionsMet();
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
			static fn() => ( new Entries( '/plugin/linker-tools.php' ) )->chip(
				'Compare with…',
				'product',
				'Compare with…'
			)
		);
		$this->assertStringContainsString( 'data-linker-genie-open', $html );
		$this->assertStringContainsString( 'data-page-type="product"', $html );
		$this->assertStringContainsString(
			'data-ask-message="Compare with…"',
			$html
		);
		$this->assertConditionsMet();
	}

	/**
	 * An account chip is the first question, not a button that only opens
	 * an empty panel. The loader reads data-ask-message, and only an explicit
	 * ask is written there — the visible label is not the payload.
	 */
	public function test_account_chip_carries_its_question_as_the_first_ask(): void {
		WP_Mock::passthruFunction( '__' );
		WP_Mock::passthruFunction( 'esc_html' );
		WP_Mock::passthruFunction( 'esc_attr' );
		$html = $this->capture(
			static fn() => ( new Entries( '/plugin/linker-tools.php' ) )->account_chips()
		);
		$this->assertStringContainsString( 'data-linker-genie-open', $html );
		$this->assertStringContainsString(
			'data-ask-message="Where is my Proforma?"',
			$html
		);
		$this->assertStringContainsString( 'data-page-type="account"', $html );
		$this->assertConditionsMet();
	}

	/**
	 * The catalogue opener is a label, not a question. Writing "Ask Genie"
	 * into data-ask-message would send that literal as the first turn
	 * (docs/specs/13-genie.md: the shop opener sends no message).
	 */
	public function test_category_opener_carries_no_ask_payload(): void {
		WP_Mock::passthruFunction( '__' );
		WP_Mock::passthruFunction( 'esc_html' );
		WP_Mock::passthruFunction( 'esc_attr' );
		$html = $this->capture(
			static fn() => ( new Entries( '/plugin/linker-tools.php' ) )->shop_chip()
		);
		$this->assertStringContainsString( 'Ask Genie', $html );
		$this->assertStringContainsString( 'data-linker-genie-open', $html );
		$this->assertStringContainsString( 'data-page-type="category"', $html );
		$this->assertStringNotContainsString( 'data-ask-message', $html );
		$this->assertConditionsMet();
	}

	/**
	 * The loader consumes data-ask-message as the first question, and a
	 * missing attribute opens with nothing. Deleting that read sends the
	 * catalogue label ("Ask Genie") as the first turn, so this fixture fails.
	 * An anchor opener (the empty Proforma request's pill) must ask without
	 * navigating away — its href is the no-JavaScript fallback only.
	 *
	 * The loader is the inline script the dock prints. Running it needs a
	 * process, which WordPress's filesystem layer does not provide.
	 *
	 * phpcs:disable WordPress.WP.AlternativeFunctions, WordPress.PHP.DiscouragedPHPFunctions.system_calls_shell_exec, WordPress.PHP.DiscouragedPHPFunctions.system_calls_proc_open
	 */
	public function test_loader_sends_the_ask_attribute_and_not_a_bare_label(): void {
		$GLOBALS['linker_tools_test_inline_scripts'] = array();
		$this->frontend( 'en', array( 'type' => 'category' ) );
		WP_Mock::userFunction(
			'wp_scripts',
			array(
				'return' => static fn() => new FakeScripts(),
			)
		);

		$this->capture( array( new Entries( '/plugin/linker-tools.php' ), 'dock' ) );

		$script = (string) ( $GLOBALS['linker_tools_test_inline_scripts'][0][0] ?? '' );
		$node   = trim( (string) shell_exec( 'command -v node' ) );
		$this->assertNotSame( '', $node, 'node is required to run the loader fixture' );
		$fixture = tempnam( sys_get_temp_dir(), 'genie-loader-' );
		$this->assertIsString( $fixture );
		file_put_contents(
			$fixture,
			<<<'JS'
class El {
	constructor(name) { this.nodeName = name; this.tagName = name.toUpperCase(); this.attrs = {}; this.hidden = true; this.children = []; this.textContent = ''; this.className = ''; this.src = ''; }
	addEventListener() {}
	setAttribute(name, value) { this.attrs[name] = String(value); }
	getAttribute(name) { return Object.prototype.hasOwnProperty.call(this.attrs, name) ? this.attrs[name] : null; }
	appendChild(child) { this.children.push(child); return child; }
	remove() {}
	closest(selector) { return selector === '[data-linker-genie-open]' && this.getAttribute('data-linker-genie-open') !== null ? this : null; }
	dispatchEvent(event) { window.dispatchEvent(Object.assign(event, { target: this })); }
}
const mount = new El('div');
mount.setAttribute('data-linker-genie-mount', '');
const loader = new El('script');
loader.setAttribute('data-linker-genie-loader', '');
loader.setAttribute('data-linker-genie-boot-payload', JSON.stringify({ src: 'genie.js', deps: [], translations: [], error: 'Genie could not load.', retry: 'Try again', open: false }));
const listeners = {};
function on(type, fn) { (listeners[type] = listeners[type] || []).push(fn); }
function emit(type, event) { (listeners[type] || []).forEach((fn) => fn(event)); }
global.window = { addEventListener: on, dispatchEvent(event) { emit(event.type, event); } };
global.document = {
	querySelector(selector) { return selector === '[data-linker-genie-loader]' ? loader : selector === '[data-linker-genie-mount]' ? mount : null; },
	querySelectorAll() { return []; },
	createElement(name) { return new El(name); },
	body: { appendChild() {} },
	addEventListener(type, fn, capture) { window.addEventListener(type, fn, capture); },
};
JS . $script . <<<'JS'

var asks = [];
window.addEventListener('linker-genie-ready', function () {
	window.dispatchEvent(new CustomEvent('linker-genie-state', { detail: { open: true } }));
});
window.addEventListener('linker-genie-open', function (event) {
	asks.push(event.detail && event.detail.message);
});
var events = [];
function click(button) {
	var event = {
		type: 'click', target: button, bubbles: true, defaultPrevented: false,
		preventDefault() { this.defaultPrevented = true; },
	};
	events.push(event);
	window.dispatchEvent(event);
}
var labelled = document.createElement('button');
labelled.setAttribute('data-linker-genie-open', '');
labelled.textContent = 'Ask Genie';
document.body.appendChild(labelled);
click(labelled);
window.dispatchEvent({ type: 'linker-genie-ready' });
var asking = document.createElement('button');
asking.setAttribute('data-linker-genie-open', '');
asking.setAttribute('data-ask-message', 'Where is my Proforma?');
asking.textContent = 'Where is my Proforma?';
document.body.appendChild(asking);
click(asking);
// The empty Proforma request's pill is an anchor: the dock opens here, so
// the click must not also navigate to the pill's href.
var pill = document.createElement('a');
pill.setAttribute('data-linker-genie-open', '');
pill.setAttribute('href', '/genie/');
pill.textContent = 'Genie';
document.body.appendChild(pill);
click(pill);
process.stdout.write(JSON.stringify({
	asks: asks,
	buttonPrevented: events[0].defaultPrevented || events[1].defaultPrevented,
	anchorPrevented: events[2].defaultPrevented,
}));
JS
		);
		$run = proc_open(
			array( $node, $fixture ),
			array(
				1 => array( 'pipe', 'w' ),
				2 => array( 'pipe', 'w' ),
			),
			$pipes
		);
		$this->assertIsResource( $run );
		$out = stream_get_contents( $pipes[1] );
		$err = stream_get_contents( $pipes[2] );
		fclose( $pipes[1] );
		fclose( $pipes[2] );
		$code = proc_close( $run );
		unlink( $fixture );
		$this->assertSame( 0, $code, $err );
		$result = (array) json_decode( (string) $out, true );
		$this->assertSame( array( '', 'Where is my Proforma?', '' ), $result['asks'] ?? null, 'every opener asks, the anchor included' );
		$this->assertFalse( (bool) ( $result['buttonPrevented'] ?? true ), 'a button opener has no default action to cancel' );
		$this->assertTrue( (bool) ( $result['anchorPrevented'] ?? false ), 'the anchor opener must not navigate away from the page' );
		$this->assertConditionsMet();
	}
	// phpcs:enable WordPress.WP.AlternativeFunctions, WordPress.PHP.DiscouragedPHPFunctions.system_calls_shell_exec, WordPress.PHP.DiscouragedPHPFunctions.system_calls_proc_open

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
	 * @param string               $slug     Current page slug, empty off a page.
	 * @param string               $language Language layer's answer; empty when it has none.
	 */
	private function frontend( string $locale, array $page, string $slug = '', string $language = '' ): void {
		WP_Mock::userFunction( 'shortcode_exists', array( 'return' => fn (): bool => $this->account_entries ) );
		$kinds = array(
			'product'  => 'product',
			'draft'    => 'cart',
			'account'  => 'account',
			'category' => 'shop',
			'other'    => 'search',
		);
		$this->query( $kinds[ $page['type'] ?? 'other' ], $locale, $language );
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
			'wp_create_nonce',
			array(
				'return' => static fn( string $action ): string => 'nonce-' . $action,
			)
		);
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => false ) );
		WP_Mock::userFunction( 'wp_salt', array( 'return' => 'test-salt' ) );
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
			WP_Mock::userFunction(
				'get_post',
				array(
					'return' => '' === $slug
						? null
						: new \WP_Post(
							(object) array(
								'ID'           => 9,
								'post_name'    => $slug,
								'post_content' => '',
							)
						),
				)
			);
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
