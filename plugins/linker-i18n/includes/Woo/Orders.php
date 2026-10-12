<?php
/**
 * The language of an order and of its emails.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Woo;

use Linker\I18n\Languages;

/**
 * Stores the language an order was placed in and sends the order's customer
 * emails in it, whoever triggers them: the checkout, a status change in the
 * admin screens, a scheduled job. Emails to the shop's own staff are sent in
 * the site's language, English.
 *
 * WooCommerce switches a customer email to the site locale and has no notion
 * of an order language (`WC_Email::setup_locale()`); its German (Formal)
 * language pack, de_DE_formal, gives the Sie form
 * (docs/research/2026-10-09/i18n-opensource-replication.md §9).
 */
final class Orders {

	/**
	 * Order meta holding the language slug.
	 */
	public const LANGUAGE = '_linker_i18n_language';

	/**
	 * Order meta holding a WordPress locale, written by linker-commerce's
	 * inquiry flow (OrderLocale::META) since #11. The fallback source of
	 * {@see self::language_of()} for orders that predate this plugin's own
	 * record; the slug meta is the authority.
	 */
	public const LEGACY_LOCALE = '_linker_locale';

	/**
	 * One entry per email notification being sent: the order's language and
	 * whether entering it switched the locale.
	 *
	 * @var list<array{language: string|null, switched: array{bool, mixed, string}}>
	 */
	private array $notifications = array();

	/**
	 * One entry per customer email being rendered: what switching to the
	 * order's language changed, and the country list it replaced.
	 *
	 * @var list<array{array{bool, mixed, string}, \WC_Countries}>
	 */
	private array $customer_emails = array();

	/**
	 * The email WooCommerce is setting up or restoring the locale for.
	 *
	 * @var \WC_Email|null
	 */
	private ?\WC_Email $email = null;

	/**
	 * Sets up the order filters.
	 *
	 * @param Languages $languages The site's languages.
	 */
	public function __construct( private readonly Languages $languages ) {}

	/**
	 * Records the language of the request on a new order (actions
	 * `woocommerce_checkout_create_order` and
	 * `woocommerce_store_api_checkout_update_order_meta`).
	 *
	 * The checkout form's own `lang` field is read first: it posts by AJAX to
	 * an address without the language's URL prefix (?wc-ajax=checkout), where
	 * Polylang answers with the default language and a German inquiry was
	 * recorded as English (#9, found in #11's replay). The Store API names the
	 * language in its URL, which {@see \Linker\I18n\Languages::current()}
	 * resolves; a posted value wins only when it names a language of the site.
	 *
	 * @param \WC_Order $order The order.
	 */
	public function record( \WC_Order $order ): void {
		// The checkout POST carries WooCommerce's checkout nonce, verified before any order is created.
		// phpcs:ignore WordPress.Security.NonceVerification.Missing
		$posted   = isset( $_POST['lang'] ) && is_string( $_POST['lang'] ) ? sanitize_key( wp_unslash( $_POST['lang'] ) ) : '';
		$language = '' !== $posted && $this->languages->exists( $posted ) ? $posted : $this->languages->current();
		$order->update_meta_data( self::LANGUAGE, $language );
	}

	/**
	 * The language an order was placed in; English for orders without one.
	 *
	 * Orders that linker-commerce recorded before this plugin's meta existed
	 * carry a locale instead (#11's `_linker_locale`); their language is read
	 * from it so both metas answer the same. The slug meta is the authority:
	 * every read goes through this one method.
	 *
	 * @param \WC_Order $order The order.
	 */
	public function language_of( \WC_Order $order ): string {
		$language = $order->get_meta( self::LANGUAGE );
		if ( is_string( $language ) && $this->languages->exists( $language ) ) {
			return $language;
		}
		$locale = $order->get_meta( self::LEGACY_LOCALE );
		if ( is_string( $locale ) && '' !== $locale ) {
			$language = $this->languages->slug_of_locale( $locale );
			if ( null !== $language ) {
				return $language;
			}
		}
		return Languages::SOURCE;
	}

