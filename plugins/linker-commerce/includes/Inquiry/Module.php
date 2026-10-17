<?php
/**
 * Hooks of the inquiry module.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry;

use Linker\Commerce\Inquiry\Emails\InquiryReceivedEmail;
use Linker\Commerce\Inquiry\Emails\NewInquiryEmail;
use Linker\Commerce\Settings\Options;

/**
 * Statuses, the Proforma gateway, the request page, the admin labels and the
 * two inquiry emails.
 */
final class Module {

	/**
	 * Sets up the module.
	 *
	 * @param string      $plugin_file Absolute path of the main plugin file.
	 * @param Options     $options     The plugin settings.
	 * @param Statuses    $statuses    The inquiry statuses.
	 * @param Checkout    $checkout    The Proforma request page.
	 * @param OrderLocale $locale      The inquiry language.
	 * @param OrderAdmin  $admin       The admin labels.
	 */
	public function __construct(
		private readonly string $plugin_file,
		private readonly Options $options,
		private readonly Statuses $statuses,
		private readonly Checkout $checkout,
		private readonly OrderLocale $locale,
		private readonly OrderAdmin $admin
	) {}

	/**
	 * Adds the module's hooks.
	 */
	public function register(): void {
		( new Form() )->register();
		( new AccountLink() )->register();
		( new Handler() )->register();
		add_action( 'before_woocommerce_init', array( $this, 'declare_compatibility' ) );
		add_action( 'init', array( $this->statuses, 'register' ) );
		add_filter( 'wc_order_statuses', array( $this->statuses, 'names' ) );
		add_filter( 'wc_order_is_editable', array( $this->statuses, 'editable' ), 10, 2 );
		add_filter( 'woocommerce_valid_order_statuses_for_order_again', array( $this->statuses, 'request_again' ) );
		add_filter( 'woocommerce_analytics_excluded_order_statuses', array( $this->statuses, 'analytics_excluded' ) );
		add_filter( 'woocommerce_can_reduce_order_stock', '__return_false' );
		add_action( 'admin_head', array( $this->statuses, 'admin_colours' ) );

		add_filter( 'woocommerce_payment_gateways', array( $this, 'add_gateway' ) );
		add_filter( 'woocommerce_available_payment_gateways', array( $this->checkout, 'gateways' ) );
		add_action( 'woocommerce_checkout_create_order', array( $this->checkout, 'without_payment_method_title' ) );
		add_action( 'woocommerce_after_checkout_validation', array( $this->checkout, 'validate_public' ), 10, 2 );
		add_filter( 'rest_pre_dispatch', array( $this->checkout, 'block_store_checkout' ), 10, 3 );
		add_action( 'woocommerce_checkout_create_order', array( $this->locale, 'remember' ) );
		add_action( 'woocommerce_thankyou_' . ProformaGateway::ID, array( $this->checkout, 'next_steps' ) );
		add_filter( 'woocommerce_get_checkout_order_received_url', array( $this->checkout, 'received_url' ), 10, 2 );
		add_filter( 'woocommerce_order_item_permalink', array( $this->checkout, 'item_permalink' ), 10, 3 );

		add_filter( 'woocommerce_register_post_type_shop_order', array( $this->admin, 'labels' ) );
		add_filter( 'manage_edit-shop_order_columns', array( $this->admin, 'columns' ) );
		add_filter( 'manage_woocommerce_page_wc-orders_columns', array( $this->admin, 'columns' ) );
		add_action( 'manage_shop_order_posts_custom_column', array( $this->admin, 'source' ), 10, 2 );
		add_action( 'manage_woocommerce_page_wc-orders_custom_column', array( $this->admin, 'source' ), 10, 2 );

		add_filter( 'woocommerce_email_actions', array( $this, 'email_actions' ) );
		add_filter( 'woocommerce_email_classes', array( $this, 'add_emails' ) );
	}

	/**
	 * Tells WooCommerce what the plugin works with: inquiries are orders read
	 * and written through WooCommerce's order objects only, so both order
	 * storages work; the Proforma request page is the classic checkout
	 * (shortcode), whose hooks the gateway and the page texts use, so the
	 * checkout block is not supported. Runs on before_woocommerce_init.
	 */
	public function declare_compatibility(): void {
		\Automattic\WooCommerce\Utilities\FeaturesUtil::declare_compatibility( 'custom_order_tables', $this->plugin_file, true );
		\Automattic\WooCommerce\Utilities\FeaturesUtil::declare_compatibility( 'cart_checkout_blocks', $this->plugin_file, false );
	}

	/**
	 * Adds the Proforma gateway.
	 *
	 * @param list<string|object> $gateways Gateway classes or objects.
	 * @return list<string|object>
	 */
	public function add_gateway( array $gateways ): array {
		$gateways[] = ProformaGateway::class;
		return $gateways;
	}

	/**
	 * WooCommerce sends emails only on the actions in this list.
	 *
	 * @param string[] $actions Actions.
	 * @return string[]
	 */
	public function email_actions( array $actions ): array {
		$actions[] = 'woocommerce_order_status_pending_to_' . Statuses::RECEIVED;
		return $actions;
	}

	/**
	 * Adds the two inquiry emails.
	 *
	 * @param array<string, object> $emails Email objects by class.
	 * @return array<string, object>
	 */
	public function add_emails( array $emails ): array {
		$emails[ InquiryReceivedEmail::class ] = new InquiryReceivedEmail( $this->plugin_file );
		$emails[ NewInquiryEmail::class ]      = new NewInquiryEmail( $this->plugin_file, $this->options );
		return $emails;
	}
}
