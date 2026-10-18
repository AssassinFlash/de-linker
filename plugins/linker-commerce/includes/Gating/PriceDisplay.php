<?php
/**
 * Prices hidden at their source, texts where a price would be.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Gating;

use WC_Order;
use WC_Order_Item;
use WC_Order_Item_Product;
use WC_Product;
use Linker\Commerce\Registration\Approval;

/**
 * Applies CommerceState: a product whose price the visitor may not see has no
 * price at all in that request (so no template, widget, feed or API can print
 * it), stays addable to the solution draft, and shows a text instead:
 * "Log in for prices", a note about the account's approval, "Quoted per
 * project" or "Price on request".
 */
final class PriceDisplay {

	/**
	 * Order item meta recording that a line had no price when the inquiry was
	 * sent, so the inquiry shows the text instead of 0 until staff set a price.
	 */
	public const ITEM_REASON_META = '_linker_price_reason';

	/**
	 * Sets up the display.
	 *
	 * @param CommerceState $state The price rule.
	 */
	public function __construct( private readonly CommerceState $state ) {}

	/**
	 * A price the visitor may see, otherwise ''. Runs on the price getters of
	 * products and variations (view context only; saving reads the edit context).
	 *
	 * @param mixed      $price   Stored price.
	 * @param WC_Product $product Product.
	 * @return mixed
	 */
	public function price( $price, WC_Product $product ) {
		return $this->state->shows_price( $product ) ? $price : '';
	}

	/**
	 * Whether the current visitor sees prices: the one answer to the filter
	 * `linker_commerce_visitor_sees_prices`, for plugins that must ask this
	 * question without a rule of their own (linker-tools' Genie shell tells
	 * its service whether the account is approved, #242). This callback is the
	 * single authority on that filter: it answers with CommerceState and does
	 * not read the value the filter is applied with.
	 */
	public function sees_prices(): bool {
		return $this->state->visitor_sees_prices();
	}

	/**
	 * The variation price cache must differ between visitors who see prices and
	 * those who do not.
	 *
	 * @param array<int|string, mixed> $hash Parts of the cache key.
	 * @return array<int|string, mixed>
	 */
	public function variation_prices_hash( array $hash ): array {
		$hash['linker_prices_visible'] = $this->state->visitor_sees_prices();
		return $hash;
	}

	/**
	 * A product without a visible price can still be added to the solution
	 * draft: WooCommerce refuses products with an empty price, the inquiry asks
	 * for exactly those.
	 *
	 * @param bool       $purchasable WooCommerce's verdict.
	 * @param WC_Product $product     Product.
	 */
	public function purchasable( bool $purchasable, WC_Product $product ): bool {
		if ( $purchasable || ! $product->exists() || ! $product->is_type( array( 'simple', 'variation' ) ) ) {
			return $purchasable;
		}
		$owner_id = $product->get_parent_id() > 0 ? $product->get_parent_id() : $product->get_id();
		return 'publish' === get_post_status( $owner_id ) || current_user_can( 'edit_post', $owner_id );
	}

	/**
	 * The text shown where a product's price would be; runs on woocommerce_empty_price_html.
	 *
	 * @param string     $html    WooCommerce's text for an empty price.
	 * @param WC_Product $product Product.
	 */
	public function empty_price_html( string $html, WC_Product $product ): string {
		$reason = $this->state->reason( $product, CommerceState::CARD );
		return null === $reason ? $html : $this->label( $reason );
	}

	/**
	 * Price and subtotal cells of a solution draft line.
	 *
	 * @param string              $html      WooCommerce's price or subtotal HTML.
	 * @param array<string,mixed> $cart_item Cart line.
	 */
	public function cart_item_price( string $html, array $cart_item ): string {
		$product = $cart_item['data'] ?? null;
		if ( ! $product instanceof WC_Product ) {
			return $html;
		}
		$reason = $this->state->reason( $product, CommerceState::CARD );
		return null === $reason ? $html : $this->label( $reason );
	}

	/**
	 * The solution draft's subtotal where a theme shows it (the header, the
	 * mini draft): a visitor without prices has no prices to add up, so
	 * instead of 0 it says what opens them. Plain text, as themes print it
	 * inside their own link to the draft: only the approval note carries its
	 * own markup, the guest's text stays unlinked (the theme's link around the
	 * subtotal is already there, and a link inside a link is not valid HTML).
	 *
	 * @param string $subtotal Formatted subtotal.
	 */
	public function cart_subtotal( string $subtotal ): string {
		if ( $this->state->visitor_sees_prices() ) {
			return $subtotal;
		}
		$reason = $this->state->visitor_reason();
		if ( CommerceState::APPROVAL === $reason ) {
			return $this->label( $reason );
		}
		return '<span class="linker-price-note">' . $this->reason_text( $reason ) . '</span>';
	}

