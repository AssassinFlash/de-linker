<?php
/**
 * Native module registration and a semantic mount for the isolated planner.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Planner;

use Linker\Commerce\Presentation\ContactChannels;
use Linker\Commerce\Presentation\PageUrls;
use Linker\Commerce\Presentation\WindPressPageStyles;

/** No layout, inline script, style or browser-selected identity is emitted. */
final class Application {

	public const HANDLE = 'linker-planner';

	private const LANDING_ROUTES = '(?:solution-configurator|de/loesungskonfigurator)/?';
	private const PRIVATE_COOKIE = '(?:wp_woocommerce_session_|woocommerce_|wordpress_logged_in_|linker_planner_)';

	/**
	 * Initial workspace shell and session-boundary messages kept inline so the
	 * page still reads in its own language when the full static catalog cannot
	 * be requested at all.
	 *
	 * @var list<string>
	 */
	private const SHELL_MESSAGES = array(
		'A project can start with the information already available. Roof drawing is optional.',
		'About this tool',
		'Account workspace',
		'All design views use the same project geometry. Source records retain the declared accuracy and permissions; a displayed model provides no engineering approval.',
		'Annual consumption as recorded in the saved solution.',
		'Back to projects',
		'Backup supply requested; accessories may be considered.',
		'Check session',
		'Continue without these inputs',
		'Guest projects are available in this browser session. Signing in links them to the account.',
		'Guest workspace',
		'Interface and project data: React, TanStack Query and Ajv. 3D views: Three.js and React Three Fiber. Map display: MapLibre GL JS.',
		'Linker brings your inputs into an editable project for solar and storage planning.',
		'You can reopen saved projects and restore available drafts.',
		'Loading projects…',
		'More projects',
		'New project',
		'OpenFreeMap privacy policy',
		'Opening project…',
		'Opening your workspace…',
		'Project workspace',
		'Projects',
		'Projects from the guest session are still being linked to your account.',
		'Refresh projects',
		'Reload workspace',
		'Revision %d',
		'Saved projects',
		'Saved projects are linked to your account.',
		'Saved projects could not be loaded.',
		'Site information, roof layout and system planning belong to the same project.',
		'Software and data credits',
		'Solution Configurator',
		'Start a new project from a saved solution',
		'Street map: OpenFreeMap. © OpenMapTiles; © OpenStreetMap contributors.',
		'The saved inputs could not be loaded in this session.',
		'The workspace could not be displayed. Saved projects are unchanged.',
		'This project could not be opened in the current session.',
		'Try again',
		'Unconfirmed project creations and CSV imports from earlier sessions could not be checked. Any recovery data already stored in this browser remains unchanged.',
		'Your projects',
		'Your workspace could not be opened. Your saved projects are unchanged.',
		'by Linker',
	);

	/**
	 * One document has one project/session coordinator.
	 *
	 * @var bool
	 */
	private bool $mounted = false;

	/**
	 * Versioned URL of the full script-module translation catalog when split.
	 *
	 * @var string|null
	 */
	private ?string $catalog_url = null;

	/**
	 * Entry module followed by its static Vite imports.
	 *
	 * @var list<string>
	 */
	private array $module_preloads = array();

	/**
	 * Path WordPress uses to identify the entry's native translation catalog.
	 *
	 * @var string
	 */
	private string $entry_path = '';

	/**
	 * Public, reviewed build metadata; never a project-supplied executable URL.
	 *
	 * @var string|null
	 */
	private ?string $scene_module_url = null;

	/**
	 * Reviewed lazy map module, never a provider or user-selected script.
	 *
	 * @var string|null
	 */
	private ?string $map_module_url = null;

	/**
	 * Locate the plugin's reviewed build.
	 *
	 * @param string $plugin_file Main plugin file.
	 */
	public function __construct( private readonly string $plugin_file ) {}

	/** Register only; the module loads where its shortcode is rendered. */
	public function register(): void {
		add_action( 'init', array( $this, 'assets' ) );
		add_action( 'wp_head', array( $this, 'preload' ), 1 );
		add_action( 'template_redirect', array( $this, 'inquiry_entry' ) );
		add_shortcode( 'linker_planner', array( $this, 'mount' ) );
		add_filter( 'load_script_translations', array( $this, 'filter_translations' ), 10, 4 );
		add_action( 'wp_footer', array( $this, 'print_translation_loader' ), 22 );
		add_filter( 'mod_rewrite_rules', array( $this, 'cache_rules' ) );
		( new Indexing() )->register();
		( new WindPress( $this->plugin_file ) )->register();
	}

	/** Public configurator URL for the current site language. */
	private function configurator_url(): string {
		return class_exists( PageUrls::class ) ? PageUrls::translated( 'solution-configurator' ) : '';
	}

