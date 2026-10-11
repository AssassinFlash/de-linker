<?php
/**
 * Plugin bootstrap.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce;

use Linker\Commerce\Abilities\Registrar;
use Linker\Commerce\Admin\DocumentsMetaBox;
use Linker\Commerce\Admin\FaqsMetaBox;
use Linker\Commerce\Admin\FiguresMetaBox;
use Linker\Commerce\Catalog\CatalogSearchController;
use Linker\Commerce\Catalog\EngineeringFeedController;
use Linker\Commerce\Catalog\SearchScope;
use Linker\Commerce\Catalog\SelectionFactsController;
use Linker\Commerce\Contact\Module as ContactModule;
use Linker\Commerce\Health\Monitor;
use Linker\Commerce\Storefront\CatalogFilters;
use Linker\Commerce\Storefront\ProductSchema;
use Linker\Commerce\Storefront\ProductView;
use Linker\Commerce\Storefront\Storefront;

/**
 * Hooks Linker Commerce into WordPress.
 */
final class Plugin {

	/**
	 * Sets up the plugin.
	 *
	 * @param string                    $file            Absolute path of the main plugin file.
	 * @param Registrar                 $abilities       Registers the plugin's abilities.
	 * @param SelectionFactsController  $selection_facts REST route of the selection facts.
	 * @param EngineeringFeedController $engineering     REST route of the engineering feed (#8).
	 * @param CatalogSearchController   $catalog_search  REST route of the catalogue search (#68).
	 * @param SearchScope               $search_scope    The scope of the site search results (#68).
	 * @param ContactModule             $contact         The contact form of the /contact/ page (#68).
	 * @param FiguresMetaBox            $figures         The figure-citation meta box of the product edit screen (#8).
	 * @param FaqsMetaBox               $faqs            The FAQ meta box of the product edit screen (#15).
	 * @param DocumentsMetaBox          $documents       The document meta box of the product edit screen (#68).
	 */
	public function __construct(
		private readonly string $file,
		private readonly Registrar $abilities,
		private readonly SelectionFactsController $selection_facts,
		private readonly EngineeringFeedController $engineering,
		private readonly CatalogSearchController $catalog_search,
		private readonly SearchScope $search_scope,
		private readonly ContactModule $contact,
		private readonly FiguresMetaBox $figures,
		private readonly FaqsMetaBox $faqs,
		private readonly DocumentsMetaBox $documents
	) {}

	/**
	 * Adds the plugin's hooks.
	 */
	public function register(): void {
		// Priority 0: WooCommerce already uses strings at init 5 (its post types), and
		// Vocabulary replaces some of them with this plugin's translated strings.
		add_action( 'init', array( $this, 'load_textdomain' ), 0 );
		add_action( 'wp_abilities_api_categories_init', array( $this->abilities, 'register_category' ) );
		add_action( 'wp_abilities_api_init', array( $this->abilities, 'register_abilities' ) );
		add_action( 'rest_api_init', array( $this->selection_facts, 'register_routes' ) );
		add_action( 'plugins_loaded', array( $this, 'register_commerce' ) );
		add_action( 'rest_api_init', array( $this->engineering, 'register_routes' ) );
		add_action( 'rest_api_init', array( $this->catalog_search, 'register_routes' ) );
		add_action( 'add_meta_boxes', array( $this->figures, 'register' ) );
		add_action( 'save_post_product', array( $this->figures, 'save' ) );
		add_action( 'admin_notices', array( $this->figures, 'notice_refused' ) );
		add_action( 'add_meta_boxes', array( $this->faqs, 'register' ) );
		add_action( 'save_post_product', array( $this->faqs, 'save' ) );
		add_action( 'admin_notices', array( $this->faqs, 'notice_refused' ) );
		add_action( 'add_meta_boxes', array( $this->documents, 'register' ) );
		add_action( 'save_post_product', array( $this->documents, 'save' ) );
		add_action( 'cli_init', array( $this, 'register_cli' ) );

		$filters = new CatalogFilters();
		$filters->register();
		$this->search_scope->register();
		$this->contact->register();
		( new Storefront( $this->file ) )->register();
		( new ProductSchema() )->register();
		( new Monitor( $this->file, new Settings\Options() ) )->register();
	}