	/**
	 * Wraps every email notification WooCommerce sends (filter
	 * `woocommerce_email_actions`) between {@see self::open()} and
	 * {@see self::close()}.
	 *
	 * @param array<int, string> $actions Actions that send emails.
	 * @return array<int, string>
	 */
	public function notifications( array $actions ): array {
		foreach ( $actions as $action ) {
			if ( ! has_action( $action . '_notification', array( $this, 'open' ) ) ) {
				add_action( $action . '_notification', array( $this, 'open' ), 1, 2 );
				add_action( $action . '_notification', array( $this, 'close' ), PHP_INT_MAX, 0 );
			}
		}
		return $actions;
	}

	/**
	 * Starts a notification in the site's language and notes the order's.
	 *
	 * @param mixed $subject First argument of the notification: an order ID, an order, or an array with `order_id`.
	 * @param mixed $order   Second argument: the order, for status changes.
	 */
	public function open( $subject = null, $order = null ): void {
		$found = $order instanceof \WC_Order ? $order : $this->order( $subject );

		$this->notifications[] = array(
			'language' => null === $found ? null : $this->language_of( $found ),
			'switched' => $this->languages->enter( Languages::SOURCE ),
		);
	}

	/**
	 * Ends the innermost notification.
	 */
	public function close(): void {
		$notification = array_pop( $this->notifications );
		if ( null !== $notification ) {
			$this->languages->leave( $notification['switched'] );
		}
	}

	/**
	 * Notes which email is about to switch or restore its locale (filter
	 * `woocommerce_allow_switching_email_locale`, applied just before
	 * `woocommerce_email_setup_locale` and `woocommerce_email_restore_locale`).
	 *
	 * @param mixed $allow Whether the email may switch its locale.
	 * @param mixed $email The email.
	 * @return mixed
	 */
	public function email( $allow, $email ) {
		$this->email = $email instanceof \WC_Email ? $email : null;
		return $allow;
	}

	/**
	 * Renders a customer email in the order's language instead of the site
	 * locale WooCommerce would pick (filter `woocommerce_email_setup_locale`).
	 *
	 * @param mixed $switches Whether WooCommerce switches to the site locale.
	 * @return mixed
	 */
	public function setup_customer_email( $switches ) {
		$notification = array() === $this->notifications ? null : $this->notifications[ array_key_last( $this->notifications ) ];
		if ( null === $notification || null === $notification['language'] ) {
			return $switches;
		}
		$this->customer_emails[] = array( $this->languages->enter( $notification['language'] ), WC()->countries );
		$this->reload_texts( new \WC_Countries() );
		return false;
	}

	/**
	 * Restores the language after a customer email (filter
	 * `woocommerce_email_restore_locale`).
	 *
	 * @param mixed $restore Whether WooCommerce restores the locale.
	 * @return mixed
	 */
	public function restore_customer_email( $restore ) {
		$frame = array_pop( $this->customer_emails );
		if ( null === $frame ) {
			return $restore;
		}
		$this->languages->leave( $frame[0] );
		$this->reload_texts( $frame[1] );
		return false;
	}

	/**
	 * Makes the texts WooCommerce read before the switch follow the new
	 * language: the email's settings, whose defaults (the closing line) were
	 * translated when the mailer was built, and the country names, which
	 * WooCommerce keeps once loaded.
	 *
	 * @param \WC_Countries $countries The country list to use.
	 */
	private function reload_texts( \WC_Countries $countries ): void {
		WC()->countries = $countries;
		if ( null !== $this->email ) {
			$this->email->init_form_fields();
			$this->email->init_settings();
		}
	}

	/**
	 * The order a notification is about.
	 *
	 * @param mixed $subject Order ID, order, or array with `order_id`.
	 */
	private function order( $subject ): ?\WC_Order {
		if ( is_array( $subject ) && isset( $subject['order_id'] ) ) {
			$subject = $subject['order_id'];
		}
		if ( $subject instanceof \WC_Order ) {
			return $subject;
		}
		if ( ! is_numeric( $subject ) ) {
			return null;
		}
		$order = wc_get_order( (int) $subject );
		return $order instanceof \WC_Order ? $order : null;
	}
}
