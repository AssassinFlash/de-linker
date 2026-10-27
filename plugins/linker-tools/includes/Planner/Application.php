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
	 * One document has one project/session coordinator.
	 *
	 * @var bool
	 */
	private bool $mounted = false;

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
		( new Indexing() )->register();
		( new WindPress( $this->plugin_file ) )->register();
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
