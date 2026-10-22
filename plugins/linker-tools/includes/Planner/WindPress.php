<?php
/**
 * Source tokens from the isolated app enter the site's WindPress pipeline.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Planner;

/** The build exports static JSX classes; no second Tailwind build exists. */
final class WindPress {

	/**
	 * Locate the deployed app scan surface.
	 *
	 * @param string $plugin_file Main plugin file.
	 */
	public function __construct( private readonly string $plugin_file ) {}

	/** Native provider registration. */
	public function register(): void {
		add_filter( 'f!windpress/core/cache:compile.providers', array( $this, 'providers' ) );
	}

	/**
	 * Add the app's compiled source class inventory.
	 *
	 * @param array<int,array<string,mixed>> $providers Current providers.
	 * @return array<int,array<string,mixed>>
	 */
	public function providers( array $providers ): array {
		$providers[] = array(
			'id'          => 'linker-planner',
			'name'        => 'Linker planner',
			'description' => 'Isolated planner JSX classes',
			'callback'    => array( $this, 'scan' ),
			'enabled'     => true,
		);
		return $providers;
	}

	/**
	 * Scan only the exported class inventory, including deployed lazy views.
	 *
	 * @return list<array{name:string,content:string}>
	 */
	public function scan(): array {
		$file = plugin_dir_path( $this->plugin_file ) . 'build/planner/windpress.scan.txt';
		if ( ! is_readable( $file ) ) {
			return array();
		}
		$content = file_get_contents( $file ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- local build artifact.
		return false === $content ? array() : array(
			array(
				'name'    => 'planner-jsx',
				'content' => $content,
			),
		);
	}
}
