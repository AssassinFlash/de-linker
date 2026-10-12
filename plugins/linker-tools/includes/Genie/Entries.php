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
	 * Set when the workspace shortcode has already rendered this request.
	 *
	 * The dock runs in `wp_footer`, after the template. The shortcode is
	 * the authority for "this page is the workspace": a renamed page still
	 * carries the shortcode, and a page whose template lost it does not.
	 *
	 * @var bool
	 */
	private static bool $workspace_rendered = false;

	/**
	 * Clears the workspace mark. Tests share a process; a request does not.
	 */
	public static function reset_workspace_rendered(): void {
		self::$workspace_rendered = false;
	}

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
		add_shortcode( 'linker_genie_chips', array( $this, 'chips_shortcode' ) );
		add_shortcode( 'linker_genie_workspace', array( $this, 'workspace_shortcode' ) );
		add_action( 'wp_enqueue_scripts', array( $this, 'search_assets' ) );
		add_action( 'wp_enqueue_scripts', array( $this, 'dock_assets' ) );
	}

	/**
	 * The dock's stylesheet: the standing bubble belongs to every front-end
	 * page's chrome, so its registered style loads with the page. The app
	 * script itself still waits for the first click (the dock's loader).
	 */
	public function dock_assets(): void {
		if ( is_admin() ) {
			return;
		}
		wp_enqueue_style( self::HANDLE );
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
	 * The full-page workspace on /linker-advisor/.
	 *
	 * The LiveCanvas template of that page prints this shortcode. It is
	 * the same mount the dock uses, marked as the page surface so the
	 * app renders the history rail instead of the helper card. The
	 * mount element is what the dock loader's ready and failure
	 * protocol looks up (`[data-linker-genie-mount]`); without it the
	 * workspace never enters that handshake. The dock loader still
	 * owns boot, ready and open; this mount does not load a second
	 * copy of the app.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function workspace_shortcode( $atts = array() ): string {
		unset( $atts );
		if ( is_admin() ) {
			return '';
		}
		self::$workspace_rendered = true;
		return sprintf(
			'<div id="linker-genie-mount" class="linker-genie-panel linker-genie-panel--workspace" data-linker-genie-mount>%s</div>',
			$this->mount_markup( 'workspace' )
		);
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
	 * The button is the live page's resting Advisor bubble (50×50, bottom-right
	 * 20/20, hidden under 861px — the live's own switch sits between 860 and
	 * 865, measured 2026-10-12); the word rides in a label the stylesheet keeps
	 * out of sight, as the live button's own label does. The dock adds no flow
	 * height to the page (the live page's bubble is fixed).
	 */
	public function dock(): void {
		if ( is_admin() ) {
			return;
		}
		// The workspace shortcode already printed the mount. This only
		// boots it. A second helper mount would boot a second app
		// against the same cookie. A missing template is not a workspace.
		if ( self::$workspace_rendered ) {
			$this->print_loader( true );
			return;
		}
		$mount   = 'linker-genie-mount';
		$payload = array(
			'src'          => $this->script_src(),
			'deps'         => $this->script_deps(),
			'translations' => $this->script_translations(),
			'error'        => __( 'Genie could not load.', 'linker-tools' ),
			'retry'        => __( 'Try again', 'linker-tools' ),
		);
		echo '<div class="linker-genie">';
		printf(
			'<button type="button" class="linker-genie-open" data-linker-genie-open aria-expanded="false" aria-controls="%1$s" aria-label="%2$s"><span class="linker-genie-open-mark"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7.4 5v10.9a1.8 1.8 0 0 0 1.8 1.8H17" stroke-width="3.1"/><path d="M8.8 8.4C11.8 4.5 16.4 3.1 19.6 3.5" stroke-width="1.5" opacity="0.62"/><circle cx="20.7" cy="4.9" r="1.5" fill="currentColor" stroke="none"/></svg></span><span class="linker-genie-open-label">%2$s</span></button>',
			esc_attr( $mount ),
			esc_html__( 'Ask Genie', 'linker-tools' )
		);
		printf(
			'<div id="%1$s" class="linker-genie-panel" data-linker-genie-mount hidden>',
			esc_attr( $mount )
		);
		// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- mount_markup() escapes every attribute.
		echo $this->mount_markup( 'helper' );
		echo '</div>';
		if ( '' !== $payload['src'] ) {
			$this->print_loader( false );
		}
		echo '</div>';
	}

	/**
	 * The one boot loader. `$open` is the workspace: it has no bubble, so
	 * the loader boots before the script is inserted and opens the mount
	 * once the app reports ready. A click or ask is what boots a helper.
	 *
	 * @param bool $open Whether to boot now and open as soon as the app is ready.
	 */
	private function print_loader( bool $open ): void {
		$payload = array(
			'src'          => $this->script_src(),
			'deps'         => $this->script_deps(),
			'translations' => $this->script_translations(),
			'error'        => __( 'Genie could not load.', 'linker-tools' ),
			'retry'        => __( 'Try again', 'linker-tools' ),
			'open'         => $open,
		);
		if ( '' === $payload['src'] ) {
			return;
		}
		// The loader owns entry delivery: an open click, an ask, or a
		// workspace page (payload.open) boots once, waits for the App's
		// ready event, then opens it with the first ask. The App reports
		// Hide/Open back so the shell and mobile card agree.
		// The payload rides in a data
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
	var ready = false;
		var pendingOpen = false;
		var pendingAsk = '';
		var failure = null;
		function clearFailure() {
			if (failure) {
				failure.remove();
				failure = null;
			}
		}
			function showFailure() {
				clearFailure();
				var panel = document.querySelector('[data-linker-genie-mount]');
				if (!panel) {
					return;
				}
				failure = document.createElement('section');
				failure.className = 'linker-genie-app';
				failure.setAttribute('data-linker-genie-load-error', '');
				var message = document.createElement('p');
				message.className = 'linker-genie-app__error';
				message.setAttribute('role', 'alert');
				message.textContent = payload.error;
				var retry = document.createElement('button');
				retry.type = 'button';
				retry.className = 'linker-genie-app__toggle';
				retry.setAttribute('data-linker-genie-open', '');
				retry.textContent = payload.retry;
				failure.appendChild(message);
				failure.appendChild(retry);
				panel.appendChild(failure);
				shell(true);
			}
		function shell(open) {
		var panel = document.querySelector('[data-linker-genie-mount]');
		if (panel) {
			panel.hidden = !open;
		}
		document.querySelectorAll('[data-linker-genie-open]').forEach(function (button) {
			button.setAttribute('aria-expanded', String(open));
		});
	}
	function deliver() {
		if (!ready || !pendingOpen) {
			return;
		}
		var message = pendingAsk;
		pendingOpen = false;
		pendingAsk = '';
		window.dispatchEvent(new CustomEvent('linker-genie-open', {
			detail: { message: message }
		}));
	}
	function open(message) {
		pendingOpen = true;
		// A plain reopen during loading must not erase the first question.
		if (message && !pendingAsk) {
			pendingAsk = message;
		}
		boot();
		deliver();
	}
				window.addEventListener('linker-genie-ready', function () {
					ready = true;
					clearFailure();
					if (payload.open) {
						pendingOpen = true;
					}
					deliver();
				});
		window.addEventListener('linker-genie-state', function (event) {
		shell(event.detail.open);
	});
	window.addEventListener('linker-genie-ask', function (event) {
		var detail = event.detail;
		if (detail && typeof detail.message === 'string' && detail.message.trim()) {
			open(detail.message);
		}
	});
			function boot() {
				if (loaded) {
					return;
				}
				loaded = true;
				clearFailure();
				// The workspace has no bubble to reopen a hidden page. Keep it
				// visible while the app loads; ready then delivers open.
				// A helper stays closed until the visitor's click is delivered.
				shell(!!payload.open);
		var failed = false;
		var inserted = [];
		function fail() {
			if (failed) {
				return;
			}
			failed = true;
			loaded = false;
			inserted.forEach(function (script) { script.remove(); });
			// Keep pendingOpen/pendingAsk: retry delivers the original ask.
			showFailure();
		}
		function append(script) {
			inserted.push(script);
			document.body.appendChild(script);
		}
		function finish() {
			if (failed) {
				return;
			}
			(payload.translations || []).forEach(function (js) {
				var data = document.createElement('script');
				data.text = js;
				append(data);
			});
			var app = document.createElement('script');
			app.src = payload.src;
			app.async = false;
			app.addEventListener('error', fail);
			append(app);
		}
		// Wait for every dependency, not merely the last one: any failed
		// dependency aborts this batch before the app can execute broken.
		var remaining = payload.deps.length;
		if (remaining === 0) {
			finish();
			return;
		}
		payload.deps.forEach(function (url) {
			var dep = document.createElement('script');
			dep.src = url;
			dep.async = false;
			dep.addEventListener('error', fail);
			dep.addEventListener('load', function () {
				remaining -= 1;
				if (remaining === 0) {
					finish();
				}
			});
				append(dep);
			});
		}
		// A workspace page has no bubble. Setting pendingOpen and waiting
		// for a click leaves the mount empty: nothing ever calls boot().
		// Boot before any script is inserted; ready then delivers open.
		if (payload.open) {
			pendingOpen = true;
			boot();
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
					// A page chip carries its label as the first question. A plain
					// opener (the bubble, a retry) has no payload and must not ask.
					open(trigger.getAttribute('data-ask-message') || '');
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

	/**
	 * The mount the app renders into. One markup for the dock and the
	 * workspace, so both carry the same routes and the same nonce.
	 *
	 * @param string $surface `helper` on every page, `workspace` on the advisor page.
	 */
	private function mount_markup( string $surface ): string {
		$locale = $this->locale();
		$page   = $this->page_context();
		return sprintf(
			'<div data-linker-app="genie" data-surface="%1$s" data-locale="%2$s" data-page-type="%3$s" data-product-id="%4$s" data-turn-url="%5$s" data-thread-url="%6$s" data-conversations-url="%7$s" data-vote-url="%8$s" data-rest-url="%9$s" data-rest-nonce="%10$s" data-disclosure="%11$s" data-account-url="%12$s" data-workspace-url="%13$s" data-prompts=\'%14$s\'></div>',
			esc_attr( $surface ),
			esc_attr( $locale ),
			esc_attr( $page['type'] ),
			esc_attr( (string) ( $page['product_id'] ?? 0 ) ),
			esc_attr( esc_url_raw( rest_url( Proxy::NAMESPACE . Proxy::ROUTE ) ) ),
			esc_attr( esc_url_raw( rest_url( Proxy::NAMESPACE . Proxy::THREAD_ROUTE ) ) ),
			esc_attr( esc_url_raw( rest_url( Proxy::NAMESPACE . Proxy::CONVERSATIONS_ROUTE ) ) ),
			esc_attr( esc_url_raw( rest_url( Proxy::NAMESPACE . Proxy::ROUTE ) ) ),
			esc_attr( esc_url_raw( rest_url() ) ),
			esc_attr( wp_create_nonce( 'wp_rest' ) ),
			esc_attr( $this->disclosure( $locale ) ),
			esc_attr( esc_url_raw( home_url( '/my-account/' ) ) ),
			esc_attr( esc_url_raw( $this->workspace_url() ) ),
			esc_attr( (string) wp_json_encode( $this->prompts( $page, $locale ) ) )
		);
	}

	/**
	 * Shop chip: opens Genie over the catalogue.
	 */
	public function shop_chip(): void {
		$this->print_group( 'category' );
	}

	/**
	 * Product page chips.
	 */
	public function product_chips(): void {
		$this->print_group( 'product' );
	}

	/**
	 * Solution draft chips.
	 */
	public function draft_chips(): void {
		$this->print_group( 'draft' );
	}

	/**
	 * Account chips.
	 */
	public function account_chips(): void {
		$this->print_group( 'account' );
	}

	/**
	 * The chip groups of one page type: the one list the Woo hooks and the
	 * LiveCanvas templates' shortcode both read.
	 *
	 * @return array<string, list<array{0: string, 1: string}>> Page type => chips (label, page type).
	 */
	private function chips_for(): array {
		return array(
			'category' => array(
				array( __( 'Ask Genie', 'linker-tools' ), 'category' ),
			),
			'product'  => array(
				array( __( 'What pairs with this model?', 'linker-tools' ), 'product' ),
				array( __( 'Compare with…', 'linker-tools' ), 'product' ),
				array( __( 'Documents', 'linker-tools' ), 'product' ),
			),
			'draft'    => array(
				array( __( 'Check my draft', 'linker-tools' ), 'draft' ),
				array( __( 'What happens next?', 'linker-tools' ), 'draft' ),
			),
			'account'  => array(
				array( __( 'Where is my Proforma?', 'linker-tools' ), 'account' ),
			),
		);
	}

	/**
	 * Echoes one page type's chips.
	 *
	 * @param string $type Page type.
	 */
	private function print_group( string $type ): void {
		foreach ( $this->chips_for()[ $type ] ?? array() as $chip ) {
			$this->chip( $chip[0], $chip[1] );
		}
	}

	/**
	 * The chips as a shortcode: the entries of the LiveCanvas-rendered page
	 * types, whose templates do not fire WooCommerce's hook surfaces. With no
	 * `page_type` attribute the current query decides.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function chips_shortcode( $atts = array() ): string {
		$parsed = is_array( $atts ) ? $atts : shortcode_parse_atts( (string) $atts );
		$atts   = shortcode_atts( array( 'page_type' => '' ), $parsed, 'linker_genie_chips' );
		$type   = '' !== $atts['page_type'] ? (string) $atts['page_type'] : $this->page_context()['type'];
		ob_start();
		$this->print_group( $type );
		return (string) ob_get_clean();
	}

		/**
		 * One chip that opens the dock with a starting question.
		 *
		 * The label is both the visible text and the first question the loader
		 * delivers (`data-ask-message`). A chip that only opens the dock leaves
		 * the visitor with an empty panel.
		 *
		 * @param string $label Chip label.
		 * @param string $type  Page type.
		 */
	public function chip( string $label, string $type ): void {
		printf(
			'<button type="button" class="linker-genie-chip" data-linker-genie-open data-ask-message="%1$s" data-page-type="%2$s">%3$s</button>',
			esc_attr( $label ),
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
	 * The advisor page in the request's language.
	 *
	 * The language layer (`pll_current_language`) is the authority for which
	 * language this request is in — the same one ComparePage asks. German
	 * gets that page's twin (`pll_get_post`); English, a missing twin, or
	 * no language layer stays on /linker-advisor/.
	 */
	private function workspace_url(): string {
		$fallback = home_url( '/linker-advisor/' );
		if ( ! function_exists( 'pll_current_language' ) || 'de' !== pll_current_language() ) {
			return $fallback;
		}
		$page = get_page_by_path( 'linker-advisor' );
		if ( ! $page instanceof \WP_Post || ! function_exists( 'pll_get_post' ) ) {
			return home_url( '/de/linker-berater/' );
		}
		$twin = (int) pll_get_post( (int) $page->ID, 'de' );
		$link = $twin > 0 ? get_permalink( $twin ) : false;
		return is_string( $link ) && '' !== $link ? $link : home_url( '/de/linker-berater/' );
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
