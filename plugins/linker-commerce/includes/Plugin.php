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
use Linker\Commerce\Products\ProductSearchController;
use Linker\Commerce\Products\EngineeringFeedController;
use Linker\Commerce\Products\SearchScope;
use Linker\Commerce\Products\SelectionFactsController;
use Linker\Commerce\Contact\Module as ContactModule;
use Linker\Commerce\Health\Monitor;
use Linker\Commerce\Storefront\ArchiveSchema;
use Linker\Commerce\Storefront\ProductFilters;
use Linker\Commerce\Storefront\ProductSchema;
use Linker\Commerce\Storefront\ProductView;

/**
 * Hooks Linker Commerce into WordPress.
 */
final class Plugin {

	/**
	 * Sets up the plugin.
	 *
	 * @param string                      $file            Absolute path of the main plugin file.
	 * @param Registrar                   $abilities       Registers the plugin's abilities.
	 * @param SelectionFactsController    $selection_facts REST route of the selection facts.
	 * @param EngineeringFeedController   $engineering     REST route of the engineering feed (#8).
	 * @param ProductSearchController     $product_search  REST route of the catalogue search (#68).
	 * @param SearchScope                 $search_scope    The scope of the site search results (#68).
	 * @param ContactModule               $contact         The contact form of the /contact/ page (#68).
	 * @param FiguresMetaBox              $figures         The figure-citation meta box of the product edit screen (#8).
	 * @param FaqsMetaBox                 $faqs            The FAQ meta box of the product edit screen (#15).
	 * @param DocumentsMetaBox            $documents       The document meta box of the product edit screen (#68).
	 * @param Account\SavedSolutions|null $solutions    The plugin's one store of saved solutions, shared with the read ability (#496).
	 */
	public function __construct(
		private readonly string $file,
		private readonly Registrar $abilities,
		private readonly SelectionFactsController $selection_facts,
		private readonly EngineeringFeedController $engineering,
		private readonly ProductSearchController $product_search,
		private readonly SearchScope $search_scope,
		private readonly ContactModule $contact,
		private readonly FiguresMetaBox $figures,
		private readonly FaqsMetaBox $faqs,
		private readonly DocumentsMetaBox $documents,
		private readonly ?Account\SavedSolutions $solutions = null
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
		add_action( 'rest_api_init', array( $this->product_search, 'register_routes' ) );
		add_action( 'add_meta_boxes', array( $this->figures, 'register' ) );
		add_action( 'save_post_product', array( $this->figures, 'save' ) );
		add_action( 'admin_notices', array( $this->figures, 'notice_refused' ) );
		add_action( 'add_meta_boxes', array( $this->faqs, 'register' ) );
		add_action( 'save_post_product', array( $this->faqs, 'save' ) );
		add_action( 'admin_notices', array( $this->faqs, 'notice_refused' ) );
		add_action( 'add_meta_boxes', array( $this->documents, 'register' ) );
		add_action( 'save_post_product', array( $this->documents, 'save' ) );
		add_action( 'cli_init', array( $this, 'register_cli' ) );

		add_action( 'plugins_loaded', array( $this, 'stand_down_legacy_template_preemption' ) );

		$filters = new ProductFilters();
		$filters->register();
		$this->search_scope->register();
		$this->contact->register();
		( new ProductSchema() )->register();
		( new ArchiveSchema() )->register();
		( new Consent\BasicMode() )->register();
		( new Products\Publication\Module() )->register();
		( new Monitor( $this->file, new Settings\Options() ) )->register();
	}

	/**
	 * Stands down the legacy stack's template preemption.
	 *
	 * The presentation layer's one rule (owner rulings 2026-10-10 and
	 * 2026-10-11, "LC 为基础"): the LiveCanvas dynamic templates are the only
	 * rendering channel of the commerce page types. The legacy stack's
	 * commerce renderer (terravolt-b2b-core's tv_b2b_template_include) still
	 * takes the shop, the product archives, the single product, cart and
	 * checkout away from them with a template_include filter at PHP_INT_MAX —
	 * above LiveCanvas's own 99998 — for as long as that plugin is installed,
	 * and the review instances are: their snapshot ships the live code. The
	 * filter is removed on plugins_loaded, when every plugin's registrations
	 * exist. The old plugin goes away whole at the production cutover; past
	 * it this removal finds nothing and retires with the old code.
	 */
	public function stand_down_legacy_template_preemption(): void {
		remove_filter( 'template_include', 'tv_b2b_template_include', PHP_INT_MAX );
	}