	/**
	 * The presentation installer, the stock push key, and the test-mode switch.
	 */
	public function register_cli(): void {
		if ( ! class_exists( 'WP_CLI' ) ) {
			return;
		}
		\WP_CLI::add_command( 'linker-commerce', new Cli\PresentCommand() );
		\WP_CLI::add_command( 'linker-commerce stock-key', new Cli\StockKeyCommand() );
		\WP_CLI::add_command( 'linker-commerce test-mail', new Cli\TestMailCommand() );
	}

	/**
	 * Loads the translations shipped in the plugin's languages/ directory.
	 */
	public function load_textdomain(): void {
		load_plugin_textdomain( 'linker-commerce', false, dirname( plugin_basename( $this->file ) ) . '/languages' );
	}

	/**
	 * Adds the hooks of the inquiry chain once every plugin is loaded; without
	 * WooCommerce there is nothing to add them to.
	 */
	public function register_commerce(): void {
		if ( ! class_exists( 'WooCommerce' ) ) {
			return;
		}
		foreach ( $this->commerce_modules() as $module ) {
			$module->register();
		}
	}

	/**
	 * The modules of the inquiry chain, with what they share.
	 *
	 * @return list<Settings\Module|Vocabulary\Module|Gating\Module|Mail\Module|Registration\Module|Inquiry\Module|Proforma\Module|Account\Module|Presentation\Module|Stock\Module|Digest\Module>
	 */
	private function commerce_modules(): array {
		$templates = plugin_dir_path( $this->file ) . 'templates/';
		$options   = new Settings\Options();
		$approval  = new Registration\Approval();
		$state     = new Gating\CommerceState( $approval );
		$prices    = new Gating\PriceDisplay( $state );
		$jobs      = new Mail\JobStore();
		$vat       = new Registration\VatProfile( new Registration\ViesClient() );
		$proformas = new Account\PrivateFiles( Proforma\Issuer::DIRECTORY );
		$solutions = new Account\SavedSolutions( new Account\PrivateFiles( Account\SavedSolutions::REPORTS_DIRECTORY ), $templates );
		$issuer    = new Proforma\Issuer( $options, new Proforma\Sequence(), new Proforma\Document( $options ), new Proforma\Renderer( $this->file ), $proformas, $prices );
		$documents = new Account\Documents( $solutions, $templates );
		$gate      = new Presentation\LoginGate( $approval );
		$checkout  = new Inquiry\Checkout( $approval );

		return array(
			new Settings\Module( new Settings\SettingsTab( $jobs ), new Settings\WooOptions() ),
			new Vocabulary\Module( new Vocabulary\Overrides( new Vocabulary\Terms() ), new Vocabulary\Labels(), new Vocabulary\LocaleFormat() ),
			new Gating\Module( $prices, new Gating\DraftSummary( $state, $prices ), new Gating\StoreApiPrices( $state ), new Gating\CatalogSorting( $state ) ),
			new Mail\Module( new Mail\Outbox( $jobs, new Mail\Throttle(), $options ), $jobs, new Mail\EmailLocale(), new Mail\EmailPolicy() ),
			new Digest\Module( $this->file, $jobs ),
			new Registration\Module( $this->file, $options, new Registration\Fields( $vat, $approval ), new Registration\BillingVatField( $vat ), new Registration\AddressForm(), $approval, new Registration\ApprovalAdmin( $approval ), new Registration\PendingApprovals( $approval ) ),
			new Inquiry\Module( $this->file, $options, new Inquiry\Statuses(), $checkout, new Inquiry\OrderLocale(), new Inquiry\OrderAdmin() ),
			new Proforma\Module( $this->file, new Proforma\AdminBox( $issuer ) ),
			new Account\Module( new Account\Menu(), new Account\ContactCard( $options ), new Account\InquiryList(), $solutions, $documents, new Account\DocumentDownload( $proformas, $solutions ), new Account\SolutionsRoute( $solutions ) ),
			new Presentation\Module( new Presentation\Shortcodes( $gate, $approval ), $gate, new Presentation\WindPress() ),
			new Stock\Module( new Stock\StockController(), new Stock\BatchLog(), new Stock\Retention( $this->file ) ),
		);
	}
}
