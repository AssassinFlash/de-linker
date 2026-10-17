<?php
/**
 * Who sees which price.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Gating;

use Linker\Commerce\Registration\Approval;
use WC_Product;

/**
 * The one rule for prices: a product shows its price to approved partner
 * accounts, unless it is quoted per project. Every surface (product pages, the
 * solution draft, the Store API, Genie's abilities) reads it here. Approval is
 * part of the rule since ticket 73: a pending or restricted account reads the
 * site like a guest.
 */
final class CommerceState {

	/**
	 * Product meta that marks a product as quoted per project. The value
	 * "rfq_only" is the live catalogue's data (1957 GW208.9-BAT-LCD-G10,
	 * docs/research/2026-10-09/old-repo-live-catalogue-facts.md).
	 */
	public const MODE_META = 'tv_b2b_product_mode';

	/**
	 * Value of MODE_META for a product quoted per project.
	 */
	public const RFQ_ONLY = 'rfq_only';

	/**
	 * Why a product shows a text instead of a price.
	 */
	public const LOGIN    = 'login';
	public const PROJECT  = 'project';
	public const UNPRICED = 'unpriced';
	public const APPROVAL = 'approval';

	/**
	 * The surfaces that print a price, each with its own order of reasons
	 * (see reason()).
	 */
	public const CARD = 'card';
	public const PAGE = 'page';

	/**
	 * Sets up the state.
	 *
	 * @param Approval $approval The account approval rule.
	 */
	public function __construct( private readonly Approval $approval = new Approval() ) {}

	/**
	 * Whether the product is quoted per project; a variation follows its parent,
	 * and a German product its English one (`linker_commerce_facts_product_id`,
	 * answered by linker-i18n): the mode is the English record's, as the
	 * selection facts are, and the solution draft holds the English product
	 * (the German twin of 1957 carries no mode of its own in the live snapshot
	 * of 2026-10-17, and its page showed the price an English page hides).
	 *
	 * @param WC_Product $product Product.
	 */
	public function is_rfq_only( WC_Product $product ): bool {
		$id = $product->get_parent_id() > 0 ? $product->get_parent_id() : $product->get_id();
		/** This filter is documented in includes/Products/SelectionFacts.php */
		$source = (int) apply_filters( 'linker_commerce_facts_product_id', $id );
		return self::RFQ_ONLY === get_post_meta( $source > 0 ? $source : $id, self::MODE_META, true );
	}

	/**
	 * Whether the visitor sees prices at all: approved partner accounts do,
	 * guests and accounts without approval do not (docs/specs/11-commerce.md,
	 * journey steps 1 and 3, approval). Every price surface asks this.
	 */
	public function visitor_sees_prices(): bool {
		return is_user_logged_in() && $this->approval->sees_prices( get_current_user_id() );
	}

	/**
	 * Why the visitor without prices shows a text: a guest reads "log in", a
	 * signed-in account without approval reads its own state.
	 *
	 * @return self::LOGIN|self::APPROVAL
	 */
	public function visitor_reason(): string {
		return is_user_logged_in() ? self::APPROVAL : self::LOGIN;
	}

	/**
	 * The current visitor's approval state, for the texts that name it (the
	 * price note distinguishes pending from restricted).
	 */
	public function current_approval_status(): string {
		return $this->approval->status( get_current_user_id() );
	}

	/**
	 * Whether the current visitor sees the product's stored price.
	 *
	 * @param WC_Product $product Product.
	 */
	public function shows_price( WC_Product $product ): bool {
		return $this->visitor_sees_prices() && ! $this->is_rfq_only( $product );
	}

	/**
	 * Why a product shows a text instead of its price on a surface, or null
	 * when it shows the price. The two surfaces ask in different orders, each
	 * as the live site shows it:
	 *
	 * - CARD — WooCommerce's own price HTML (`woocommerce_empty_price_html`:
	 *   Woo's loops and the Store API's `price_html`), the solution draft's and
	 *   the inquiry's lines, the draft summary: the product before the account.
	 *   Live 2026-10-18: a guest's `/wc/store/v1/products/1957` answers
	 *   `price_html` "Quoted per project".
	 * - PAGE — the product page, the comparison page and Genie's product card
	 *   (#242): the account before the product. Live 2026-10-18: the guest's
	 *   product page of 1957 reads "Net price after partner sign-in".
	 *
	 * Either way an approved account on a priced product sees the price, and
	 * on a product without a stored price reads "on request".
	 *
	 * @param WC_Product $product Product.
	 * @param string     $surface self::CARD or self::PAGE.
	 * @return self::LOGIN|self::APPROVAL|self::PROJECT|self::UNPRICED|null
	 * @throws \InvalidArgumentException For a surface the rule does not know.
	 */
	public function reason( WC_Product $product, string $surface ): ?string {
		if ( self::CARD !== $surface && self::PAGE !== $surface ) {
			throw new \InvalidArgumentException( 'Unknown price surface.' );
		}
		$account = $this->visitor_sees_prices() ? null : $this->visitor_reason();
		$project = $this->is_rfq_only( $product ) ? self::PROJECT : null;
		$first   = self::CARD === $surface ? ( $project ?? $account ) : ( $account ?? $project );
		if ( null !== $first ) {
			return $first;
		}
		return '' === (string) $product->get_price( 'edit' ) ? self::UNPRICED : null;
	}
}
