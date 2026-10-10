<?php
/**
 * Hooks of the Proforma module.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Proforma;

use Linker\Commerce\Inquiry\Statuses;
use Linker\Commerce\Proforma\Emails\ProformaIssuedEmail;

/**
 * The Proforma box and button on the inquiry screen, the Proforma column of
 * the inquiry list, and the email to the customer.
 */
final class Module {

	/**
	 * Sets up the module.
	 *
	 * @param string   $plugin_file Absolute path of the main plugin file.
	 * @param AdminBox $box         The admin box.
	 */
	public function __construct(
		private readonly string $plugin_file,
		private readonly AdminBox $box
	) {}

	/**
	 * Adds the module's hooks.
	 */
	public function register(): void {
		add_action( 'add_meta_boxes', array( $this->box, 'add' ) );
		add_action( 'woocommerce_process_shop_order_meta', array( $this->box, 'process' ), 60 );
		add_filter( 'woocommerce_order_actions', array( $this->box, 'order_actions' ) );
		add_filter( 'woocommerce_shop_order_list_table_columns', array( $this->box, 'columns' ) );
		add_action( 'woocommerce_shop_order_list_table_custom_column', array( $this->box, 'column' ), 10, 2 );
		add_filter( 'manage_edit-shop_order_columns', array( $this->box, 'columns' ) );
		add_action( 'manage_shop_order_posts_custom_column', array( $this->box, 'column' ), 10, 2 );

		add_filter( 'woocommerce_email_actions', array( $this, 'email_actions' ) );
		add_filter( 'woocommerce_email_classes', array( $this, 'add_email' ) );
	}

	/**
	 * WooCommerce sends emails only on the actions in this list.
	 *
	 * @param string[] $actions Actions.
	 * @return string[]
	 */
	public function email_actions( array $actions ): array {
		$actions[] = 'woocommerce_order_status_' . Statuses::RECEIVED . '_to_' . Statuses::PROFORMA;
		return $actions;
	}

	/**
	 * Adds the Proforma email.
	 *
	 * @param array<string, object> $emails Email objects by class.
	 * @return array<string, object>
	 */
	public function add_email( array $emails ): array {
		$emails[ ProformaIssuedEmail::class ] = new ProformaIssuedEmail( $this->plugin_file );
		return $emails;
	}
}
