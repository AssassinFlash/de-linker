<?php
/**
 * WindPress scan provider for this plugin's HTML and PHP.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

/**
 * Registers on f!windpress/core/cache:compile.providers the way picostrap does
 * (inc/windpress-support.php), so Tailwind classes in the new templates and in
 * this plugin's HTML enter the same compile surface.
 */
final class WindPress {

	/**
	 * Adds the provider.
	 */
	public function register(): void {
		add_filter( 'f!windpress/core/cache:compile.providers', array( $this, 'providers' ) );
	}

	/**
	 * Appends this plugin to the compile providers.
	 *
	 * @param array<int, array<string, mixed>> $providers Existing providers.
	 * @return array<int, array<string, mixed>>
	 */
	public function providers( array $providers ): array {
		$providers[] = array(
			'id'          => 'linker-commerce',
			'name'        => 'Linker Commerce',
			'description' => 'Scans linker-commerce templates and PHP for Tailwind classes',
			'callback'    => array( $this, 'scan' ),
			'enabled'     => true,
		);
		return $providers;
	}

	/**
	 * Files WindPress should scan: LiveCanvas HTML plus PHP that prints classes.
	 *
	 * @return list<array{name: string, content: string}>
	 */
	public function scan(): array {
		$root     = dirname( __DIR__, 2 );
		$contents = array();
		foreach ( Templates::catalog() as $path ) {
			$contents[] = array(
				'name'    => 'livecanvas/' . basename( $path ),
				'content' => Tokens::read( $path ),
			);
		}
		foreach ( $this->php_files( $root . '/includes/Presentation' ) as $path ) {
			$contents[] = array(
				'name'    => 'includes/Presentation/' . basename( $path ),
				'content' => Tokens::read( $path ),
			);
		}
		return $contents;
	}

	/**
	 * PHP files in a directory.
	 *
	 * @param string $dir Directory.
	 * @return list<string>
	 */
	private function php_files( string $dir ): array {
		$files = glob( $dir . '/*.php' );
		return false === $files ? array() : $files;
	}
}
