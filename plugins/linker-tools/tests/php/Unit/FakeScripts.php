<?php
/**
 * A wp_scripts() double that knows the Genie entry and its dependencies.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

/**
 * A wp_scripts() double that knows the Genie entry and its dependencies.
 */
final class FakeScripts {

	/**
	 * Whether the entry is registered.
	 *
	 * @var bool
	 */
	private readonly bool $registered;

	/**
	 * Sets up the double.
	 *
	 * @param bool $registered Whether the entry is registered.
	 */
	public function __construct( bool $registered = true ) {
		$this->registered = $registered;
	}

	/**
	 * The script lookup.
	 *
	 * @param string $handle Script handle.
	 * @return object|false
	 */
	public function query( string $handle ) {
		$deps = array(
			'linker-tools-genie' => array(
				'src'  => 'https://de-linker.test/wp-content/plugins/linker-tools/build/genie.js',
				'ver'  => 'abc123',
				'deps' => array( 'react-jsx-runtime', 'wp-element', 'wp-i18n' ),
			),
			'react-jsx-runtime'  => array(
				'src'  => '/wp-includes/js/dist/react-jsx-runtime.min.js',
				'deps' => array( 'react', 'react-dom' ),
			),
			'react'              => array(
				'src'  => '/wp-includes/js/dist/vendor/react.min.js',
				'deps' => array(),
			),
			'react-dom'          => array(
				'src'  => '/wp-includes/js/dist/vendor/react-dom.min.js',
				'deps' => array(),
			),
			'wp-element'         => array(
				'src'  => '/wp-includes/js/dist/element.min.js',
				'deps' => array( 'wp-escape-html' ),
			),
			'wp-escape-html'     => array(
				'src'  => '/wp-includes/js/dist/escape-html.min.js',
				'deps' => array(),
			),
			'wp-hooks'           => array(
				'src'  => '/wp-includes/js/dist/hooks.min.js',
				'deps' => array(),
			),
			'wp-i18n'            => array(
				'src'  => '/wp-includes/js/dist/i18n.min.js',
				'deps' => array( 'wp-hooks' ),
			),
		);
		if ( 'linker-tools-hero' === $handle ) {
			$deps[ $handle ]        = $deps['linker-tools-genie'];
			$deps[ $handle ]['src'] = '/build/hero.js';
		}
		if ( ! $this->registered || ! isset( $deps[ $handle ] ) ) {
			return false;
		}
		return (object) $deps[ $handle ];
	}
}
