<?php
/**
 * Minimal WooCommerce classes for the unit tests: the class hierarchy and the
 * members this plugin uses, with WooCommerce 11.1's signatures. Behaviour of
 * WooCommerce itself is tested against a real installation (tests/php/Integration).
 *
 * @package Linker\Commerce
 */

// phpcs:disable -- test doubles mirror WooCommerce's own class names and signatures.

if ( ! class_exists( 'WC_Data' ) ) {
	class WC_Data {
		public function get_id() { return 0; }
		public function get_meta( $key = '', $single = true, $context = 'view' ) { return ''; }
		public function update_meta_data( $key, $value, $meta_id = 0 ) {}
		public function add_meta_data( $key, $value, $unique = false ) {}
		public function save() { return 0; }
	}
	class WC_Product extends WC_Data {}
	class WC_Order_Item extends WC_Data {}
	class WC_Order_Item_Product extends WC_Order_Item {}
	class WC_Order_Item_Fee extends WC_Order_Item {}
	class WC_Abstract_Order extends WC_Data {}
	class WC_Order extends WC_Abstract_Order {}
	class WC_Customer extends WC_Data {}
	class WC_Cart {}
}
if ( ! class_exists( 'WC_DateTime' ) ) {
	class WC_DateTime extends \DateTimeImmutable {}
}

if ( ! class_exists( 'WC_Settings_API' ) ) {
	abstract class WC_Settings_API {
		public $id          = '';
		public $form_fields = array();
		public $settings    = array();
		public $enabled     = 'no';
		// Woo's native settings reload is exercised by bilingual native fixtures.
		public function init_settings() {
			$this->settings = get_option( 'woocommerce_' . $this->id . '_settings', null );
			if ( ! is_array( $this->settings ) ) {
				$this->settings = array();
				foreach ( $this->form_fields as $key => $field ) {
					$this->settings[ $key ] = $field['default'] ?? '';
				}
			}
		}
		public function get_option( $key, $empty_value = null ) {
			return $this->settings[ $key ] ?? $empty_value;
		}
	}
}

if ( ! class_exists( 'WC_Payment_Gateway' ) ) {
	abstract class WC_Payment_Gateway extends WC_Settings_API {
		public $title              = '';
		public $description        = '';
		public $has_fields         = false;
		public $method_title       = '';
		public $method_description = '';
		public $supports           = array( 'products' );
		public function get_return_url( $order = null ) {
			return 'https://example.test/proforma-request/inquiry-received/';
		}
	}
}

if ( ! class_exists( 'WC_Email' ) ) {
	class WC_Email extends WC_Settings_API {
		public $title          = '';
		public $description    = '';
		public $customer_email = false;
		public $template_html  = '';
		public $template_base  = null;
		public $placeholders   = array();
		public $object;
		public $recipient      = '';
		public function __construct() {}
		public function is_customer_email() { return $this->customer_email; }
		public function get_content_type( $default_content_type = '' ) { return 'text/html'; }
		public function get_heading() { return 'Heading'; }
		public function get_additional_content() { return ''; }
		public function get_recipient() { return $this->recipient; }
		// Woo's external sender contract; native filtering and the send lifecycle
		// are exercised by NotificationRoutingTest on the real local instance.
		public function get_from_name( $from_name = '' ) { return get_option( 'woocommerce_email_from_name', '' ); }
		public function get_from_address( $from_email = '' ) { return get_option( 'woocommerce_email_from_address', '' ); }
		// The tests observe sending through this action (WP_Mock::expectAction).
		protected function send_notification(): bool {
			do_action( 'linker_test_email_sent', $this->id, $this->get_recipient() );
			return true;
		}
	}
}

// The tests observe these static helpers through actions (WP_Mock::expectAction).
if ( ! class_exists( 'WC_Admin_Settings' ) ) {
	class WC_Admin_Settings {
		public static function add_error( $text ) { do_action( 'linker_test_settings_error', $text ); }
		public static function output_fields( $options ) { do_action( 'linker_test_settings_output', $options ); }
		public static function show_message( $message ) { echo $message; }
		public static function save_fields( $options, $data = null ) { do_action( 'linker_test_settings_saved', $options ); return true; }
	}
}

if ( ! class_exists( 'WC_Admin_Meta_Boxes' ) ) {
	class WC_Admin_Meta_Boxes {
		public static function add_error( $text ) { do_action( 'linker_test_meta_box_error', $text ); }
	}
}

if ( ! class_exists( 'WC_Validation' ) ) {
	class WC_Validation {
		public static function is_postcode( $postcode, $country ) {
			return 'DE' !== $country || 1 === preg_match( '/^[0-9]{5}$/', $postcode );
		}
	}
}

if ( ! class_exists( 'WC_Countries' ) ) {
	class WC_Countries {
		public function get_countries() {
			return array();
		}
		public function get_formatted_address( $args = array(), $separator = '<br/>' ) {
			return '';
		}
	}
}
