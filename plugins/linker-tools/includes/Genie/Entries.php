<?php
/**
 * Four page chip groups, the standing dock, and the AI disclosure sentence.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Genie;

/**
 * Prints the opening prompts per page type and the dock on every page. The
 * chips and the dock only print markup; the React app is loaded on the first
 * click (docs/specs/13-genie.md).
 */
class Entries {

	/**
	 * Script handle of the Genie entry (registered by Assets on init).
	 */
	public const HANDLE = 'linker-tools-genie';

	/**
	 * Handle of the search box's script (a plain asset, not a built entry).
	 */
	public const SEARCH_HANDLE = 'linker-tools-search-ask';

	/**
	 * Sets up the entries.
	 *
	 * @param string $plugin_file Absolute path of the main plugin file.
	 */
	public function __construct( private readonly string $plugin_file ) {}

	/**
	 * Hooks the chips and the dock; runs during plugin registration.
	 */
	public function register(): void {
		add_action( 'wp_footer', array( $this, 'dock' ) );
		add_action( 'woocommerce_before_shop_loop', array( $this, 'shop_chip' ) );
		add_action( 'woocommerce_single_product_summary', array( $this, 'product_chips' ), 35 );
		add_action( 'woocommerce_before_cart', array( $this, 'draft_chips' ) );
		add_action( 'woocommerce_account_dashboard', array( $this, 'account_chips' ) );
		add_shortcode( 'linker_genie_ask', array( $this, 'ask_shortcode' ) );
		add_action( 'wp_enqueue_scripts', array( $this, 'search_assets' ) );
	}

	/**
	 * The Ask Genie chip of the catalogue search box, mountable in the
	 * LiveCanvas templates that render the catalogue (ticket #68: the markup
	 * of the search box itself belongs to those templates; this chip and its
	 * script are the part the entries own). The chip is hidden until the
	 * script's question detection shows it — without JavaScript the search
	 * box is the plain form it always was.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function ask_shortcode( $atts = array() ): string {
		unset( $atts );
		return $this->ask_chip();
	}

	/**
	 * The chip the search box shows for a question: it opens Genie with the
	 * typed text (the dock's loader boots the app on the same click).
	 */
	public function ask_chip(): string {
		return sprintf(
			'<button type="button" class="linker-genie-ask min-h-11 rounded-xl border border-neutral-200 bg-white px-4 py-2 text-sm font-semibold text-[#0c7f73]" data-linker-genie-open data-linker-ask-genie hidden><span aria-hidden="true">&#10022;</span> %s</button>',
			esc_html__( 'Ask Genie', 'linker-tools' )
		);
	}

	/**
	 * The search box's script: on the pages that carry the catalogue's search
	 * box (the catalogue and its categories) and on pages that mount the chip
	 * shortcode. The chip is markup of those pages; the script only binds to
	 * what they carry.
	 */
	public function search_assets(): void {
		if ( is_admin() || ! $this->has_search_surface() ) {
			return;
		}
		$base = plugin_dir_path( $this->plugin_file );
		wp_enqueue_script(
			self::SEARCH_HANDLE,
			plugins_url( 'assets/search-ask.js', $this->plugin_file ),
			array(),
			(string) filemtime( $base . 'assets/search-ask.js' ),
			array( 'in_footer' => true )
		);
		$config = array(
			'input'          => '#search-box',
			'chip'           => '[data-linker-ask-genie]',
			'endpoint'       => esc_url_raw( rest_url( 'linker/v1/catalog-search' ) ),
			'lang'           => $this->locale(),
			'questionLength' => 8,
			'queryLength'    => 2,
			'timeout'        => 1500,
		);
		wp_add_inline_script(
			self::SEARCH_HANDLE,
			'window.linkerSearchAsk = ' . wp_json_encode( $config ) . ';',
			'before'
		);
	}

