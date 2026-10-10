<?php
/**
 * The site's words for WooCommerce's.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Vocabulary;

/**
 * WooCommerce's customer-facing strings that speak of carts, orders, checkout,
 * payment or shipping, and what this site says instead (AGENTS.md §3: Solution
 * draft / Lösungsentwurf, Inquiry / Anfrage, Proforma invoice /
 * Proformarechnung; docs/specs/11-commerce.md, Vocabulary). Each replacement is
 * a string of this plugin, translated in its .po files; each key is
 * WooCommerce 11.1.0's source string, character for character.
 */
final class Terms {

	/**
	 * Replacements of singular strings, in the current language.
	 *
	 * @return array<string, string> WooCommerce source string → replacement.
	 */
	public function singular(): array {
		return array(
			// The solution draft (WooCommerce's cart).
			'Cart totals'                                  => __( 'Totals', 'linker-commerce' ),
			'Update cart'                                  => __( 'Update solution draft', 'linker-commerce' ),
			'Proceed to checkout'                          => __( 'Continue to Proforma request', 'linker-commerce' ),
			/* translators: %s: product name. */
			'Remove %s from cart'                          => __( 'Remove %s from the solution draft', 'linker-commerce' ),
			'Cart updated.'                                => __( 'Solution draft updated.', 'linker-commerce' ),
			'Your cart is currently empty.'                => __( 'Your solution draft is empty.', 'linker-commerce' ),
			'Return to shop'                               => __( 'Browse products', 'linker-commerce' ),
			'View cart'                                    => __( 'View solution draft', 'linker-commerce' ),
			'Checkout'                                     => __( 'Proforma request', 'linker-commerce' ),
			'No products in the cart.'                     => __( 'No products in the solution draft.', 'linker-commerce' ),
			'Return to cart'                               => __( 'Back to the solution draft', 'linker-commerce' ),
			'Add to cart'                                  => __( 'Add to solution draft', 'linker-commerce' ),
			/* translators: %s: product name. */
			'Add to cart: &ldquo;%s&rdquo;'                => __( 'Add to solution draft: &ldquo;%s&rdquo;', 'linker-commerce' ),
			/* translators: %s: product name. */
			'&ldquo;%s&rdquo; has been added to your cart' => __( '&ldquo;%s&rdquo; has been added to your solution draft', 'linker-commerce' ),
			/* translators: %s: product name. */
			'&ldquo;%s&rdquo; has been removed from your cart' => __( '&ldquo;%s&rdquo; has been removed from your solution draft', 'linker-commerce' ),
			'An item which is no longer available was removed from your cart.' => __( 'A product that is no longer available was removed from your solution draft.', 'linker-commerce' ),
			/* translators: %s: product name. */
			'%s has been removed from your cart because it can no longer be purchased. Please contact us if you need assistance.' => __( '%s has been removed from your solution draft because it is no longer available. Please contact us if you need help.', 'linker-commerce' ),
			/* translators: 1: product name, 2: link that adds it again. */
			'%1$s has been removed from your cart because it has since been modified. You can add it back to your cart <a href="%2$s">here</a>.' => __( '%1$s has been removed from your solution draft because the product has changed since you added it. You can <a href="%2$s">add it again</a>.', 'linker-commerce' ),
			'The cart has been filled with the items from your previous order.' => __( 'Your solution draft has been replaced with the products of the earlier inquiry.', 'linker-commerce' ),
			'Please choose a product to add to your cart&hellip;' => __( 'Please choose a product to add to your solution draft&hellip;', 'linker-commerce' ),
			'Please choose the quantity of items you wish to add to your cart&hellip;' => __( 'Please choose the quantity you want to add to your solution draft&hellip;', 'linker-commerce' ),
			/* translators: %s: product name. */
			'You can only have 1 %s in your cart.'         => __( 'Your solution draft can hold only one %s.', 'linker-commerce' ),
			/* translators: %s: product name. */
			'You cannot add another "%s" to your cart.'    => __( 'You cannot add another &ldquo;%s&rdquo; to your solution draft.', 'linker-commerce' ),
			/* translators: %s: product name. */
			'You cannot add &quot;%s&quot; to the cart because the product is out of stock.' => __( '&ldquo;%s&rdquo; is not available at the moment and cannot be added to the solution draft.', 'linker-commerce' ),
			'There are some issues with the items in your cart. Please go back to the cart page and resolve these issues before checking out.' => __( 'Some products in your solution draft need checking. Please go back to the solution draft before you request a Proforma invoice.', 'linker-commerce' ),
			'Quantity'                                     => __( 'Quantity', 'linker-commerce' ),

			// Products (AGENTS.md §2, 2026-10-05: Product / Model / Series, never "article").
			'Shop order'                                   => __( 'Sort products', 'linker-commerce' ),
			// WooCommerce's German pack mixes "sortiert" and "sortieren" in the sort options; this one joins the others.
			'Sort by popularity'                           => __( 'Sort by popularity', 'linker-commerce' ),
			'SKU:'                                         => __( 'Product no.:', 'linker-commerce' ),
			'Remove item'                                  => __( 'Remove product', 'linker-commerce' ),

			// The Proforma request page (WooCommerce's checkout).
			'Payment methods'                              => __( 'Proforma invoice', 'linker-commerce' ),
			'If you have shopped with us before, please enter your details below. If you are a new customer, please proceed to the Billing section.' => __( 'Log in with your account.', 'linker-commerce' ),
			'Returning customer?'                          => __( 'Already have an account?', 'linker-commerce' ),
			'Click here to login'                          => __( 'Log in', 'linker-commerce' ),
			'Login'                                        => __( 'Log in', 'linker-commerce' ),
			// WooCommerce's German pack names the form "Neues Kundenkonto anlegen" while every link to it says "Registrieren".
			'Register'                                     => __( 'Register', 'linker-commerce' ),
			'Billing details'                              => __( 'Company details', 'linker-commerce' ),
			'Order notes'                                  => __( 'Notes', 'linker-commerce' ),
			'Notes about your order, e.g. special notes for delivery.' => __( 'Notes on your inquiry, e.g. your project name.', 'linker-commerce' ),
			'Note:'                                        => __( 'Notes:', 'linker-commerce' ),
			// The emails' heading of the same field ("Kundenhinweis" in WooCommerce's German pack).
			'Customer note'                                => __( 'Notes', 'linker-commerce' ),
			'Your order'                                   => __( 'Your inquiry', 'linker-commerce' ),
			'Place order'                                  => __( 'Request Proforma', 'linker-commerce' ),
			'You must be logged in to checkout.'           => __( 'Please log in to request a Proforma invoice. No account yet? Register on the account page.', 'linker-commerce' ),
			'Please read and accept the terms and conditions to proceed with your order.' => __( 'Please read and accept the terms and conditions to send your inquiry.', 'linker-commerce' ),
			'We were unable to process your order, please try again.' => __( 'Your inquiry could not be sent. Please try again.', 'linker-commerce' ),
			'Unable to create order.'                      => __( 'Your inquiry could not be saved. Please try again.', 'linker-commerce' ),
			'Invalid payment method.'                      => __( 'Your inquiry could not be sent. Please reload the page and try again.', 'linker-commerce' ),
			'Sorry, it seems that there are no available payment methods. Please contact us if you require assistance or wish to make alternate arrangements.' => __( 'An inquiry cannot be sent at the moment. Please contact us.', 'linker-commerce' ),
			'Please fill in your details above to see available payment methods.' => __( 'Please fill in your details above.', 'linker-commerce' ),
			/* translators: 1: opening tag of the button, 2: closing tag. */
			'Since your browser does not support JavaScript, or it is disabled, please ensure you click the %1$sUpdate Totals%2$s button before placing your order. You may be charged more than the amount stated above if you fail to do so.' => __( 'Your browser does not run JavaScript. Please click %1$sUpdate totals%2$s before sending your inquiry, so that the totals above are up to date.', 'linker-commerce' ),
			/* translators: %s: link to the inquiries in the account. */
			'There was an error processing your order. Please check for any charges in your payment method and review your <a href="%s">order history</a> before placing the order again.' => __( 'Your inquiry could not be sent. Please check your <a href="%s">inquiries</a> before sending it again.', 'linker-commerce' ),
			'The order totals have been updated. Please confirm your order by pressing the "Place order" button at the bottom of the page.' => __( 'The totals have been updated. Please confirm your inquiry with the &ldquo;Request Proforma&rdquo; button at the bottom of the page.', 'linker-commerce' ),

			// The confirmation, the inquiry pages and the account.
			'Thank you. Your order has been received.'     => __( 'Thank you. Your inquiry has been received.', 'linker-commerce' ),
			// The confirmation link of the email a guest opens: WooCommerce asks for a login naming the order.
			'Please log in to your account to view this order.' => __( 'Please log in to your account to view this inquiry.', 'linker-commerce' ),
			'Order received'                               => __( 'Inquiry received', 'linker-commerce' ),
			'Order number:'                                => __( 'Inquiry no.:', 'linker-commerce' ),
			'Order details'                                => __( 'Inquiry details', 'linker-commerce' ),
			'Order again'                                  => __( 'Request again', 'linker-commerce' ),
			/* translators: 1: inquiry number, 2: date, 3: status. */
			'Order #%1$s was placed on %2$s and is currently %3$s.' => __( 'Inquiry #%1$s was sent on %2$s. Status: %3$s.', 'linker-commerce' ),
			'Order updates'                                => __( 'Updates', 'linker-commerce' ),
			/* translators: %s: inquiry number. */
			'Order #%s'                                    => __( 'Inquiry #%s', 'linker-commerce' ),
			'Orders'                                       => __( 'Inquiries', 'linker-commerce' ),
			/* translators: %d: page number. */
			'Orders (page %d)'                             => __( 'Inquiries (page %d)', 'linker-commerce' ),
			'No order has been made yet.'                  => __( 'You have not sent an inquiry yet.', 'linker-commerce' ),
			/* translators: %s: inquiry number. */
			'View order %s'                                => __( 'View inquiry %s', 'linker-commerce' ),
			/* translators: %s: inquiry number. */
			'View order number %s'                         => __( 'View inquiry number %s', 'linker-commerce' ),
			/* translators: 1: "View" or a similar word, 2: inquiry number. */
			'%1$s order number %2$s'                       => __( '%1$s: inquiry number %2$s', 'linker-commerce' ),
			'Billing address'                              => __( 'Company details', 'linker-commerce' ),
			'The following addresses will be used on the checkout page by default.' => __( 'These details are pre-filled on the Proforma request page.', 'linker-commerce' ),
			'Save address'                                 => __( 'Save company details', 'linker-commerce' ),
			/* translators: 1: link to the inquiries, 2: link to the company details, 3: link to the account details. */
			'From your account dashboard you can view your <a href="%1$s">recent orders</a>, manage your <a href="%2$s">billing address</a>, and <a href="%3$s">edit your password and account details</a>.' => __( 'In your account you can follow your <a href="%1$s">inquiries</a>, keep your <a href="%2$s">company details</a> up to date and <a href="%3$s">change your password and account details</a>.', 'linker-commerce' ),
			/* translators: 1: link to the inquiries, 2: link to the company details, 3: link to the account details. */
			'From your account dashboard you can view your <a href="%1$s">recent orders</a>, manage your <a href="%2$s">shipping and billing addresses</a>, and <a href="%3$s">edit your password and account details</a>.' => __( 'In your account you can follow your <a href="%1$s">inquiries</a>, keep your <a href="%2$s">company details</a> up to date and <a href="%3$s">change your password and account details</a>.', 'linker-commerce' ),

			// Emails.
			'You can access your account area to view orders, change your password, and more via the link below:' => __( 'In your account you can follow your inquiries and change your password:', 'linker-commerce' ),
			/* translators: 1: site name, 2: username, 3: link to the account. The sentence follows the salutation "Hi %s,". */
			'Thanks for creating an account on %1$s. Your username is %2$s. You can access your account area to view orders, change your password, and more at: %3$s' => __( 'Thank you for creating an account on %1$s. Your username is %2$s. In your account you can follow your inquiries and change your password: %3$s', 'linker-commerce' ),
			/* translators: %s: inquiry number. */
			'[Order #%s]'                                  => __( '[Inquiry #%s]', 'linker-commerce' ),
			'Order summary'                                => __( 'Inquiry summary', 'linker-commerce' ),
		);
	}

	/**
	 * Replacements of strings with a context, in the current language.
	 *
	 * @return array<string, string> Context, "\004", source string → replacement.
	 */
	public function with_context(): array {
		return array();
	}

	/**
	 * Replacements of plural strings.
	 *
	 * @return array<string, array<int|string, mixed>> WooCommerce singular source → nooped plural of this plugin.
	 */
	public function plural(): array {
		return array(
			/* translators: %s: product names. */
			'%s has been added to your cart.' => _n_noop( '%s has been added to your solution draft.', '%s have been added to your solution draft.', 'linker-commerce' ),
			/* translators: %d: number of products. */
			'%d item from your previous order is currently unavailable and could not be added to your cart.' => _n_noop( '%d product of the earlier inquiry is not available and could not be added to your solution draft.', '%d products of the earlier inquiry are not available and could not be added to your solution draft.', 'linker-commerce' ),
			/* translators: 1: amount, 2: number of units (quantities added up). */
			'%1$s for %2$s item'              => _n_noop( '%1$s (%2$s unit)', '%1$s (%2$s units)', 'linker-commerce' ),
		);
	}
}
