<?php
/**
 * Tests for the inquiry module's hooks.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Inquiry;

use Linker\Commerce\Inquiry\Checkout;
use Linker\Commerce\Inquiry\Emails\InquiryReceivedEmail;
use Linker\Commerce\Inquiry\Emails\NewInquiryEmail;
use Linker\Commerce\Inquiry\Module;
use Linker\Commerce\Inquiry\OrderAdmin;
use Linker\Commerce\Inquiry\OrderLocale;
use Linker\Commerce\Inquiry\ProformaGateway;
use Linker\Commerce\Inquiry\Statuses;
use Linker\Commerce\Settings\Options;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Tests for Module.
 *
 * @covers \Linker\Commerce\Inquiry\Module
 */
final class ModuleTest extends TestCase {

	/**
	 * Statuses, stock, gateway, request page, admin labels and emails are hooked; stock is never reduced.
	 */
	public function test_register_adds_the_hooks(): void {
		$this->expect_action_on_any( \Linker\Commerce\Inquiry\Assessment\RecoverySchedule::HOOK, \Linker\Commerce\Inquiry\Assessment\RecoverySchedule::class, 'recover' );
		// @phpstan-ignore argument.type (WP_Mock accepts its AnyInstance matcher for array callbacks, as below.)
		WP_Mock::expectFilterAdded( 'cron_schedules', array( new WP_Mock\Matcher\AnyInstance( \Linker\Commerce\Inquiry\Assessment\RecoverySchedule::class ), 'schedules' ) );
		$this->expect_action_on_any( \Linker\Commerce\Inquiry\Assessment\Queue::PROCESS, \Linker\Commerce\Inquiry\Assessment\Queue::class, 'process' );
		$this->expect_action_on_any( \Linker\Commerce\Inquiry\Assessment\Queue::EXPIRE, \Linker\Commerce\Inquiry\Assessment\Queue::class, 'expire' );
		$this->expect_action_on_any( \Linker\Commerce\Inquiry\Assessment\Queue::FINISH, \Linker\Commerce\Inquiry\Assessment\Queue::class, 'finish', 10, 2 );
		$this->expect_action_on_any( 'add_meta_boxes', \Linker\Commerce\Inquiry\Assessment\Admin::class, 'boxes' );
		$this->expect_action_on_any( 'admin_post_linker_inquiry_assessment_correct', \Linker\Commerce\Inquiry\Assessment\Admin::class, 'correct' );
		// @phpstan-ignore argument.type (WP_Mock accepts its AnyInstance matcher for array callbacks, as in TestCase::plain_text.)
		WP_Mock::expectFilterAdded( 'woocommerce_privacy_export_order_personal_data', array( new WP_Mock\Matcher\AnyInstance( \Linker\Commerce\Inquiry\Assessment\EvidencePrivacy::class ), 'export' ), 10, 2 );
		$this->expect_action_on_any( 'woocommerce_privacy_before_remove_order_personal_data', \Linker\Commerce\Inquiry\Assessment\EvidencePrivacy::class, 'erase' );
		WP_Mock::userFunction( 'add_shortcode', array( 'return' => true ) );
		$this->expect_action_on_any( 'woocommerce_created_customer', \Linker\Commerce\Inquiry\AccountLink::class, 'claim', 20 );
		$this->expect_action_on_any( 'admin_post_nopriv_linker_inquiry', \Linker\Commerce\Inquiry\Handler::class, 'handle' );
		$this->expect_action_on_any( 'admin_post_linker_inquiry', \Linker\Commerce\Inquiry\Handler::class, 'handle' );
		$statuses = new Statuses();
		$checkout = new Checkout();
		$locale   = new OrderLocale();
		$admin    = new OrderAdmin();
		$module   = new Module( '/plugin/linker-commerce.php', new Options(), $statuses, $checkout, $locale, $admin );

		WP_Mock::expectActionAdded( 'before_woocommerce_init', array( $module, 'declare_compatibility' ) );
		WP_Mock::expectActionAdded( 'init', array( $statuses, 'register' ) );
		WP_Mock::expectFilterAdded( 'wc_order_statuses', array( $statuses, 'names' ) );
		WP_Mock::expectFilterAdded( 'wc_order_is_editable', array( $statuses, 'editable' ), 10, 2 );
		WP_Mock::expectFilterAdded( 'woocommerce_valid_order_statuses_for_order_again', array( $statuses, 'request_again' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_analytics_excluded_order_statuses', array( $statuses, 'analytics_excluded' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_can_reduce_order_stock', '__return_false' );
		WP_Mock::expectActionAdded( 'admin_head', array( $statuses, 'admin_colours' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_payment_gateways', array( $module, 'add_gateway' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_add_to_cart_redirect', array( $checkout, 'after_add_destination' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_available_payment_gateways', array( $checkout, 'gateways' ) );
		WP_Mock::expectActionAdded( 'woocommerce_checkout_create_order', array( $checkout, 'without_payment_method_title' ) );
		WP_Mock::expectActionAdded( 'woocommerce_checkout_create_order', array( $locale, 'remember' ) );
		WP_Mock::expectActionAdded( 'woocommerce_thankyou_' . ProformaGateway::ID, array( $checkout, 'next_steps' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_get_checkout_order_received_url', array( $checkout, 'received_url' ), 10, 2 );
		WP_Mock::expectFilterAdded( 'woocommerce_order_item_permalink', array( $checkout, 'item_permalink' ), 10, 3 );
		WP_Mock::expectActionAdded( 'woocommerce_after_checkout_validation', array( $checkout, 'validate_public' ), 10, 2 );
		WP_Mock::expectActionAdded( 'woocommerce_before_checkout_process', array( $checkout, 'block_native_checkout' ) );
		WP_Mock::expectFilterAdded( 'rest_pre_dispatch', array( $checkout, 'block_store_checkout' ), 10, 3 );
		WP_Mock::expectFilterAdded( 'manage_edit-shop_order_columns', array( $admin, 'columns' ) );
		WP_Mock::expectFilterAdded( 'manage_woocommerce_page_wc-orders_columns', array( $admin, 'columns' ) );
		WP_Mock::expectActionAdded( 'manage_shop_order_posts_custom_column', array( $admin, 'source' ), 10, 2 );
		WP_Mock::expectActionAdded( 'manage_woocommerce_page_wc-orders_custom_column', array( $admin, 'source' ), 10, 2 );
		WP_Mock::expectActionAdded( 'add_meta_boxes', array( $admin, 'register_summary_box' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_register_post_type_shop_order', array( $admin, 'labels' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_email_actions', array( $module, 'email_actions' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_email_classes', array( $module, 'add_emails' ) );

		$module->register();

		$this->assertConditionsMet();
	}

	/**
	 * Both order storages are supported; the checkout block is not, the request page is the classic checkout.
	 */
	public function test_declare_compatibility(): void {
		WP_Mock::expectAction( 'linker_test_feature_declared', 'custom_order_tables', '/plugin/linker-commerce.php', true );
		WP_Mock::expectAction( 'linker_test_feature_declared', 'cart_checkout_blocks', '/plugin/linker-commerce.php', false );

		( new Module( '/plugin/linker-commerce.php', new Options(), new Statuses(), new Checkout(), new OrderLocale(), new OrderAdmin() ) )->declare_compatibility();

		$this->assertConditionsMet();
	}

	/**
	 * The gateway, the email action and the two emails are added.
	 */
	public function test_additions(): void {
		$module = new Module( '/plugin/linker-commerce.php', new Options(), new Statuses(), new Checkout(), new OrderLocale(), new OrderAdmin() );

		$this->assertSame( array( 'bacs', ProformaGateway::class ), $module->add_gateway( array( 'bacs' ) ) );
		$this->assertSame( array( 'woocommerce_order_status_pending_to_inquiry-received' ), $module->email_actions( array() ) );

		$this->plain_text();
		WP_Mock::userFunction( 'plugin_dir_path', array( 'return' => '/plugin/' ) );
		$this->expect_action_on_any( 'woocommerce_order_status_pending_to_inquiry-received_notification', InquiryReceivedEmail::class, 'trigger', 10, 2 );
		$this->expect_action_on_any( 'woocommerce_order_status_pending_to_inquiry-received_notification', NewInquiryEmail::class, 'trigger', 10, 2 );
		$this->assertSame( array( InquiryReceivedEmail::class, NewInquiryEmail::class ), array_keys( $module->add_emails( array() ) ) );
	}
}