	/**
	 * The presentation installer, the stock push key, the test-mode switch and
	 * the blocked-registration counter.
	 */
	public function register_cli(): void {
		if ( ! class_exists( 'WP_CLI' ) ) {
			return;
		}
		\WP_CLI::add_command( 'linker-commerce', new Cli\PresentCommand() );
		\WP_CLI::add_command( 'linker-commerce inquiry-assessments', new Inquiry\Assessment\RecoveryCommand() );
		\WP_CLI::add_command( 'linker-commerce publication', new Cli\PublicationCommand() );
		\WP_CLI::add_command( 'linker-commerce stock-key', new Cli\StockKeyCommand() );
		\WP_CLI::add_command( 'linker-commerce test-mail', new Cli\TestMailCommand() );
		\WP_CLI::add_command( 'linker-commerce mail-budget', new Cli\MailBudgetCommand() );
		\WP_CLI::add_command( 'linker-commerce registration-blocks', new Cli\RegistrationBlocksCommand() );
		\WP_CLI::add_command( 'linker-commerce registration-notices', new Registration\RegistrationRecoveryCommand() );
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
	 * @return list<Settings\Module|Vocabulary\Module|Gating\Module|Mail\Module|Registration\Module|Inquiry\Module|Proforma\Module|Account\Module|Presentation\Module|Stock\Module|Digest\Module|Genie\Module|Protection\Module>
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
		$solutions = $this->solutions ?? new Account\SavedSolutions( new Account\PrivateFiles( Account\SavedSolutions::REPORTS_DIRECTORY ), $templates );
		$issuer    = new Proforma\Issuer( $options, new Proforma\Sequence(), new Proforma\Document( $options ), new Proforma\Renderer( $this->file ), $proformas, $prices );
		$documents = new Account\Documents( $solutions, $templates );
		$gate      = new Presentation\LoginGate( $approval );
		$checkout  = new Inquiry\Checkout();
		$fields    = new Registration\Fields( $vat, $approval );
		$accounts  = new Registration\Accounts( $approval, new Registration\RegistrationInformation( $fields ) );

		return array(
			new Settings\Module( new Settings\SettingsTab( $jobs ), new Settings\WooOptions() ),
			new Protection\Module( $this->file ),
			new Vocabulary\Module( new Vocabulary\Overrides( new Vocabulary\Terms() ), new Vocabulary\Labels(), new Vocabulary\LocaleFormat() ),
			new Gating\Module( $prices, new Gating\DraftSummary( $state, $prices ), new Gating\StoreApiPrices( $state ), new Gating\ProductSorting( $state ) ),
			new Mail\Module( new Mail\Outbox( $jobs, new Mail\Throttle() ), $jobs, new Mail\EmailLocale(), new Mail\EmailPolicy() ),
			new Digest\Module( $this->file, $jobs ),
			new Registration\Module( $this->file, $options, $fields, new Registration\BillingVatField( $vat ), new Registration\AddressForm(), $approval, new Registration\ApprovalAdmin( $approval ), new Registration\PendingApprovals( $approval ), new Registration\AccountsAdmin( $this->file, $accounts, $approval ), new Registration\AccountsController( $accounts, $approval ) ),
			new Inquiry\Module( $this->file, $options, new Inquiry\Statuses(), $checkout, new Inquiry\OrderLocale(), new Inquiry\OrderAdmin() ),
			new Proforma\Module( $this->file, new Proforma\AdminBox( $issuer ), $issuer ),
			new Account\Module( new Account\Menu(), new Account\ContactCard( $options ), new Account\InquiryList(), $solutions, $documents, new Account\DocumentDownload( $proformas, $solutions ), new Planning\LegacyRoutes() ),
			new Presentation\Module( new Presentation\Shortcodes(), $gate, new Presentation\WindPress(), account: new Presentation\AccountTemplates( $documents ) ),
			new Stock\Module( new Stock\StockController(), new Stock\BatchLog(), new Stock\Retention( $this->file ) ),
			new Genie\Module( $this->file, $options ),
		);
	}
}
