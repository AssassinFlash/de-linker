<?php
/**
 * Minimal WordPress classes for the unit tests: the members this plugin uses,
 * with WordPress's signatures (WP_Mock mocks functions, not classes).
 *
 * @package Linker\Tools
 */

// phpcs:disable -- test doubles mirror WordPress's own class names and signatures.

// WordPress's time constants (wp-includes/default-constants.php).
defined( 'MINUTE_IN_SECONDS' ) || define( 'MINUTE_IN_SECONDS', 60 );
defined( 'HOUR_IN_SECONDS' ) || define( 'HOUR_IN_SECONDS', 60 * MINUTE_IN_SECONDS );
defined( 'DAY_IN_SECONDS' ) || define( 'DAY_IN_SECONDS', 24 * HOUR_IN_SECONDS );
defined( 'MONTH_IN_SECONDS' ) || define( 'MONTH_IN_SECONDS', 30 * DAY_IN_SECONDS );

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
	}
}

if ( ! class_exists( 'WP_User' ) ) {
	class WP_User {
		public $ID         = 0;
		public $user_email = '';
	}
}

if ( ! class_exists( 'WP_Post' ) ) {
	class WP_Post {
		public $ID            = 0;
		public $post_type     = 'post';
		public $post_author   = '0';
		public $post_title    = '';
		public $post_status   = 'publish';
		public $post_content  = '';
		public $post_name     = '';
			public $post_date_gmt     = '1970-01-01 00:00:00';
			public $post_modified_gmt = '1970-01-01 00:00:00';
		public function __construct( $post ) {
			foreach ( get_object_vars( $post ) as $key => $value ) {
				$this->$key = $value;
			}
		}
	}
}

if ( ! class_exists( 'WP_Post' ) ) {
	class WP_Post {
		public int $ID = 0;
		public string $post_type = 'post';
		public string $post_status = 'publish';
		public string $post_name = '';
	}
}

if ( ! class_exists( 'WP_Term' ) ) {
	class WP_Term {
		public $term_id = 0;
		public $slug = '';
		public $taxonomy = '';

		/**
		 * WordPress's own constructor: the term row, as an object.
		 *
		 * @param object|null $term The row, e.g. (object) array( 'term_id' => 1, 'slug' => 'x' ).
		 */
		public function __construct( $term = null ) {
			if ( is_object( $term ) ) {
				foreach ( get_object_vars( $term ) as $key => $value ) {
					$this->$key = $value;
				}
			}
		}
	}
}

if ( ! class_exists( 'WP_REST_Request' ) ) {
	class WP_REST_Request {
		private $method;
		private $route;
		private $params = array();
		private $query  = array();
		private $body   = '';
		public function __construct( $method = '', $route = '' ) {
			$this->method = $method;
			$this->route  = $route;
		}
		public function get_method() {
			return $this->method;
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
		public function set_query_params( $query ) {
			$this->query = $query;
		}
		public function get_query_params() {
			return $this->query;
		}
		public function set_body( $body ) {
			$this->body = $body;
		}
		public function get_body() {
			return $this->body;
		}
	}
}

if ( ! class_exists( 'WP_REST_Response' ) ) {
	class WP_REST_Response {
		public $data;
		public $status;
		/** @var array<string, string> */
		public $headers = array();
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
		public function header( $key, $value, $replace = true ) {
			if ( $replace || ! isset( $this->headers[ $key ] ) ) {
				$this->headers[ $key ] = $value;
			}
		}
		public function get_headers() {
			return $this->headers;
		}
	}
}
