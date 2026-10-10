<?php
/**
 * Plugin bootstrap.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce;

use Linker\Commerce\Abilities\Registrar;
use Linker\Commerce\Admin\FiguresMetaBox;
use Linker\Commerce\Catalog\EngineeringFeedController;
use Linker\Commerce\Catalog\SelectionFactsController;
use Linker\Commerce\Storefront\CatalogFilters;
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
	 * @param FiguresMetaBox            $figures         The figure-citation meta box of the product edit screen (#8).
	 */
	public function __construct(
		private readonly string $file,
		private readonly Registrar $abilities,
		private readonly SelectionFactsController $selection_facts,
		private readonly EngineeringFeedController $engineering,
		private readonly FiguresMetaBox $figures
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
		add_action( 'add_meta_boxes', array( $this->figures, 'register' ) );
		add_action( 'save_post_product', array( $this->figures, 'save' ) );
		add_action( 'admin_notices', array( $this->figures, 'notice_refused' ) );
		add_action( 'cli_init', array( $this, 'register_cli' ) );

		$filters = new CatalogFilters();
		$filters->register();
		( new Storefront( $this->file ) )->register();
	}

	/**
	 * The presentation installer: LiveCanvas templates and Additional CSS.
	 */
	public function register_cli(): void {
		if ( ! class_exists( 'WP_CLI' ) ) {
			return;
		}
		\WP_CLI::add_command( 'linker-commerce present', new Cli\PresentCommand() );
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
	 * @return list<Settings\Module|Vocabulary\Module|Gating\Module|Mail\Module|Registration\Module|Inquiry\Module|Proforma\Module|Account\Module|Presentation\Module>
	 */
	private function commerce_modules(): array {
		$templates = plugin_dir_path( $this->file ) . 'templates/';
		$options   = new Settings\Options();
		$state     = new Gating\CommerceState();
		$prices    = new Gating\PriceDisplay( $state );
		$jobs      = new Mail\JobStore();
		$vat       = new Registration\VatProfile( new Registration\ViesClient() );
		$proformas = new Account\PrivateFiles( Proforma\Issuer::DIRECTORY );
		$solutions = new Account\SavedSolutions( new Account\PrivateFiles( Account\SavedSolutions::REPORTS_DIRECTORY ), $templates );
		$issuer    = new Proforma\Issuer( $options, new Proforma\Sequence(), new Proforma\Document( $options ), new Proforma\Renderer( $this->file ), $proformas, $prices );
		$documents = new Account\Documents( $solutions, $templates );
		$gate      = new Presentation\LoginGate();

		return array(
			new Settings\Module( new Settings\SettingsTab( $jobs ), new Settings\WooOptions() ),
			new Vocabulary\Module( new Vocabulary\Overrides( new Vocabulary\Terms() ), new Vocabulary\Labels(), new Vocabulary\LocaleFormat() ),
			new Gating\Module( $prices, new Gating\DraftSummary( $state, $prices ), new Gating\StoreApiPrices( $state ), new Gating\CatalogSorting( $state ) ),
			new Mail\Module( new Mail\Outbox( $jobs, new Mail\Throttle() ), $jobs, new Mail\EmailLocale(), new Mail\EmailPolicy() ),
			new Registration\Module( $this->file, $options, new Registration\Fields( $vat ), new Registration\BillingVatField( $vat ), new Registration\AddressForm() ),
			new Inquiry\Module( $this->file, $options, new Inquiry\Statuses(), new Inquiry\Checkout(), new Inquiry\OrderLocale(), new Inquiry\OrderAdmin() ),
			new Proforma\Module( $this->file, new Proforma\AdminBox( $issuer ) ),
			new Account\Module( new Account\Menu(), new Account\ContactCard( $options ), new Account\InquiryList(), $solutions, $documents, new Account\DocumentDownload( $proformas, $solutions ), new Account\SolutionsRoute( $solutions ) ),
			new Presentation\Module( new Presentation\Shortcodes( $gate, $solutions, $documents ), $gate, new Presentation\WindPress() ),
		);
	}
}