	/** Open the native translated Woo inquiry from the public configurator showcase. */
	public function inquiry_entry(): void {
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended, WordPress.Security.ValidatedSanitizedInput -- Exact public view discriminator, never written or rendered.
		if ( 'inquiry' !== ( $_GET['view'] ?? null ) || isset( $_GET['project'] ) || ! is_page() || ! function_exists( 'wc_get_checkout_url' ) ) {
			return;
		}
		if ( get_permalink( get_queried_object_id() ) === $this->configurator_url() ) {
			wp_safe_redirect( wc_get_checkout_url() );
			exit;
		}
	}

	/**
	 * Keep only the initial workspace-shell translations inline and record the
	 * versioned static catalog URL for on-demand loading.
	 *
	 * @param string|false $translations JSON translation catalog.
	 * @param string|false $file         Catalog file path on disk.
	 * @param string       $handle       Script or script-module handle.
	 * @param string       $domain       Text domain.
	 * @return string|false
	 */
	public function filter_translations( string|false $translations, string|false $file, string $handle, string $domain ): string|false {
		if ( self::HANDLE !== $handle || 'linker-tools' !== $domain || ! is_string( $translations ) || '' === $translations ) {
			return $translations;
		}
		if ( ! is_string( $file ) || '' === $file || ! is_readable( $file ) ) {
			return $translations;
		}
		$name = basename( $file );
		if ( 1 !== preg_match( '~\Alinker-tools-[a-zA-Z0-9_]+-[a-f0-9]{32}\.json\z~', $name ) ) {
			return $translations;
		}
		$decoded = json_decode( $translations, true );
		if ( ! is_array( $decoded ) || ! isset( $decoded['locale_data'] ) || ! is_array( $decoded['locale_data'] ) ) {
			return $translations;
		}
		$messages = $decoded['locale_data']['messages'] ?? $decoded['locale_data']['linker-tools'] ?? null;
		if ( ! is_array( $messages ) ) {
			return $translations;
		}
		$subset = array(
			'' => is_array( $messages[''] ?? null ) ? $messages[''] : array( 'domain' => 'messages' ),
		);
		foreach ( self::SHELL_MESSAGES as $msgid ) {
			if ( isset( $messages[ $msgid ] ) && is_array( $messages[ $msgid ] ) ) {
				$subset[ $msgid ] = $messages[ $msgid ];
			}
		}
		if ( count( $subset ) >= count( $messages ) ) {
			return $translations;
		}
		$this->catalog_url    ??= $this->catalog_file_url( $file );
		$decoded['locale_data'] = array( 'messages' => $subset );
		$encoded                = wp_json_encode( $decoded, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES );
		return is_string( $encoded ) ? $encoded : $translations;
	}

	/**
	 * The catalog filename identifies the script, so its URL also includes the translation revision.
	 *
	 * @param string $file Readable generated catalog.
	 */
	private function catalog_file_url( string $file ): ?string {
		$revision = hash_file( 'sha256', $file );
		return is_string( $revision ) ? plugin_dir_url( $this->plugin_file ) . 'languages/' . basename( $file ) . '?ver=' . substr( $revision, 0, 12 ) : null;
	}

	/** Discover the entry's static imports and start the localized fetch in the document head. */
	public function preload(): void {
		if ( ! $this->module_preloads ) {
			return;
		}
		$post    = get_queried_object();
		$content = ( $post instanceof \WP_Post ? $post->post_content : '' ) . "\n" . ( $GLOBALS['lc_main_html'] ?? '' );
		if ( ! $this->mounted && ! $this->includes_planner( $content ) ) {
			return;
		}
		foreach ( $this->module_preloads as $url ) {
			echo '<link rel="modulepreload" href="' . esc_url( $url ) . '" crossorigin="anonymous">' . "\n";
		}
		$file = plugin_dir_path( $this->plugin_file ) . 'languages/linker-tools-' . determine_locale() . '-' . md5( $this->entry_path ) . '.json';
		if ( ! is_readable( $file ) ) {
			return;
		}
		$this->catalog_url = $this->catalog_file_url( $file );
		if ( ! $this->catalog_url ) {
			return;
		}
		echo '<link rel="preload" as="fetch" href="' . esc_url( $this->catalog_url ) . '" crossorigin="anonymous">' . "\n";
		wp_print_inline_script_tag(
			'window.linkerPlannerCatalogRequest = fetch(' . wp_json_encode( $this->catalog_url, JSON_HEX_TAG | JSON_UNESCAPED_SLASHES ) . ', { credentials: "same-origin" }).then(r => r.ok ? r.json() : null).catch(() => null);',
			array( 'id' => 'linker-planner-catalog-request' )
		);
	}

