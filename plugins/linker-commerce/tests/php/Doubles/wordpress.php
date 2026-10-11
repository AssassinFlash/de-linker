<?php
/**
 * Minimal WordPress classes for the unit tests: the members this plugin uses,
 * with WordPress's signatures (WP_Mock mocks functions, not classes).
 *
 * @package Linker\Commerce
 */

// phpcs:disable -- test doubles mirror WordPress's own class names and signatures.

// WordPress's time constants (wp-includes/default-constants.php).
defined( 'MINUTE_IN_SECONDS' ) || define( 'MINUTE_IN_SECONDS', 60 );
defined( 'HOUR_IN_SECONDS' ) || define( 'HOUR_IN_SECONDS', 60 * MINUTE_IN_SECONDS );
defined( 'DAY_IN_SECONDS' ) || define( 'DAY_IN_SECONDS', 24 * HOUR_IN_SECONDS );

	if ( ! class_exists( 'wpdb' ) ) {
		class wpdb {
			public $prefix = 'wp_';
			public function prepare( $query, ...$args ) {
				return $query;
			}
			public function get_col( $query = null, $x = 0 ) {
				return array();
			}
			public function get_results( $query = null, $output = OBJECT ) {
				return array();
			}
		}
	}

	if ( ! class_exists( 'WP_Error' ) ) {
	class WP_Error {
		/** @var array<string, list<string>> */
		public $errors = array();
		/** @var array<string, mixed> */
		public $error_data = array();
		public function __construct( $code = '', $message = '', $data = '' ) {
			if ( '' !== $code ) {
				$this->add( $code, $message, $data );
			}
		}
		public function add( $code, $message, $data = '' ) {
			$this->errors[ $code ][] = $message;
			if ( '' !== $data ) {
				$this->error_data[ $code ] = $data;
			}
		}
		public function get_error_code() {
			return array_key_first( $this->errors ) ?? '';
		}
		public function get_error_data( $code = '' ) {
			return $this->error_data[ '' === $code ? $this->get_error_code() : $code ] ?? null;
		}
		public function has_errors() {
			return array() !== $this->errors;
		}
		public function get_error_message( $code = '' ) {
			$all = $this->get_error_messages();
			return $all[0] ?? '';
		}
		public function get_error_messages( $code = '' ) {
			return array_merge( ...array_values( $this->errors ?: array( array() ) ) );
		}
		public function get_error_codes() {
			return array_keys( $this->errors );
		}
	}
}

if ( ! class_exists( 'WP_User' ) ) {
	class WP_User {
		public $ID           = 0;
		public $user_email   = '';
		public $display_name = '';
		public $user_login   = '';
		/** WordPress's signature: "Y-m-d H:i:s" in the site's own time. */
		public $user_registered = '';
		/** @var list<string> */
		public $roles = array();
	}
}

if ( ! class_exists( 'WP_Session_Tokens' ) ) {
	/**
	 * The API WordPress signs sessions out with; the double records the
	 * destroyed users so a test can assert the sign-out.
	 */
	class WP_Session_Tokens {
		/** @var list<int> */
		public static array $destroyed_all = array();

		public static function get_instance( $user_id ): self {
			return new self( (int) $user_id );
		}

		public function __construct( public readonly int $user_id ) {}

		public function destroy_all(): void {
			self::$destroyed_all[] = $this->user_id;
		}
	}
}

if ( ! class_exists( 'WP_Post' ) ) {
	class WP_Post {
		public $ID          = 0;
		public $post_type   = 'post';
		public $post_author = '0';
		public $post_title  = '';
		public $post_status  = 'publish';
		public $post_content = '';
		public $post_name    = '';
		public function __construct( $post ) {
			foreach ( get_object_vars( $post ) as $key => $value ) {
				$this->$key = $value;
			}
		}
	}
}

if ( ! class_exists( 'WP_REST_Request' ) ) {
	class WP_REST_Request {
		private $route;
		private $params = array();
		public function __construct( $method = '', $route = '' ) {
			$this->route = $route;
		}
		public function get_route() {
			return $this->route;
		}
		public function set_param( $key, $value ) {
			$this->params[ $key ] = $value;
		}
		public function get_param( $key ) {
			return $this->params[ $key ] ?? null;
		}
	}
}

if ( ! class_exists( 'WP_REST_Response' ) ) {
	class WP_REST_Response {
		public $data;
		public $status;
		public function __construct( $data = null, $status = 200 ) {
			$this->data   = $data;
			$this->status = $status;
		}
		public function get_status() {
			return $this->status;
		}
		public function get_data() {
			return $this->data;
		}
		public function set_data( $data ) {
			$this->data = $data;
		}
	}
}

// LocaleSwitch reloads the plugin's text domain (tests use the doubles, never WordPress's own).
	if ( ! function_exists( 'unload_textdomain' ) ) {
		function unload_textdomain( $domain ) {
			return true;
		}
	}

	if ( ! class_exists( 'WP_CLI' ) ) {
		class WP_CLI {
			/** @var array<string, callable> The commands add_command registered. */
			public static array $registered_commands = array();
			public static function error( $message ) {
				throw new \WP_CLI\ExitException( (string) $message );
			}
			public static function log( $message ) {
				echo 'wp-cli log: ' . $message . "\n";
			}
			public static function success( $message ) {
				echo 'wp-cli success: ' . $message . "\n";
			}
			public static function warning( $message ) {
				echo 'wp-cli warning: ' . $message . "\n";
			}
			public static function add_command( $name, $callable ) {
				self::$registered_commands[ (string) $name ] = $callable;
			}
		}
	}
	if ( ! class_exists( 'WP_CLI\ExitException' ) ) {
		class WP_CLI_ExitException extends \Exception {}
		class_alias( WP_CLI_ExitException::class, 'WP_CLI\\ExitException' );
	}
