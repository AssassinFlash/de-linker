<?php
/**
 * Tests for the account module's hooks.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Account;

use Linker\Commerce\Account\ContactCard;
use Linker\Commerce\Account\DocumentDownload;
use Linker\Commerce\Account\Documents;
use Linker\Commerce\Account\InquiryList;
use Linker\Commerce\Account\Menu;
use Linker\Commerce\Account\Module;
use Linker\Commerce\Account\PrivateFiles;
use Linker\Commerce\Account\SavedSolutions;
use Linker\Commerce\Account\SolutionsRoute;
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
	 * The menu with its navigation template, titles, contact card, inquiry list, saved solutions with their route and claim, documents and downloads are hooked.
	 */
	public function test_register_adds_the_hooks(): void {
		$menu      = new Menu( '/plugin/templates/' );
		$contact   = new ContactCard( new Options() );
		$inquiries = new InquiryList();
		$saved     = new SavedSolutions( new PrivateFiles( SavedSolutions::REPORTS_DIRECTORY ), '/plugin/templates/' );
		$documents = new Documents( $saved, '/plugin/templates/' );
		$download  = new DocumentDownload( new PrivateFiles( 'proforma' ), $saved );
		$route     = new SolutionsRoute( $saved );

		WP_Mock::expectFilterAdded( 'woocommerce_get_query_vars', array( $menu, 'query_vars' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_account_menu_items', array( $menu, 'items' ), 20 );
		WP_Mock::expectFilterAdded( 'woocommerce_locate_template', array( $menu, 'navigation_template' ), 10, 2 );
		foreach ( array( 'orders', 'view-order', 'saved-solutions', 'documents', 'edit-address', 'edit-account' ) as $endpoint ) {
			WP_Mock::expectFilterAdded( 'woocommerce_endpoint_' . $endpoint . '_title', array( $menu, 'title' ), 10, 2 );
		}
		WP_Mock::expectActionAdded( 'woocommerce_account_content', array( $contact, 'render' ), 5 );
		WP_Mock::expectFilterAdded( 'woocommerce_account_orders_columns', array( $inquiries, 'columns' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_my_account_my_orders_actions', array( $inquiries, 'actions' ), 10, 2 );
		WP_Mock::expectActionAdded( 'woocommerce_order_item_meta_end', array( $inquiries, 'datasheet_link' ), 10, 4 );
		WP_Mock::expectActionAdded( 'init', array( $saved, 'register_post_type' ) );
		WP_Mock::expectActionAdded( 'woocommerce_account_saved-solutions_endpoint', array( $saved, 'render' ) );
		WP_Mock::expectActionAdded( 'wp_loaded', array( $saved, 'add_to_draft' ), 30 );
		WP_Mock::expectActionAdded( 'woocommerce_load_cart_from_session', array( $saved, 'claim' ) );
		WP_Mock::expectActionAdded( 'rest_api_init', array( $route, 'register' ) );
		WP_Mock::expectActionAdded( 'woocommerce_account_documents_endpoint', array( $documents, 'render' ) );
		WP_Mock::expectActionAdded( 'template_redirect', array( $download, 'serve' ), 1 );

		( new Module( $menu, $contact, $inquiries, $saved, $documents, $download, $route ) )->register();

		$this->assertConditionsMet();
	}
}
