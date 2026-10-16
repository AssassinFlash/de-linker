<?php
/**
 * The plugin's WindPress volume stylesheets.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

	/**
	 * The storefront component CSS is a WindPress volume file: `present` copies
	 * `content/windpress/*.css` into the volume directory the WindPress compiler
	 * reads (uploads/windpress/data/) and makes the volume's `main.css` import
	 * them — the compiler's entry point only reaches a volume file through an
	 * import, which is how the site's own `terravolt-*.css` are wired. The next
	 * compile ships the rules inside the compiled cache; the plugin never
	 * enqueues site CSS itself (AGENTS.md presentation ruling). The styles reach
	 * exactly the templates whose class names the selectors carry.
	 *
	 * `tokens.css` and `site-base.css` are the header's foundation, formerly
	 * inlined in both header partials. `content/windpress/tokens.css` is the
	 * only tokens file: Tokens::path() reads it, and this volume publishes
	 * it. The compiler keeps their declarations (verified against Tailwind
	 * 4.3, the version the volume compiles with).
	 */
final class WindPressVolume {

	/**
	 * The compiler's entry stylesheet in the volume.
	 */
	private const ENTRY = 'main.css';

	/**
	 * Directory of the exported stylesheets, relative to this plugin.
	 */
	private const RELATIVE_DIR = 'content/windpress';

	/**
	 * Copies each exported stylesheet into the volume directory and imports
	 * it from `main.css`; a changed file keeps its previous copy beside it,
	 * so a rollback is one rename away.
	 */
	public function install(): void {
		$data_dir = $this->data_dir();
		if ( null === $data_dir ) {
			return;
		}
		$imports = array();
		foreach ( self::files() as $source ) {
			$target    = $data_dir . '/' . basename( $source );
			$imports[] = './' . basename( $source );
			if ( file_exists( $target ) && md5_file( $source ) !== md5_file( $target ) ) {
				copy( $target, $target . '.bak' );
			}
			if ( ! file_exists( $target ) || md5_file( $source ) !== md5_file( $target ) ) {
				copy( $source, $target );
			}
		}
		$this->import_from_entry( $data_dir . '/' . self::ENTRY, $imports );
	}

	/**
	 * Adds the volume files' imports to `main.css` when missing; a changed
	 * entry keeps its previous copy beside it. The import lines go to the
	 * bottom, after the file's own imports — Tailwind v4 orders the cascade
	 * by import position, and our selectors carry their own specificity.
	 *
	 * @param string   $entry   Absolute path of `main.css`.
	 * @param string[] $imports The relative paths to import.
	 */
	private function import_from_entry( string $entry, array $imports ): void {
		// phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- local volume file on disk, not a remote URL.
		$current = is_readable( $entry ) ? (string) file_get_contents( $entry ) : '';
		$missing = array();
		foreach ( $imports as $import ) {
			$rule = "@import \"{$import}\";";
			if ( ! str_contains( $current, $import ) ) {
				$missing[] = $rule;
			}
		}
		// A renamed volume file leaves its old import in main.css, and the
		// compiler follows every import it finds. The previous names are the
		// only ones removed: an instance compiled before the rename would
		// otherwise ship both selector families.
		$retired = array( './catalogue.css', './catalogue-mounts.css' );
		$kept    = array();
		$dropped = false;
		$lines   = '' === $current ? array() : explode( "\n", str_replace( "\r\n", "\n", $current ) );
		foreach ( $lines as $line ) {
			$retires = false;
			foreach ( $retired as $old ) {
				if ( str_contains( $line, $old ) ) {
					$retires = true;
					break;
				}
			}
			if ( $retires ) {
				$dropped = true;
				continue;
			}
			$kept[] = $line;
		}
		if ( array() === $missing && ! $dropped ) {
			return;
		}
		if ( '' !== $current ) {
			copy( $entry, $entry . '.bak' );
		}
		$current = implode( "\n", $kept );
		// phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_file_put_contents -- local volume file on disk, not a remote URL.
		file_put_contents( $entry, rtrim( $current ) . "\n" . implode( "\n", $missing ) . "\n" );
	}

	/**
	 * The volume files' drift against the exported stylesheets: the read-only
	 * twin of install(), for a deploy to assert that the volume really carries
	 * the checkout's files. A volume file absent, or with a hash the export
	 * does not carry, is one row; the entry's missing imports are one more.
	 * Nothing here writes, and the volume directory is not created (a site
	 * without WindPress has no volume to compare).
	 *
	 * @return list<array{surface: string, target: string, detail: string}> Drift rows, empty when in sync.
	 */
	public function drift(): array {
		$uploads = wp_get_upload_dir();
		if ( empty( $uploads['basedir'] ) ) {
			return array(
				array(
					'surface' => 'windpress volume',
					'target'  => 'uploads',
					'detail'  => 'the uploads directory cannot be resolved',
				),
			);
		}
		$dir = $uploads['basedir'] . '/windpress/data';
		if ( ! is_dir( $dir ) ) {
			return array(
				array(
					'surface' => 'windpress volume',
					'target'  => 'windpress/data',
					'detail'  => 'the volume directory does not exist: present has not installed it',
				),
			);
		}
		$rows    = array();
		$imports = array();
		foreach ( self::files() as $source ) {
			$name      = basename( $source );
			$target    = $dir . '/' . $name;
			$imports[] = './' . $name;
			if ( ! is_readable( $target ) ) {
				$rows[] = array(
					'surface' => 'windpress volume',
					'target'  => $name,
					'detail'  => 'not installed',
				);
				continue;
			}
			if ( md5_file( $source ) !== md5_file( $target ) ) {
				$rows[] = array(
					'surface' => 'windpress volume',
					'target'  => $name,
					'detail'  => 'the volume copy does not hash the same as the export',
				);
			}
		}
		// phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- local volume file on disk, not a remote URL.
		$entry = is_readable( $dir . '/' . self::ENTRY ) ? (string) file_get_contents( $dir . '/' . self::ENTRY ) : '';
		foreach ( $imports as $import ) {
			if ( ! str_contains( $entry, $import ) ) {
				$rows[] = array(
					'surface' => 'windpress volume',
					'target'  => self::ENTRY,
					'detail'  => 'the entry does not import ' . $import,
				);
			}
		}
		return $rows;
	}

	/**
	 * Absolute path of the exported stylesheets.
	 */
	public static function path(): string {
		return dirname( __DIR__, 2 ) . '/' . self::RELATIVE_DIR;
	}

	/**
	 * Absolute paths of the exported stylesheets.
	 *
	 * @return list<string>
	 */
	public static function files(): array {
		$files = glob( self::path() . '/*.css' );
		return false === $files ? array() : $files;
	}

	/**
	 * The volume directory WindPress reads, null when its path cannot be
	 * resolved (WindPress inactive — nothing will compile, nothing to install).
	 */
	private function data_dir(): ?string {
		$uploads = wp_get_upload_dir();
		if ( empty( $uploads['basedir'] ) ) {
			return null;
		}
		$dir = $uploads['basedir'] . '/windpress/data';
		if ( ! is_dir( $dir ) ) {
			wp_mkdir_p( $dir );
		}
		return is_dir( $dir ) ? $dir : null;
	}
}