	/**
	 * Remembers on each inquiry line why it had no price.
	 *
	 * @param WC_Order_Item_Product $item      The order line being created.
	 * @param string                $cart_key  Cart line key.
	 * @param array<string,mixed>   $cart_item Cart line.
	 */
	public function remember_line_reason( WC_Order_Item_Product $item, string $cart_key, array $cart_item ): void {
		$product = $cart_item['data'] ?? null;
		if ( $product instanceof WC_Product ) {
			$reason = $this->state->reason( $product, CommerceState::CARD );
			if ( null !== $reason ) {
				$item->add_meta_data( self::ITEM_REASON_META, $reason, true );
			}
		}
	}

	/**
	 * An inquiry line sent without a price shows the text until staff set one.
	 *
	 * @param string        $subtotal Formatted line subtotal.
	 * @param WC_Order_Item $item     Order line.
	 */
	public function order_line_subtotal( string $subtotal, WC_Order_Item $item ): string {
		$reason = $item->get_meta( self::ITEM_REASON_META );
		if ( ! $item instanceof WC_Order_Item_Product || ! is_string( $reason ) || '' === $reason || 0.0 !== (float) $item->get_total() ) {
			return $subtotal;
		}
		return $this->label( $reason );
	}

	/**
	 * Keeps the reason a line was sent without a price out of the inquiry
	 * screen's line details: it is bookkeeping for order_line_subtotal() and
	 * has_unpriced_lines(), and staff see the missing price as the line's 0.
	 *
	 * @param string[] $keys Item meta keys WooCommerce does not show.
	 * @return string[]
	 */
	public function hidden_item_meta( array $keys ): array {
		$keys[] = self::ITEM_REASON_META;
		return $keys;
	}

	/**
	 * Whether an inquiry has lines that are still without a price.
	 *
	 * @param WC_Order $order Order.
	 */
	public function has_unpriced_lines( WC_Order $order ): bool {
		foreach ( $order->get_items() as $item ) {
			if ( $item instanceof WC_Order_Item_Product && '' !== $item->get_meta( self::ITEM_REASON_META ) && 0.0 === (float) $item->get_total() ) {
				return true;
			}
		}
		return false;
	}

	/**
	 * A quote with missing prices, or a contact message, has no monetary total.
	 *
	 * @param array<string, array{label: string, value: string}> $totals Woo totals.
	 * @param WC_Order                                           $order Inquiry.
	 * @return array<string, array{label: string, value: string}>
	 */
	public function order_totals( array $totals, WC_Order $order ): array {
		return 0 === $order->get_item_count() || $this->has_unpriced_lines( $order ) || 'contact' === $order->get_meta( '_linker_inquiry_source' ) ? array() : $totals;
	}

	/**
	 * The text for a reason, escaped, without any markup: the one place each
	 * reason's words come from, so label() and the draft's subtotal cannot
	 * drift apart.
	 *
	 * @param string $reason One of the CommerceState reasons.
	 */
	public function reason_text( string $reason ): string {
		if ( CommerceState::LOGIN === $reason ) {
			return esc_html__( 'Log in for prices', 'linker-commerce' );
		}
		if ( CommerceState::APPROVAL === $reason ) {
			$status = $this->state->current_approval_status();
			// An inquiry can retain its original approval reason after approval;
			// its unset line price then needs the neutral request wording.
			if ( Approval::APPROVED === $status ) {
				return $this->reason_text( CommerceState::UNPRICED );
			}
			$text   = Approval::PENDING !== $status
				? __( 'Not available for your account', 'linker-commerce' )
				: __( 'Account under review. Prices after approval.', 'linker-commerce' );
			return esc_html( $text );
		}
		$text = CommerceState::PROJECT === $reason
			? __( 'Quoted per project', 'linker-commerce' )
			: __( 'Price on request', 'linker-commerce' );
		return esc_html( $text );
	}

	/**
	 * The text for a reason; runs on woocommerce_empty_price_html and the cart
	 * cells. The guest's text links to the account page, every other text is a
	 * plain note.
	 *
	 * @param string $reason One of the CommerceState reasons.
	 */
	public function label( string $reason ): string {
		if ( CommerceState::LOGIN === $reason ) {
			return sprintf(
				'<a class="linker-price-login" href="%1$s">%2$s</a>',
				esc_url( wc_get_page_permalink( 'myaccount' ) ),
				$this->reason_text( $reason )
			);
		}
		return '<span class="linker-price-note">' . $this->reason_text( $reason ) . '</span>';
	}
}
