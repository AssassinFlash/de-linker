<?php
/**
 * Hooks of the presentation module.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

use Linker\Commerce\Storefront\ProductFilters;
use Linker\Commerce\Storefront\ProductView;

/**
 * Shortcodes, the catalogue shortcodes, the empty Proforma-request gate, the
 * comparison page, the document library page and WindPress.
 */
final class Module {

	/**
	 * Sets up the module.
	 *
	 * @param Shortcodes             $shortcodes B2B shortcodes.
	 * @param LoginGate              $gate       Empty Proforma-request page.
	 * @param WindPress              $windpress  Compile provider.
	 * @param ProductShortcodes|null $products   The replica product shortcodes; built
	 *                                           from the kept data layers when omitted.
	 * @param ComparePage            $compare    The comparison page and its chip (#66).
	 * @param LibraryPage            $library    The document library page (#66).
	 * @param AccountTemplates       $account    Account content data for LC.
	 * @param BlogShortcodes         $blog       The blog single template's data.
	 */
	public function __construct(
		private readonly Shortcodes $shortcodes,
		private readonly LoginGate $gate,
		private readonly WindPress $windpress,
		private readonly ?ProductShortcodes $products = null,
		private readonly ComparePage $compare = new ComparePage(),
		private readonly LibraryPage $library = new LibraryPage(),
		private readonly AccountTemplates $account = new AccountTemplates(),
		private readonly BlogShortcodes $blog = new BlogShortcodes()
	) {}

	/**
	 * Adds the module's hooks.
	 */
	public function register(): void {
		$this->shortcodes->register();
			( $this->products ?? new ProductShortcodes( new ProductFilters(), new ProductView() ) )->register();
		$this->gate->register();
		$this->windpress->register();
		$this->compare->register();
		$this->library->register();
		$this->account->register();
		$this->blog->register();
		add_action( 'wp_enqueue_scripts', array( $this, 'enqueue_product_scripts' ) );
		add_action( 'wp_enqueue_scripts', array( $this, 'enqueue_account_scripts' ) );
	}

	/**
	 * The account chain's interaction layer (ticket #184): the submit state and
	 * the two-field password check of the guest cards, the gates and the
	 * workspace forms. The strength meter is WooCommerce's own
	 * (wc-password-strength-meter), which Woo enqueues on the pages that carry
	 * a password field. Only the account chain loads this file.
	 */
	public function enqueue_account_scripts(): void {
		$is_chain = ( function_exists( 'is_account_page' ) && is_account_page() )
			|| ( function_exists( 'is_checkout' ) && is_checkout() );
		if ( ! $is_chain ) {
			return;
		}
		$base = plugins_url( 'assets/', dirname( __DIR__, 2 ) . '/linker-commerce.php' );
		wp_enqueue_script( 'linker-account-ui', $base . 'account-ui.js', array(), (string) filemtime( dirname( __DIR__, 2 ) . '/assets/account-ui.js' ), true );
	}

	/**
	 * The product page's interaction layer: the gallery viewer, the
	 * specification tabs. The template renders the markup these scripts read;
	 * the styles stay in the WindPress layer. The comparison selection (its
	 * controls and its floating chip) is the comparison page's own module
	 * (ComparePage), which loads on the surfaces that carry either.
	 */
	public function enqueue_product_scripts(): void {
		$base = plugins_url( 'assets/', dirname( __DIR__, 2 ) . '/linker-commerce.php' );
		wp_enqueue_script( 'linker-header-menu', $base . 'header-menu.js', array(), (string) filemtime( dirname( __DIR__, 2 ) . '/assets/header-menu.js' ), true );
		if ( function_exists( 'is_shop' ) && ( is_shop() || is_product_taxonomy() ) ) {
			// The catalogue's family cards: the model picker switches the
			// article a card shows (spec: the live shop's family grid).
			wp_enqueue_script( 'linker-product-family', $base . 'product-family.js', array(), '1', true );
			// The product archive's filter drawer on the narrow viewports: the open
			// and close state of the rail's panel (spec 82 planned this file
			// as the storefront script's successor; the drawer never had its
			// behaviour on the new tree — recheck 2026-10-14, family 11).
			wp_enqueue_script( 'linker-catalog-ui', $base . 'catalog-ui.js', array(), (string) filemtime( dirname( __DIR__, 2 ) . '/assets/catalog-ui.js' ), true );
		}
		if ( ! function_exists( 'is_product' ) || ! is_product() ) {
			return;
		}
		wp_enqueue_script( 'tv-b2b-pdp-ui', $base . 'pdp-ui.js', array(), '3', true );
	}
}