	/**
	 * Whether the page carries the catalogue's search box or mounts the chip.
	 */
	private function has_search_surface(): bool {
		if ( function_exists( 'is_shop' ) && ( is_shop() || is_product_taxonomy() ) ) {
			return true;
		}
		$post = get_post();
		return $post instanceof \WP_Post
			&& has_shortcode( (string) $post->post_content, 'linker_genie_ask' );
	}

	/**
	 * Standing dock: the open button and the hidden mount the app renders into.
	 */
	public function dock(): void {
		if ( is_admin() ) {
			return;
		}
		$locale  = $this->locale();
		$page    = $this->page_context();
		$mount   = 'linker-genie-mount';
		$payload = array(
			'src'          => $this->script_src(),
			'deps'         => $this->script_deps(),
			'translations' => $this->script_translations(),
		);
		echo '<div class="linker-genie">';
		printf(
			'<button type="button" class="linker-genie-open" data-linker-genie-open aria-expanded="false" aria-controls="%1$s">%2$s</button>',
			esc_attr( $mount ),
			esc_html__( 'Ask Genie', 'linker-tools' )
		);
		printf(
			'<div id="%1$s" class="linker-genie-panel" data-linker-genie-mount hidden>',
			esc_attr( $mount )
		);
		printf(
			'<div data-linker-app="genie" data-locale="%1$s" data-page-type="%2$s" data-turn-url="%3$s" data-vote-url="%4$s" data-rest-url="%5$s" data-rest-nonce="%6$s" data-disclosure="%7$s" data-account-url="%8$s" data-prompts=\'%9$s\'></div>',
			esc_attr( $locale ),
			esc_attr( $page['type'] ),
			esc_attr( esc_url_raw( rest_url( Proxy::NAMESPACE . Proxy::ROUTE ) ) ),
			esc_attr( esc_url_raw( rest_url( Proxy::NAMESPACE . Proxy::ROUTE ) ) ),
			esc_attr( esc_url_raw( rest_url() ) ),
			esc_attr( wp_create_nonce( 'wp_rest' ) ),
			esc_attr( $this->disclosure( $locale ) ),
			esc_attr( esc_url_raw( home_url( '/my-account/' ) ) ),
			esc_attr( (string) wp_json_encode( $this->prompts( $page, $locale ) ) ) // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- already inside esc_attr; the cast silences a false positive on (string).
		);
		echo '</div>';
		if ( '' !== $payload['src'] ) {
			// The loader: on the first open/chip click it injects the entry's
			// WordPress dependencies, the script translations, and the built
			// app, then reveals the panel. This is the whole of the "first
			// click loads the JS" mechanism. The payload rides in a data
			// attribute: attribute values are entity-decoded by the HTML
			// parser, so getAttribute() yields the clean JSON (script text
			// would keep the esc_html entities).
			wp_print_inline_script_tag(
				<<<'JS'
(function () {
	var payload = null;
	try {
		payload = JSON.parse(
			document
				.querySelector('[data-linker-genie-loader]')
				.getAttribute('data-linker-genie-boot-payload')
		);
	} catch (error) {
		return;
	}
	var loaded = false;
	function boot() {
		if (loaded) {
			return;
		}
		loaded = true;
		var finish = function () {
			(payload.translations || []).forEach(function (js) {
				var data = document.createElement('script');
				data.text = js;
				document.body.appendChild(data);
			});
			var app = document.createElement('script');
			app.src = payload.src;
			app.async = false;
			document.body.appendChild(app);
		};
		var deps = payload.deps;
		if (deps.length === 0) {
			finish();
			return;
		}
		// An inline script runs the moment it is inserted, so the
		// translations may only be inserted once the dependencies have
		// executed — they call wp.i18n. Classic scripts with async=false
		// execute in insertion order, and "load" fires after execution;
		// the last dependency's load is therefore the signal. "error"
		// proceeds too: the app fails on the missing global anyway, and
		// the panel must still open.
		var proceeded = false;
		var proceed = function () {
			if (proceeded) {
				return;
			}
			proceeded = true;
			finish();
		};
		deps.forEach(function (url, index) {
			var dep = document.createElement('script');
			dep.src = url;
			dep.async = false;
			if (index === deps.length - 1) {
				dep.addEventListener('load', proceed);
				dep.addEventListener('error', proceed);
			}
			document.body.appendChild(dep);
		});
	}
	document.addEventListener(
		'click',
		function (event) {
			var trigger = event.target.closest(
				'[data-linker-genie-open]'
			);
			if (!trigger) {
				return;
			}
			boot();
			var panel = document.querySelector(
				'[data-linker-genie-mount]'
			);
			if (panel) {
				panel.hidden = false;
			}
			document
				.querySelectorAll('[data-linker-genie-open]')
				.forEach(function (button) {
					button.setAttribute('aria-expanded', 'true');
				});
		},
		true
	);
})();
JS,
				array(
					'data-linker-genie-loader'       => true,
					'data-linker-genie-boot-payload' => (string) wp_json_encode( $payload ),
				)
			);
		}
		echo '</div>';
	}

