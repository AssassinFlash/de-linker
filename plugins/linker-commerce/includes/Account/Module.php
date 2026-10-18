<?php
/**
 * Hooks of the account module.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Account;

/**
 * The account menu, the contact person, the inquiry list, saved solutions
 * and the route that saves them, documents and their downloads. A pending
 * account keeps the workspace with a review status notice.
 */
final class Module {

	/**
	 * Sets up the module.
	 *
	 * @param Menu                $menu      The menu.
	 * @param ContactCard         $contact   The contact person card.
	 * @param InquiryList         $inquiries The inquiry list.
	 * @param SavedSolutions      $solutions The saved solutions.
	 * @param Documents           $documents The documents page.
	 * @param DocumentDownload    $download  The downloads.
	 * @param SolutionsRoute      $route     The route that saves solutions.
	 * @param AccountStatusNotice $status_notice   The pending or restricted account status notice.
	 * @param AuthTemplates       $auth      The guest sign-in, register and lost-password pages.
	 * @param AdminAccessNotice   $admin_access The explanation of Woo's admin protection.
	 */
	public function __construct(
		private readonly Menu $menu,
		private readonly ContactCard $contact,
		private readonly InquiryList $inquiries,
		private readonly SavedSolutions $solutions,
		private readonly Documents $documents,
		private readonly DocumentDownload $download,
		private readonly SolutionsRoute $route,
		private readonly AccountStatusNotice $status_notice = new AccountStatusNotice(),
		private readonly AuthTemplates $auth = new AuthTemplates(),
		private readonly AdminAccessNotice $admin_access = new AdminAccessNotice()
	) {}

	/**
	 * Adds the module's hooks.
	 */
	public function register(): void {
		add_filter( 'woocommerce_get_query_vars', array( $this->menu, 'query_vars' ) );
		add_filter( 'woocommerce_account_menu_items', array( $this->menu, 'items' ), 20 );
		foreach ( array( 'orders', 'view-order', 'saved-solutions', 'documents', 'edit-address', 'edit-account' ) as $endpoint ) {
			add_filter( 'woocommerce_endpoint_' . $endpoint . '_title', array( $this->menu, 'title' ), 10, 2 );
		}
		$this->status_notice->register();
		add_action( 'linker_account_after_content', array( $this->contact, 'render' ) );
		$this->auth->register();
		$this->admin_access->register();

		add_filter( 'woocommerce_account_orders_columns', array( $this->inquiries, 'columns' ) );
		add_filter( 'woocommerce_my_account_my_orders_actions', array( $this->inquiries, 'actions' ), 10, 2 );
		add_action( 'woocommerce_order_item_meta_end', array( $this->inquiries, 'datasheet_link' ), 10, 4 );

		add_action( 'init', array( $this->solutions, 'register_post_type' ) );
		add_action( 'woocommerce_account_saved-solutions_endpoint', array( $this->solutions, 'render' ) );
		add_action( 'wp_loaded', array( $this->solutions, 'add_to_draft' ), 30 );
		add_action( 'woocommerce_load_cart_from_session', array( $this->solutions, 'claim' ) );
		add_action( 'rest_api_init', array( $this->route, 'register' ) );
		add_action( 'woocommerce_account_documents_endpoint', array( $this->documents, 'render' ) );
		add_action( 'template_redirect', array( $this->download, 'serve' ), 1 );
	}
}