	/**
	 * The retired inline homepage shortcode deliberately renders no planner.
	 *
	 * @param string $content Queried post and LiveCanvas template.
	 */
	private function includes_planner( string $content ): bool {
		if ( ! str_contains( $content, '[linker_' ) ) {
			return false;
		}
		preg_match_all( '/' . get_shortcode_regex( array( 'linker_planner', 'linker_configurator' ) ) . '/s', $content, $matches, PREG_SET_ORDER );
		foreach ( $matches as $match ) {
			if ( '[' === $match[1] && ']' === $match[6] ) {
				continue;
			}
			$atts = shortcode_parse_atts( $match[3] );
			if ( 'linker_configurator' === $match[2] || 'home' !== ( $atts['mode'] ?? '' ) ) {
				return true;
			}
		}
		return false;
	}

	/** After WordPress installs the shell translations, apply the catalog requested by the head. */
	public function print_translation_loader(): void {
		if ( ! is_string( $this->catalog_url ) || '' === $this->catalog_url ) {
			return;
		}
		$url = wp_json_encode( $this->catalog_url, JSON_HEX_TAG | JSON_UNESCAPED_SLASHES );
		if ( ! is_string( $url ) ) {
			return;
		}
		$loader = sprintf(
			'window.linkerToolsCatalog = (window.linkerPlannerCatalogRequest || fetch(%s, { credentials: "same-origin" }).then(r => r.ok ? r.json() : null).catch(() => null)).then(data => { const messages = data && data.locale_data && (data.locale_data["linker-tools"] || data.locale_data.messages); if (messages && window.wp && window.wp.i18n) { messages[""] = Object.assign({}, messages[""], {domain: "linker-tools"}); window.wp.i18n.setLocaleData(messages, "linker-tools"); } });',
			$url
		);
		wp_print_inline_script_tag( $loader, array( 'id' => 'linker-planner-translation-loader' ) );
	}