	/**
	 * Shop chip: opens Genie over the catalogue.
	 */
	public function shop_chip(): void {
		$this->chip( __( 'Ask Genie', 'linker-tools' ), 'category' );
	}

	/**
	 * Product page chips.
	 */
	public function product_chips(): void {
		$this->chip( __( 'What pairs with this model?', 'linker-tools' ), 'product' );
		$this->chip( __( 'Compare with…', 'linker-tools' ), 'product' );
		$this->chip( __( 'Documents', 'linker-tools' ), 'product' );
	}

	/**
	 * Solution draft chips.
	 */
	public function draft_chips(): void {
		$this->chip( __( 'Check my draft', 'linker-tools' ), 'draft' );
		$this->chip( __( 'What happens next?', 'linker-tools' ), 'draft' );
	}

	/**
	 * Account chips.
	 */
	public function account_chips(): void {
		$this->chip( __( 'Where is my Proforma?', 'linker-tools' ), 'account' );
	}

	/**
	 * One chip that opens the dock with a starting question.
	 *
	 * @param string $label Chip label.
	 * @param string $type  Page type.
	 */
	public function chip( string $label, string $type ): void {
		printf(
			'<button type="button" class="linker-genie-chip" data-linker-genie-open data-page-type="%1$s">%2$s</button>',
			esc_attr( $type ),
			esc_html( $label )
		);
	}

	/**
	 * The opening prompts of one page type in its language.
	 *
	 * @param array{type: string} $page   Page context.
	 * @param string              $locale `en` or `de`.
	 * @return list<string>
	 */
	public function prompts( array $page, string $locale ): array {
		$de = 'de' === $locale;
		switch ( $page['type'] ) {
			case 'product':
				return array(
					$de ? 'Was passt zu diesem Modell?' : 'What pairs with this model?',
					$de ? 'Vergleichen mit …' : 'Compare with…',
					$de ? 'Unterlagen' : 'Documents',
				);
			case 'draft':
				return array(
					$de ? 'Meinen Entwurf prüfen' : 'Check my draft',
					$de ? 'Wie geht es weiter?' : 'What happens next?',
				);
			case 'account':
				return array(
					$de ? 'Wo steht meine Proforma?' : 'Where is my Proforma?',
					$de ? 'Wie geht es weiter?' : 'What happens next?',
				);
			case 'category':
				return array(
					__( 'Ask Genie', 'linker-tools' ),
					$de
						? 'Ich brauche einen dreiphasigen Hybridwechselrichter für ein Wohngebäude mit 10 kWp PV.'
						: 'I need a three-phase hybrid inverter for a home with 10 kWp PV.',
				);
			default:
				return array(
					__( 'Ask Genie', 'linker-tools' ),
					$de
						? 'Ich brauche einen Hybridwechselrichter für ein Wohngebäude.'
						: 'I need a hybrid inverter for a home.',
				);
		}
	}

