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
	 * Dependencies already printed by WordPress.
	 *
	 * @var list<string>
	 */
	public array $done = array();

	/**
	 * Whether the entry is registered.
	 *
	 * @var bool
	 */
	private readonly bool $registered;

	/**
	 * Whether the entry carries script translations.
	 *
	 * @var bool
	 */
	private readonly bool $translated;

	/**
	 * Sets up the double.
	 *
	 * @param bool $registered Whether the entry is registered.
	 * @param bool $translated Whether the entry has translations.
	 */
	public function __construct( bool $registered = true, bool $translated = false ) {
		$this->registered = $registered;
		$this->translated = $translated;
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
				'deps' => array(),
			),
			'wp-i18n'            => array(
				'src'  => '/wp-includes/js/dist/i18n.min.js',
				'deps' => array(),
			),
		);
		if ( ! $this->registered || ! isset( $deps[ $handle ] ) ) {
			return false;
		}
		return (object) $deps[ $handle ];
	}

	/**
	 * What WordPress would print as this handle's inline translation script.
	 *
	 * @param string $handle  Script handle.
	 * @param bool   $display Ignored; the callers under test read the return.
	 * @return string|false
	 */
	public function print_translations( string $handle, bool $display = true ) {
		unset( $display );
		if ( ! $this->translated || 'linker-tools-genie' !== $handle ) {
			return false;
		}
		return '( function( domain, translations ) { wp.i18n.setLocaleData( translations.locale_data.messages, domain ); } )( "linker-tools", {"locale_data":{"messages":{"":{"domain":"messages"},"Hide":["Ausblenden"]}}} );';
	}
}
