<?php
/**
 * Browser assets for the on-demand Genie entries.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Genie;

/** Resolves the registered WordPress dependency graph for each entry. */
final class EntryAssets {

	private const EXPORTS = array(
		'react'             => array( 'React' ),
		'react-dom'         => array( 'ReactDOM' ),
		'react-jsx-runtime' => array( 'ReactJSXRuntime' ),
		'wp-dom-ready'      => array( 'wp', 'domReady' ),
		'wp-element'        => array( 'wp', 'element' ),
		'wp-escape-html'    => array( 'wp', 'escapeHtml' ),
		'wp-hooks'          => array( 'wp', 'hooks' ),
		'wp-i18n'           => array( 'wp', 'i18n' ),
	);

	/**
	 * Queue the bootstrap, with no eager WordPress application dependencies.
	 *
	 * @param string   $entry Entry name.
	 * @param string[] $deps Other bootstrap handles.
	 * @phpstan-param list<non-empty-string> $deps
	 */
	public static function enqueue_loader( string $entry, array $deps = array() ): void {
		$root = dirname( __DIR__, 2 );
		$file = "assets/{$entry}-loader.js";
		wp_enqueue_script(
			"linker-tools-{$entry}-loader",
			plugins_url( $file, $root . '/linker-tools.php' ),
			$deps,
			substr( (string) md5_file( $root . '/' . $file ), 0, 12 ),
			array(
				'in_footer' => true,
				'strategy'  => 'defer',
			)
		);
	}

	/**
	 * Registered URL with the same cache version as a native enqueue.
	 *
	 * @param string $handle Registered handle.
	 * @param bool   $style Request the stylesheet for the handle.
	 */
	public static function url( string $handle, bool $style = false ): string {
		$registry = $style ? wp_styles() : wp_scripts();
		$asset    = $registry->query( $handle );
		if ( ! $asset || ! is_string( $asset->src ) || '' === $asset->src ) {
			return '';
		}
		$version = $asset->ver ?? null;
		if ( false === $version ) {
			$version = $registry->default_version;
		}
		return $version ? $asset->src . ( str_contains( $asset->src, '?' ) ? '&' : '?' ) . 'ver=' . rawurlencode( (string) $version ) : $asset->src;
	}

	/**
	 * Resolve the ordered scripts and catalog needed for one application.
	 *
	 * @param string $entry Built entry basename.
	 * @return array{src:string,deps:list<string>,nativeDependencies:array<string,list<string>>,translationUrls:list<string>}
	 */
	public static function config( string $entry ): array {
		$handle = 'linker-tools-' . $entry;
		$deps   = array();
		$native = array();
		$walk   = static function ( string $name ) use ( &$walk, &$deps, &$native, $handle ): void {
			$script = wp_scripts()->query( $name );
			if ( ! $script ) {
				return;
			}
			foreach ( $script->deps as $dep ) {
				$walk( $dep );
			}
			if ( $name === $handle || isset( $deps[ $name ] ) ) {
				return;
			}
			$url = self::url( $name );
			if ( '' !== $url ) {
				$deps[ $name ] = $url;
				if ( isset( self::EXPORTS[ $name ] ) ) {
					$native[ $url ] = self::EXPORTS[ $name ];
				}
			}
		};
		$walk( $handle );
		$root     = dirname( __DIR__, 2 );
		$relative = 'languages/linker-tools-' . determine_locale() . '-' . md5( 'build/' . $entry . '.js' ) . '.json';
		$file     = $root . '/' . $relative;
		return array(
			'src'                => self::url( $handle ),
			'deps'               => array_values( $deps ),
			'nativeDependencies' => $native,
			'translationUrls'    => is_file( $file ) ? array( plugins_url( $relative, $root . '/linker-tools.php' ) . '?ver=' . substr( (string) hash_file( 'sha256', $file ), 0, 12 ) ) : array(),
		);
	}
}
