<?php
/**
 * Tests for the account module's hooks.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Account;

use Linker\Commerce\Account\AdminAccessNotice;
use Linker\Commerce\Account\AuthTemplates;
use Linker\Commerce\Account\ContactCard;
use Linker\Commerce\Account\DocumentDownload;
use Linker\Commerce\Account\Documents;
use Linker\Commerce\Account\InquiryList;
use Linker\Commerce\Account\Menu;
use Linker\Commerce\Account\Module;
use Linker\Commerce\Account\AccountStatusNotice;
use Linker\Commerce\Account\PrivateFiles;
use Linker\Commerce\Account\SavedSolutions;
use Linker\Commerce\Account\SolutionsRoute;
use Linker\Commerce\Account\SolutionDraftRoute;
use Linker\Commerce\Settings\Options;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Tests for Module.
 *
 * @covers \Linker\Commerce\Account\Module
 */
final class ModuleTest extends TestCase {

	/**
	 * The menu, titles, contact card, inquiry list, saved solutions with their route and claim, documents, downloads, the pending review page and the guest auth pages are hooked.
	 */
	public function test_register_adds_the_hooks(): void {
		$menu        = new Menu();
		$contact     = new ContactCard( new Options() );
		$inquiries   = new InquiryList();
		$saved       = new SavedSolutions( new PrivateFiles( SavedSolutions::REPORTS_DIRECTORY ), '/plugin/templates/' );
		$documents   = new Documents( $saved, '/plugin/templates/' );
		$download    = new DocumentDownload( new PrivateFiles( 'proforma' ), $saved );
		$route       = new SolutionsRoute( $saved );
		$draft_route = new SolutionDraftRoute();
		$auth        = new AuthTemplates();

		WP_Mock::expectFilterAdded( 'woocommerce_get_query_vars', array( $menu, 'query_vars' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_account_menu_items', array( $menu, 'items' ), 20 );
		foreach ( array( 'orders', 'view-order', 'saved-solutions', 'documents', 'edit-address', 'edit-account' ) as $endpoint ) {
			WP_Mock::expectFilterAdded( 'woocommerce_endpoint_' . $endpoint . '_title', array( $menu, 'title' ), 10, 2 );
		}
		$pending = new AccountStatusNotice();
		WP_Mock::expectActionAdded( 'woocommerce_account_content', array( $pending, 'render' ), 5 );
		WP_Mock::expectActionAdded( 'linker_account_after_content', array( $contact, 'render' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_account_orders_columns', array( $inquiries, 'columns' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_my_account_my_orders_actions', array( $inquiries, 'actions' ), 10, 2 );
		WP_Mock::expectActionAdded( 'woocommerce_order_item_meta_end', array( $inquiries, 'datasheet_link' ), 10, 4 );
		WP_Mock::expectActionAdded( 'init', array( $saved, 'register_post_type' ) );
		WP_Mock::expectActionAdded( 'woocommerce_account_saved-solutions_endpoint', array( $saved, 'render' ) );
		WP_Mock::expectActionAdded( 'wp_loaded', array( $saved, 'add_to_draft' ), 30 );
		WP_Mock::expectActionAdded( 'woocommerce_load_cart_from_session', array( $saved, 'claim' ) );
		WP_Mock::expectActionAdded( 'rest_api_init', array( $route, 'register' ) );
		WP_Mock::expectActionAdded( 'rest_api_init', array( $draft_route, 'register' ) );
		WP_Mock::expectActionAdded( 'woocommerce_account_documents_endpoint', array( $documents, 'render' ) );
		WP_Mock::expectActionAdded( 'template_redirect', array( $download, 'serve' ), 1 );
		WP_Mock::expectFilterAdded( 'woocommerce_get_query_vars', array( $auth, 'query_vars' ) );
		WP_Mock::expectFilterAdded( 'wc_get_template', array( $auth, 'template' ), 30, 2 );
		WP_Mock::expectActionAdded( 'template_redirect', array( $auth, 'signed_out_notice' ) );
		WP_Mock::expectActionAdded( 'template_redirect', array( $auth, 'register_redirect' ) );

		$admin_access = new AdminAccessNotice();
		WP_Mock::expectFilterAdded( 'woocommerce_prevent_admin_access', array( $admin_access, 'protect' ), PHP_INT_MAX );
		WP_Mock::expectFilterAdded( 'wc_get_template', array( $admin_access, 'template' ), 50, 2 );
		WP_Mock::userFunction(
			'add_shortcode',
			array(
				'args' => array( 'linker_admin_access_field', array( $admin_access, 'field' ) ),
				'once' => true,
			)
		);

		( new Module( $menu, $contact, $inquiries, $saved, $documents, $download, $route, $pending, $auth, $admin_access, $draft_route ) )->register();

		$this->assertConditionsMet();
	}
}
