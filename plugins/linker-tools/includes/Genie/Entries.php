<?php
/**
 * Four page chip groups, the standing dock, and the AI disclosure sentence.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Genie;

use Linker\Commerce\Account\AuthTemplates;
use Linker\Commerce\Presentation\ContactChannels;
use Linker\Commerce\Presentation\PageUrls;

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
	 * @param string           $plugin_file Absolute path of the main plugin file.
	 * @param PageContext|null $pages       The page of the request; a default one is built when omitted.
	 * @param Preview|null     $preview     The preview card, whose questions the dock offers on its pages.
	 */
	public function __construct(
		private readonly string $plugin_file,
		?PageContext $pages = null,
		?Preview $preview = null
	) {
		$this->pages   = $pages ?? new PageContext();
		$this->preview = $preview ?? new Preview( $this->pages );
	}

	/**
	 * The page of the request (ticket #234).
	 *
	 * @var PageContext
	 */
	private readonly PageContext $pages;

	/**
	 * The preview card (ticket #249).
	 *
	 * @var Preview
	 */
	private readonly Preview $preview;

	/**
	 * Hooks the chips and the dock; runs during plugin registration.
	 */
	public function register(): void {
		add_action( 'wp_head', array( $this, 'workspace_scripts' ), 2 );
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
		add_action( 'wp_enqueue_scripts', array( $this, 'marketing_assets' ) );
		add_action( 'rest_api_init', array( new EntryContext(), 'register' ) );
	}

	/** Start the visible workspace bundle and its native WordPress dependencies with the document. */
	public function workspace_scripts(): void {
		$post = get_queried_object();
		if ( ! $post instanceof \WP_Post || ! PageIndexing::is_workspace_post( $post ) ) {
			return;
		}
		$src = EntryAssets::url( self::HANDLE );
		if ( '' === $src ) {
			return;
		}
		printf( '<link rel="preload" as="script" href="%s">', esc_url( $src ) );
		$scripts = wp_scripts();
		$entry   = $scripts->query( self::HANDLE );
		if ( $entry && $entry->deps ) {
			$scripts->do_items( $entry->deps );
		}
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
		EntryAssets::enqueue_loader( 'genie' );
	}

	/** Loads the binder only on LC pages carrying the affected editor markup. */
	public function marketing_assets(): void {
		if ( is_admin() ) {
			return;
		}
		$post = get_post();
		if ( $post instanceof \WP_Post && ( str_contains( $post->post_content, 'lk-dialog-prompt' ) || str_contains( $post->post_content, 'installer-mobile-query' ) || str_contains( $post->post_content, 'lki-hero-query' ) ) && ! is_front_page() ) {
			wp_enqueue_script( 'linker-tools-marketing' );
		}
	}

	/**
	 * The Ask Genie chip of the products search box, mountable in the
	 * LiveCanvas templates that render the products page (ticket #68: the markup
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
	 * The full-page workspace on /genie/.
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
		\Linker\Tools\Cache\DynamicHtml::forbid( 'genie workspace' );
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
	 * The search box's script: on the pages that carry the products search
	 * box (all products and the product categories) and on pages that mount the chip
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
	 * Whether the page carries the products search box or mounts the chip.
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
		$mount = 'linker-genie-mount';
		echo '<div class="linker-genie">';
		$page = $this->page_context();
		if ( null === $this->preview->card_page( $page ) ) {
			echo '<div class="linker-genie-peek">';
			foreach ( array_slice( $this->prompts( $page ), 0, 2 ) as $prompt ) {
				printf( '<button type="button" class="linker-genie-peek__prompt" data-linker-genie-open data-ask-message="%1$s" aria-controls="%2$s">%3$s</button>', esc_attr( $prompt ), esc_attr( $mount ), esc_html( $prompt ) );
			}
			echo '</div>';
		}
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
		$this->print_loader( false );
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
		$payload = EntryAssets::config( 'genie' ) + array(
			'error'   => __( 'Genie could not load.', 'linker-tools' ),
			'retry'   => __( 'Try again', 'linker-tools' ),
			'title'   => __( "Genie – Linker's AI assistant", 'linker-tools' ),
			'waiting' => __( 'Genie is thinking…', 'linker-tools' ),
			'close'   => __( 'Close', 'linker-tools' ),
			'open'    => $open,
		);
		if ( '' === $payload['src'] ) {
			return;
		}
		wp_print_inline_script_tag(
			(string) wp_json_encode( $payload, JSON_HEX_TAG | JSON_UNESCAPED_SLASHES ),
			array(
				'type'                     => 'application/json',
				'data-linker-genie-loader' => true,
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
		$signed_in = is_user_logged_in();
		$locale    = $this->locale();
		$page      = $this->page_context();
		return sprintf(
			'<div data-linker-app="genie" data-surface="%1$s" data-locale="%2$s" data-page-type="%3$s" data-product-id="%4$s" data-turn-url="%5$s" data-thread-url="%6$s" data-conversations-url="%7$s" data-vote-url="%8$s" data-rest-url="%9$s" data-rest-nonce="%10$s" data-disclosure="%11$s" data-account-url="%12$s" data-workspace-url="%13$s" data-prompts=\'%14$s\' data-page=\'%15$s\' data-signed-in="%16$s" data-retention-days="%17$s" data-contact-url="%18$s" data-inquiry-url="%19$s" data-request-page-url="%20$s" data-configurator-en-url="%21$s" data-configurator-de-url="%22$s" data-register-url="%23$s" %24$s data-whatsapp-url="%25$s"></div>',
			esc_attr( $surface ),
			esc_attr( $locale ),
			esc_attr( $page['type'] ),
			esc_attr( (string) ( $page['product_id'] ?? 0 ) ),
			esc_attr( esc_url_raw( rest_url( Proxy::NAMESPACE . Proxy::ROUTE ) ) ),
			esc_attr( esc_url_raw( rest_url( Proxy::NAMESPACE . Proxy::THREAD_ROUTE ) ) ),
			esc_attr( esc_url_raw( rest_url( Proxy::NAMESPACE . Proxy::CONVERSATIONS_ROUTE ) ) ),
			esc_attr( esc_url_raw( rest_url( Proxy::NAMESPACE . Proxy::ROUTE ) ) ),
			esc_attr( esc_url_raw( rest_url() ) ),
			$signed_in ? esc_attr( wp_create_nonce( 'wp_rest' ) ) : '',
			esc_attr( $this->disclosure( $locale ) ),
			esc_attr( esc_url_raw( self::page_url_for( 'my-account', $locale ) ) ),
			esc_attr( esc_url_raw( $this->workspace_url() ) ),
			esc_attr( (string) wp_json_encode( $this->prompts( $page ) ) ),
			// The whole page context, sent back with every turn (#234).
			esc_attr( (string) wp_json_encode( $page ) ),
			$signed_in ? '1' : '0',
			esc_attr( (string) Retention::RETENTION_DAYS ),
			// The contact card's route, "Let Linker contact me" (#243).
			esc_attr( esc_url_raw( rest_url( Proxy::NAMESPACE . ContactRequest::ROUTE ) ) ),
			// The inquiry confirmation card's route (#250).
			esc_attr( esc_url_raw( rest_url( Proxy::NAMESPACE . InquiryRequest::ROUTE ) ) ),
			esc_attr( esc_url_raw( (string) apply_filters( 'linker_genie_inquiry_page', '', $locale ) ) ), // phpcs:ignore WooCommerce.Commenting.CommentHooks.MissingHookComment, WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- Existing native inquiry-page seam owned by InquiryRequest.
			esc_attr( esc_url_raw( class_exists( PageUrls::class ) ? PageUrls::translated( 'solution-configurator', 'en' ) : '' ) ),
			esc_attr( esc_url_raw( class_exists( PageUrls::class ) ? PageUrls::translated( 'solution-configurator', 'de' ) : '' ) ),
			esc_attr( esc_url_raw( ! $signed_in && class_exists( AuthTemplates::class ) && 'yes' === get_option( 'woocommerce_enable_myaccount_registration' ) ? AuthTemplates::register_url() : '' ) ),
			$signed_in ? 'data-genie-nonce-url="' . esc_url( admin_url( 'admin-ajax.php?action=rest-nonce' ) ) . '"' : '',
			esc_attr( esc_url_raw( class_exists( ContactChannels::class ) ? ContactChannels::url() : '' ) )
		);
	}

	/**
	 * Shop chip: opens Genie over the products page.
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
	 * A real question carries its own `ask`. The products-page opener does not:
	 * "Ask Genie" / "Genie fragen" only opens the dock
	 * (docs/specs/13-genie.md: the shop opener sends no message of its own).
	 * Omitting `ask` is the absence, not an empty string the loader could send.
	 *
	 * @return array<string, list<array{0: string, 1: string, ask?: string}>> Page type => chips.
	 */
	private function chips_for(): array {
		return array(
			'category' => array(
				array( __( 'Ask Genie', 'linker-tools' ), 'category' ),
			),
			'faq'      => array(
				array(
					__( 'Datasheet & manual by model', 'linker-tools' ),
					'faq',
					'ask' => __( 'Find the datasheet and installation manual for an inverter or battery model', 'linker-tools' ),
				),
				array(
					__( 'VDE-AR-N 4105 / 4110 certificates', 'linker-tools' ),
					'faq',
					'ask' => __( 'Which models have VDE-AR-N 4105 or VDE-AR-N 4110 grid certificates?', 'linker-tools' ),
				),
				array(
					__( 'Inverter & HV battery pairing', 'linker-tools' ),
					'faq',
					'ask' => __( 'Which high-voltage batteries are compatible with my hybrid inverter and capacity ratio?', 'linker-tools' ),
				),
			),
			'product'  => array(
				array(
					__( 'What pairs with this model?', 'linker-tools' ),
					'product',
					'ask' => __( 'What pairs with this model?', 'linker-tools' ),
				),
				array(
					__( 'Compare with…', 'linker-tools' ),
					'product',
					'ask' => __( 'Compare with…', 'linker-tools' ),
				),
				array(
					__( 'Documents', 'linker-tools' ),
					'product',
					'ask' => __( 'Documents', 'linker-tools' ),
				),
			),
			'draft'    => array(
				array(
					__( 'Check my draft', 'linker-tools' ),
					'draft',
					'ask' => __( 'Check my draft', 'linker-tools' ),
				),
				array(
					__( 'What happens next?', 'linker-tools' ),
					'draft',
					'ask' => __( 'What happens next?', 'linker-tools' ),
				),
			),
			'account'  => array(
				array(
					__( 'Where is my quotation?', 'linker-tools' ),
					'account',
					'ask' => __( 'Where is my quotation?', 'linker-tools' ),
				),
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
			$this->chip( $chip[0], $chip[1], $chip['ask'] ?? '' );
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
	 * One chip that opens the dock, and asks only when it carries a question.
	 *
	 * The label is the visible text. The first question is the explicit `$ask`
	 * the loader delivers (`data-ask-message`). An opener such as the products page
	 * "Ask Genie" button passes an empty ask and prints no payload, so a click
	 * opens the dock without sending the label (docs/specs/13-genie.md).
	 *
	 * @param string $label Chip label.
	 * @param string $type  Page type.
	 * @param string $ask   First question. Empty opens the dock and sends nothing.
	 */
	public function chip( string $label, string $type, string $ask = '' ): void {
		if ( '' === $ask ) {
			printf(
				'<button type="button" class="linker-genie-chip" data-linker-genie-open data-page-type="%1$s">%2$s</button>',
				esc_attr( $type ),
				esc_html( $label )
			);
			return;
		}
		printf(
			'<button type="button" class="linker-genie-chip" data-linker-genie-open data-ask-message="%1$s" data-page-type="%2$s">%3$s</button>',
			esc_attr( $ask ),
			esc_attr( $type ),
			esc_html( $label )
		);
	}

	/**
	 * The opening prompts of one page, two or three of them, naming the
	 * page where it has a name (docs/specs/13-genie.md, 目标 3: "打开即点名
	 * 当前产品或分类", "每类页面至少两条本页建议").
	 *
	 * On the pages that carry the preview card — home, product, product
	 * category, solution — the dock offers the card's own questions
	 * (Preview::asks). Copy review: docs/acceptance/2026-10-18/249/ for
	 * those, docs/acceptance/2026-10-18/234/copy-review.md for the rest;
	 * German is written on its own in languages/linker-tools-de_DE_formal.po.
	 *
	 * @param array{type: string, title?: string, post_id?: int, category_id?: int} $page The page context.
	 * @return list<string>
	 */
	public function prompts( array $page ): array {
		$card = $this->preview->asks( $page );
		if ( null !== $card ) {
			return $card;
		}
		switch ( $page['type'] ) {
			case 'draft':
				return array(
					__( 'Check my draft', 'linker-tools' ),
					__( 'What happens next?', 'linker-tools' ),
				);
			case 'account':
				return array(
					__( 'Where is my quotation?', 'linker-tools' ),
					__( 'What happens next?', 'linker-tools' ),
				);
			case 'category':
				// All products (/products/), which has no category of its own.
				return array(
					__( 'Which model fits my project?', 'linker-tools' ),
					__( 'Compare SAJ and GoodWe hybrid inverters', 'linker-tools' ),
				);
			case 'blog':
				return isset( $page['post_id'] )
					? array(
						__( 'Summarize this post', 'linker-tools' ),
						__( 'Which products does this post apply to?', 'linker-tools' ),
					)
					: array(
						__( 'Which of these posts cover hybrid inverters?', 'linker-tools' ),
						__( 'Summarize this page', 'linker-tools' ),
					);
			case 'faq':
				return array_column( $this->chips_for()['faq'], 'ask' );
			case 'solution':
				// The hub, About and the audience pages; the solutions themselves
				// carry the card's questions above.
				return array(
					__( 'Summarize this page', 'linker-tools' ),
					__( 'Which products fit my project?', 'linker-tools' ),
				);
			default:
				// Contact, the legal pages, the forms and the tools: a summary
				// would reword legal text, so the dock offers the range.
				return array(
					__( 'Which model fits my project?', 'linker-tools' ),
					__( 'Which batteries work with my inverter?', 'linker-tools' ),
				);
		}
	}

	/**
	 * The page of the current request (PageContext, ticket #234).
	 *
	 * @return array{type: string, url: string, title: string, product_id?: int, post_id?: int, category_id?: int}
	 */
	public function page_context(): array {
		return $this->pages->current();
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
	 * no language layer stays on /genie/.
	 */
	private function workspace_url(): string {
		$lang = function_exists( 'pll_current_language' ) && 'de' === pll_current_language() ? 'de' : 'en';
		return self::workspace_url_for( $lang );
	}

	/**
	 * Genie's full page in one language: the English page at /genie/, its
	 * Polylang twin for German (/de/genie/ when the twin is missing).
	 *
	 * @param string $lang `en` or `de`.
	 */
	public static function workspace_url_for( string $lang ): string {
		return self::page_url_for( 'genie', $lang );
	}

	/**
	 * One of the site's own pages in a language: its Polylang twin when it
	 * has one, the language's own path otherwise. A plugin that runs without
	 * the language layer still answers its interface language's address.
	 *
	 * @param string $slug Page path.
	 * @param string $lang `en` or `de`.
	 */
	public static function page_url_for( string $slug, string $lang ): string {
		if ( function_exists( 'get_page_by_path' ) && function_exists( 'pll_get_post' ) ) {
			$page = get_page_by_path( $slug );
			if ( $page instanceof \WP_Post ) {
				$id   = 'en' === $lang ? (int) $page->ID : (int) pll_get_post( (int) $page->ID, $lang );
				$link = $id > 0 ? get_permalink( $id ) : false;
				if ( is_string( $link ) && '' !== $link ) {
					return $link;
				}
			}
		}
		$path = ( 'en' === $lang ? '/' : '/' . $lang . '/' ) . $slug . '/';
		return (string) home_url( $path );
	}
}
