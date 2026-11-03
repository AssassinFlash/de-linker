<?php
/**
 * Native module registration and a semantic mount for the isolated planner.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Planner;

/** No layout, inline script, style or browser-selected identity is emitted. */
final class Application {

	public const HANDLE = 'linker-planner';

	/**
	 * Initial workspace shell and session-boundary messages kept inline so the
	 * entry renders translated immediately while the full static catalog loads.
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
		'Linker provides the project workflow and editing tools. Your inputs and design stay together in the same project, with controls for saving changes and restoring available drafts.',
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
		add_shortcode( 'linker_planner', array( $this, 'mount' ) );
		add_filter( 'load_script_translations', array( $this, 'filter_translations' ), 10, 4 );
		add_filter( 'wp_inline_script_tag', array( $this, 'inline_translation_loader' ), 10, 3 );
		( new Indexing() )->register();
		( new WindPress( $this->plugin_file ) )->register();
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
		$hash = hash_file( 'sha256', $file );
		if ( is_string( $hash ) ) {
			$this->catalog_url = plugin_dir_url( $this->plugin_file ) . 'languages/' . $name . '?ver=' . substr( $hash, 0, 12 );
		}
		$decoded['locale_data'] = array( 'messages' => $subset );
		$encoded                = wp_json_encode( $decoded, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES );
		return is_string( $encoded ) ? $encoded : $translations;
	}

	/**
	 * Append the on-demand catalog loader to the planner's inline translation tag.
	 *
	 * @param string               $tag        Rendered `<script>` tag.
	 * @param string               $javascript Inline script body.
	 * @param array<string, mixed> $attributes Script element attributes.
	 */
	public function inline_translation_loader( string $tag, string $javascript, array $attributes ): string {
		unset( $javascript );
		if ( ( $attributes['id'] ?? null ) !== 'wp-script-module-translation-data-' . self::HANDLE ) {
			return $tag;
		}
		if ( ! is_string( $this->catalog_url ) || '' === $this->catalog_url || ! str_ends_with( rtrim( $tag ), '</script>' ) ) {
			return $tag;
		}
		$url = wp_json_encode( $this->catalog_url, JSON_HEX_TAG | JSON_UNESCAPED_SLASHES );
		if ( ! is_string( $url ) ) {
			return $tag;
		}
		$loader = sprintf(
			'( ( domain, url ) => { if ( typeof window.fetch !== "function" ) return; const nativeFetch = window.fetch.bind( window ); let pending = nativeFetch( url, { credentials: "same-origin" } ).then( ( r ) => ( r.ok ? r.json() : null ) ).then( ( data ) => { const localeData = data && data.locale_data && ( data.locale_data[ domain ] || data.locale_data.messages ); if ( localeData && window.wp && window.wp.i18n ) { localeData[ "" ] = Object.assign( {}, localeData[ "" ], { domain } ); window.wp.i18n.setLocaleData( localeData, domain ); } } ).catch( () => {} ).finally( () => { pending = null; } ); window.fetch = ( input, init ) => ( pending ? pending.then( () => nativeFetch( input, init ) ) : nativeFetch( input, init ) ); } )( "linker-tools", %s );',
			$url
		);
		$pos    = strrpos( $tag, '</script>' );
		if ( false === $pos ) {
			return $tag;
		}
		return substr( $tag, 0, $pos ) . "\n" . $loader . "\n</script>";
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
		wp_register_script_module( self::HANDLE, plugin_dir_url( $this->plugin_file ) . 'build/planner/' . $file, array(), is_string( $version ) ? $version : null );
		wp_set_script_module_translations( self::HANDLE, 'linker-tools', plugin_dir_path( $this->plugin_file ) . 'languages' );
	}

	/** WordPress owns routes/language/country labels; no private credential. */
	public function mount(): string {
		if ( is_admin() || $this->mounted ) {
			return '';
		}
		\Linker\Tools\Cache\DynamicHtml::forbid( 'solution configurator' );
		$this->mounted = true;
		wp_enqueue_script( 'wp-i18n' );
		wp_enqueue_script_module( self::HANDLE );
		$countries = function_exists( 'WC' ) ? WC()->countries->get_countries() : array();
		$config    = wp_json_encode(
			array(
				'base_url'         => rest_url( Gateway::NAMESPACE . Gateway::ROUTE ),
				'nonce_url'        => add_query_arg( 'action', 'rest-nonce', admin_url( 'admin-ajax.php' ) ),
				'locale'           => determine_locale(),
				'countries'        => (object) $countries,
				'scene_module_url' => $this->scene_module_url,
				'map_module_url'   => $this->map_module_url,
			)
		);
		return sprintf(
			'<section data-linker-planner data-planner-config="%s"><p role="status">%s</p></section>',
			esc_attr( is_string( $config ) ? $config : '{}' ),
			esc_html__( 'Opening your workspace…', 'linker-tools' )
		);
	}
}
