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
		// The same guard as SelectionFacts::for_product(): without the
		// language layer listening, the product answers itself.
		if ( \function_exists( 'has_filter' ) && has_filter( 'linker_commerce_facts_product_id' ) ) {
			/** This filter is documented in includes/Products/SelectionFacts.php */
			$source = (int) apply_filters( 'linker_commerce_facts_product_id', $id );
			$id     = $source > 0 ? $source : $id;
		}
		return self::RFQ_ONLY === get_post_meta( $id, self::MODE_META, true );
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
	 * Why the product page shows a text instead of the price, or null when it
	 * shows the price. The page decides in its own order: an account without
	 * prices reads its account's reason first (a guest signs in, an account
	 * waiting for approval hears its state), and an approved account reads
	 * "quoted per project" or "on request" where there is no price. Genie's
	 * product cards read the same answer (#242), so a card and its product
	 * page never disagree.
	 *
	 * @param WC_Product $product Product.
	 * @return self::LOGIN|self::APPROVAL|self::PROJECT|self::UNPRICED|null
	 */
	public function page_reason( WC_Product $product ): ?string {
		if ( ! $this->visitor_sees_prices() ) {
			return $this->visitor_reason();
		}
		if ( $this->is_rfq_only( $product ) ) {
			return self::PROJECT;
		}
		return '' === (string) $product->get_price( 'edit' ) ? self::UNPRICED : null;
	}

	/**
	 * Why the product shows a text instead of a price, or null when it shows a price.
	 *
	 * @param WC_Product $product Product.
	 * @return self::LOGIN|self::PROJECT|self::UNPRICED|self::APPROVAL|null
	 */
	public function reason( WC_Product $product ): ?string {
		if ( $this->is_rfq_only( $product ) ) {
			return self::PROJECT;
		}
		if ( ! $this->visitor_sees_prices() ) {
			return $this->visitor_reason();
		}
		return '' === (string) $product->get_price( 'edit' ) ? self::UNPRICED : null;
	}
}
