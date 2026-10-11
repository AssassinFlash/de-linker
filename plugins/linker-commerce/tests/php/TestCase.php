<?php
/**
 * Base of this plugin's unit tests.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests;

use Linker\Commerce\Gating\CommerceState;
use Linker\Commerce\Registration\Approval;
use WP_Mock;
use WP_User;

/**
 * WP_Mock's test case with shortcuts for the WordPress functions most classes
 * call: translation and escaping return their argument unchanged.
 */
abstract class TestCase extends WP_Mock\Tools\TestCase {

	/**
	 * The meta store of approval_meta().
	 *
	 * @var array<string, mixed>
	 */
	private array $user_meta = array();

	/**
	 * The user id get_current_user_id() answers while a test runs.
	 *
	 * @var int
	 */
	protected int $signed_in_user = 5;

	/**
	 * The plugin's own text domain loads again on every locale switch of the
	 * mail rendering (LocaleSwitch); tests do not count these calls.
	 */
	protected function reload_plugin_textdomain(): void {
		WP_Mock::userFunction( 'load_textdomain', array( 'times' => '0+' ) );
		WP_Mock::userFunction( 'determine_locale', array( 'return' => 'en_US' ) );
	}

	/**
	 * Lets translation and escaping functions return (or print) their first argument.
	 */
	protected function plain_text(): void {
		foreach ( array( '__', '_x', 'esc_html__', 'esc_attr__', 'esc_html_x', 'esc_html', 'esc_attr', 'esc_url', 'esc_url_raw', 'wp_kses_post' ) as $function ) {
			WP_Mock::passthruFunction( $function );
		}
		foreach ( array( '_e', 'esc_html_e', 'esc_attr_e' ) as $function ) {
			WP_Mock::echoFunction( $function );
		}
	}

	/**
	 * Lets an email switch to a language and back: WordPress's switch, WooCommerce's
	 * translations and the plugin_locale filter, the way LocaleSwitch does it.
	 *
	 * @param string $locale The language the email is expected to switch to.
	 */
	protected function allow_locale_switch( string $locale ): void {
		WP_Mock::userFunction( 'WC', array( 'return' => new Fixtures\WooCommerce() ) );
		WP_Mock::userFunction( 'switch_to_locale', array( 'args' => array( $locale ) ) );
		WP_Mock::userFunction( 'restore_previous_locale' );
		WP_Mock::userFunction( 'remove_filter' );
		// @phpstan-ignore argument.type (an AnyInstance callback, see expect_action_on_any)
		WP_Mock::expectFilterAdded( 'plugin_locale', array( new WP_Mock\Matcher\AnyInstance( \Linker\Commerce\Mail\LocaleSwitch::class ), 'plugin_locale' ) );
	}

	/**
	 * Expects an action hooked with a method of any instance of a class: for objects that
	 * add their hooks while they are being constructed.
	 *
	 * @param string $hook       Action.
	 * @param string $class_name Class of the instance.
	 * @param string $method     Method.
	 * @param int    $priority   Priority.
	 * @param int    $args       Number of arguments.
	 */
	protected function expect_action_on_any( string $hook, string $class_name, string $method, int $priority = 10, int $args = 1 ): void {
		// @phpstan-ignore argument.type (WP_Mock matches array callbacks with an AnyInstance, its docblock lists only callables)
		WP_Mock::expectActionAdded( $hook, array( new WP_Mock\Matcher\AnyInstance( $class_name ), $method ), $priority, $args );
	}

	/**
	 * Makes a filter return a value when it is applied with the given arguments
	 * (or with any arguments when none are given).
	 *
	 * @param string       $filter Filter.
	 * @param mixed        $value  Value the filter returns.
	 * @param array<mixed> $args   Arguments it is applied with.
	 * @throws \LogicException When WP_Mock answers with another responder.
	 */
	protected function filter_returns( string $filter, $value, array $args = array() ): void {
		$hook      = WP_Mock::onFilter( $filter );
		$responder = array() === $args ? $hook->withAnyArgs() : $hook->with( ...$args );
		if ( ! $responder instanceof WP_Mock\Filter_Responder ) {
			throw new \LogicException( 'WP_Mock::onFilter() answers with a Filter_Responder.' );
		}
		$responder->reply( $value );
	}

	/**
	 * The meta of the signed-in customer 5 (user 6 is staff), read and written
	 * by the Approval class for real.
	 *
	 * @param array<string, mixed> $store Meta key → value.
	 */
	protected function approval_meta( array $store ): void {
		$this->user_meta = $store;
		WP_Mock::userFunction(
			'get_user_meta',
			array(
				'return' => fn ( int $user_id, string $key ) => 5 === $user_id ? ( $this->user_meta[ $key ] ?? '' ) : '',
			)
		);
		WP_Mock::userFunction(
			'update_user_meta',
			array(
				'return' => function ( int $user_id, string $key, $value ): bool {
					if ( 5 !== $user_id ) {
						return false;
					}
					$this->user_meta[ $key ] = $value;
					return true;
				},
			)
		);
		WP_Mock::userFunction(
			'get_userdata',
			array(
				'return' => static function ( int $user_id ): ?WP_User {
					if ( ! in_array( $user_id, array( 5, 6 ), true ) ) {
						return null;
					}
					$user        = new WP_User();
					$user->ID    = $user_id;
					$user->roles = 6 === $user_id ? array( 'shop_manager' ) : array( 'customer' );
					return $user;
				},
			)
		);
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => fn (): int => $this->signed_in_user ) );
	}

	/**
	 * Who get_current_user_id() answers for from now on.
	 *
	 * @param int $user_id User.
	 */
	protected function signed_in( int $user_id ): void {
		$this->signed_in_user = $user_id;
	}

	/**
	 * The price rule of an approved visitor, for tests that read it.
	 */
	protected function approved_state(): CommerceState {
		$this->approval_meta( array( Approval::STATUS_META => Approval::APPROVED ) );
		return new CommerceState( new Approval() );
	}

	/**
	 * Mocks get_option() for the given option values; other options return their default.
	 *
	 * @param array<string, mixed> $values Option name → value.
	 */
	protected function options( array $values ): void {
		WP_Mock::userFunction(
			'get_option',
			array(
				'return' => static fn ( string $name, $default_value = false ) => array_key_exists( $name, $values ) ? $values[ $name ] : $default_value,
			)
		);
	}
}