	/** Isolated React module, using the installed native translation runtime. */
	public function assets(): void {
		$path = plugin_dir_path( $this->plugin_file ) . 'build/planner/vite-manifest.json';
		if ( ! is_readable( $path ) ) {
			return;
		}
		$manifest = json_decode( (string) file_get_contents( $path ), true ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- bounded local build metadata.
		$file     = is_array( $manifest ) ? ( $manifest['src/main.tsx']['file'] ?? null ) : null;
		if ( ! is_string( $file ) || 1 !== preg_match( '~\Aassets/[a-zA-Z0-9_.-]+\.js\z~', $file ) ) {
			return;
		}
		$asset_path = plugin_dir_path( $this->plugin_file ) . 'build/planner/' . $file;
		if ( ! is_readable( $asset_path ) ) {
			return;
		}
		$version = hash_file( 'sha256', $asset_path );
		$scene   = $manifest['src/components/design/SceneViewport.tsx']['file'] ?? null;
		if ( is_string( $scene ) && 1 === preg_match( '~\Aassets/SceneViewport-[a-zA-Z0-9_-]+\.js\z~', $scene ) ) {
			$this->scene_module_url = plugin_dir_url( $this->plugin_file ) . 'build/planner/' . $scene;
		}
		$map = $manifest['src/components/design/MapViewport.tsx']['file'] ?? null;
		if ( is_string( $map ) && 1 === preg_match( '~\Aassets/MapViewport-[a-zA-Z0-9_-]+\.js\z~', $map ) ) {
			$this->map_module_url = plugin_dir_url( $this->plugin_file ) . 'build/planner/' . $map;
		}
		$base                  = plugin_dir_url( $this->plugin_file ) . 'build/planner/';
		$this->entry_path      = 'build/planner/' . $file;
		$this->module_preloads = array( $base . $file . ( is_string( $version ) ? '?ver=' . $version : '' ) );
		foreach ( $manifest['src/main.tsx']['imports'] ?? array() as $import ) {
			$chunk = $manifest[ $import ]['file'] ?? null;
			if ( is_string( $chunk ) && preg_match( '~\Aassets/[a-zA-Z0-9_.-]+\.js\z~', $chunk ) ) {
				$this->module_preloads[] = $base . $chunk;
			}
		}
		wp_register_script_module( self::HANDLE, $base . $file, array(), is_string( $version ) ? $version : null );
		wp_set_script_module_translations( self::HANDLE, 'linker-tools', plugin_dir_path( $this->plugin_file ) . 'languages' );
	}

	/**
	 * LiteSpeed's public cache can answer before WordPress reads the request.
	 *
	 * @param string $rules WordPress's native web-server rules.
	 */
	public function cache_rules( string $rules ): string {
		$conditions = 'RewriteCond %{QUERY_STRING} !^$ [OR]' . "\n"
			. 'RewriteCond %{HTTP_COOKIE} (^|;[[:space:]]*)' . self::PRIVATE_COOKIE . "\n"
			. 'RewriteRule ^' . self::LANDING_ROUTES . '$ - [E=Cache-Control:no-cache]';
		return str_replace( 'RewriteEngine On', "RewriteEngine On\n" . $conditions, $rules );
	}

	/**
	 * Only a clean, anonymous landing URL can carry a shared copy of the workspace shell.
	 *
	 * @param bool $signed_in Whether WordPress authenticated the visitor.
	 */
	private function public_landing( bool $signed_in ): bool {
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended, WordPress.Security.ValidatedSanitizedInput -- Compare the raw URL and names only. No request data is echoed.
		if ( $signed_in || ! empty( $_GET ) || 1 !== preg_match( '~^/' . self::LANDING_ROUTES . '$~D', $_SERVER['REQUEST_URI'] ?? '' ) ) {
			return false;
		}
		return ! $this->has_workspace_session();
	}

	/** Woo session and planner transition cookies must be checked by the server, including HttpOnly cookies. */
	private function has_workspace_session(): bool {
		foreach ( array_keys( $_COOKIE ) as $name ) {
			if ( preg_match( '~^' . self::PRIVATE_COOKIE . '~', (string) $name ) ) {
				return true;
			}
		}
		return false;
	}

	/**
	 * WordPress owns routes, language and country labels.
	 *
	 * @param array<string,string>|string $attributes Native shortcode attributes.
	 */
	public function mount( array|string $attributes = array() ): string {
		if ( is_admin() || $this->mounted || ( is_array( $attributes ) && 'home' === ( $attributes['mode'] ?? '' ) ) ) {
			return '';
		}
		$signed_in = is_user_logged_in();
		if ( ! $this->public_landing( $signed_in ) ) {
			\Linker\Tools\Cache\DynamicHtml::forbid( 'solution configurator' );
		}
		$this->mounted = true;
		wp_enqueue_script( 'wp-i18n' );
		wp_enqueue_script_module( self::HANDLE );
		$countries    = function_exists( 'WC' ) ? WC()->countries->get_countries() : array();
		$raw_maps_key = defined( 'LINKER_GOOGLE_MAPS_API_KEY' ) ? constant( 'LINKER_GOOGLE_MAPS_API_KEY' ) : get_option( 'linker_google_maps_api_key', '' );
		$maps_key     = is_string( $raw_maps_key ) ? trim( $raw_maps_key ) : '';
		if ( 1 !== preg_match( '/\A[A-Za-z0-9_-]{20,80}\z/', $maps_key ) ) {
			$maps_key = '';
		}
		$config = wp_json_encode(
			array(
				'base_url'              => rest_url( Gateway::NAMESPACE . Gateway::ROUTE ),
				// `admin-ajax.php?action=rest-nonce` only answers a logged-in
				// cookie: WordPress registers it under `wp_ajax_` alone, so a
				// guest is answered `400` with the body `0` (measured
				// 2026-11-15 on production: 700ms, body `0`, and the client
				// has always treated it as the normal guest branch). Sending
				// the URL only to a signed-in visitor removes a request that
				// could never succeed from every guest's first paint.
				'nonce_url'             => $signed_in
					? add_query_arg( 'action', 'rest-nonce', admin_url( 'admin-ajax.php' ) )
					: null,
				'locale'                => determine_locale(),
				'countries'             => (object) $countries,
				'scene_module_url'      => $this->scene_module_url,
				'map_module_url'        => $this->map_module_url,
				'map_style_url'         => class_exists( WindPressPageStyles::class ) ? WindPressPageStyles::map_style_url() : null,
				'has_workspace_session' => $this->has_workspace_session(),
				'inquiry_url'           => function_exists( 'wc_get_checkout_url' ) ? wc_get_checkout_url() : null,
				'contact_mailbox'       => class_exists( ContactChannels::class ) ? ContactChannels::DIRECT_EMAIL : null,
				'whatsapp_url'          => class_exists( ContactChannels::class ) ? ContactChannels::url() : null,
				'google_maps_api_key'   => '' !== $maps_key ? $maps_key : null,
			)
		);
		return sprintf(
			'<section data-linker-planner data-planner-config="%s"><div class="sc-configurator sc-intake sc-loading"><header class="sc-project-heading"><div><h1>%s</h1><p>%s</p></div></header>%s</div></section>',
			esc_attr( is_string( $config ) ? $config : '{}' ),
			esc_html__( 'Solution Configurator', 'linker-tools' ),
			esc_html__( 'A project can start with the information already available. Roof drawing is optional.', 'linker-tools' ),
			$signed_in || $this->has_workspace_session() ? '<p role="status">' . esc_html__( 'Opening your workspace…', 'linker-tools' ) . '</p>' : ''
		);
	}
}