	/**
	 * Page context from the current query.
	 *
	 * @return array{type: string, product_id?: int}
	 */
	public function page_context(): array {
		if ( function_exists( 'is_product' ) && is_product() ) {
			return array(
				'type'       => 'product',
				'product_id' => (int) get_queried_object_id(),
			);
		}
		if ( function_exists( 'is_cart' ) && is_cart() ) {
			return array( 'type' => 'draft' );
		}
		if ( function_exists( 'is_account_page' ) && is_account_page() ) {
			return array( 'type' => 'account' );
		}
		if ( function_exists( 'is_shop' ) && ( is_shop() || is_product_taxonomy() ) ) {
			return array( 'type' => 'category' );
		}
		return array( 'type' => 'other' );
	}

	/**
	 * The AI disclosure, spoken once at the start of the thread
	 * (docs/specs/13-genie.md; naming per AGENTS.md §1).
	 *
	 * @param string $locale `en` or `de`.
	 */
	public function disclosure( string $locale ): string {
		return 'de' === $locale
			? 'Hallo, ich bin Genie, der KI-Assistent von Linker. Sie chatten mit einem KI-System.'
			: "Hi, I'm Genie, Linker's AI assistant. You're chatting with an AI system.";
	}

	/**
	 * `en` or `de` from the page's language.
	 *
	 * @return 'en'|'de'
	 */
	private function locale(): string {
		$lang = function_exists( 'determine_locale' ) ? determine_locale() : 'en_US';
		return str_starts_with( strtolower( $lang ), 'de' ) ? 'de' : 'en';
	}

	/**
	 * URL of the built Genie script, empty when Assets has not registered it.
	 */
	private function script_src(): string {
		$script = wp_scripts()->query( self::HANDLE );
		return ( $script && is_string( $script->src ) ) ? $script->src : '';
	}

	/**
	 * URLs of the entry's WordPress dependencies, in registration order.
	 *
	 * @return list<string>
	 */
	private function script_deps(): array {
		$urls = array();
		$walk = function ( string $handle ) use ( &$urls, &$walk ): void {
			$script = wp_scripts()->query( $handle );
			if ( ! $script || ! is_string( $script->src ) ) {
				return;
			}
			foreach ( $script->deps as $dep ) {
				$walk( (string) $dep );
			}
			// The entry itself is not one of its dependencies: the loader
			// appends the entry after these URLs, and a self-reference would
			// execute the app twice (a second mount with an already-read
			// config).
			if ( self::HANDLE === $handle ) {
				return;
			}
			$url = (string) $script->src;
			if ( '' !== $url && ! in_array( $url, $urls, true ) ) {
				$urls[] = $url;
			}
		};
		$walk( self::HANDLE );
		return $urls;
	}

	/**
	 * Translation data of the entry and its dependencies, in dependency
	 * order — what a regular enqueue would print with
	 * WP_Scripts::print_translations() before each script. A normal enqueue
	 * never runs here (the boot loader appends the tags itself), so the
	 * content rides in the boot payload and the loader inserts it after the
	 * dependencies, before the app.
	 *
	 * @return list<string>
	 */
	private function script_translations(): array {
		$scripts = array();
		$walk    = function ( string $handle ) use ( &$scripts, &$walk ): void {
			$script = wp_scripts()->query( $handle );
			if ( ! $script || ! is_string( $script->src ) ) {
				return;
			}
			foreach ( $script->deps as $dep ) {
				$walk( (string) $dep );
			}
			$js = wp_scripts()->print_translations( $handle, false );
			if ( is_string( $js ) && '' !== $js ) {
				$scripts[] = $js;
			}
		};
		$walk( self::HANDLE );
		return $scripts;
	}
}
