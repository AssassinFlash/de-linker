<?php
/**
 * Issuing a Proforma invoice.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Proforma;

use DateTimeImmutable;
use Linker\Commerce\Gating\PriceDisplay;
use Linker\Commerce\Inquiry\OrderLocale;
use Linker\Commerce\Inquiry\Statuses;
use Linker\Commerce\Mail\LocaleSwitch;
use Linker\Commerce\Settings\Options;
use Linker\Commerce\Account\PrivateFiles;
use RuntimeException;
use WC_Order;

/**
 * Staff issue a Proforma invoice for a received inquiry with one button: the
 * PDF is rendered in the inquiry's language with the next number, stored, and
 * the inquiry moves to "Proforma invoice issued", which emails the customer a
 * link (docs/specs/11-commerce.md, journey step 5). An inquiry gets one Proforma.
 */
final class Issuer {

	/**
	 * Directory under uploads of the PDFs: wp-content/uploads/proforma/<inquiry>/
	 * (docs/specs/11-commerce.md, module Proforma).
	 */
	public const DIRECTORY = 'proforma';

	/**
	 * Order meta of an issued Proforma.
	 */
	public const NUMBER_META = '_linker_proforma_number';
	public const ISSUED_META = '_linker_proforma_issued';
	public const FILE_META   = '_linker_proforma_file';

	/**
	 * Attempts at a free number when other requests issue at the same moment.
	 */
	private const NUMBER_ATTEMPTS = 5;

	/**
	 * Option prefix of the per-inquiry claim, and how long a claim from a
	 * request that died (fatal error, killed PHP-FPM worker) still counts,
	 * after which the next attempt takes the inquiry over.
	 */
	private const CLAIM_PREFIX = 'linker_proforma_claim_';
	private const CLAIM_STALE  = HOUR_IN_SECONDS;

	/**
	 * Sets up the issuer.
	 *
	 * @param Options      $options  The plugin settings.
	 * @param Sequence     $sequence The numbering.
	 * @param Document     $document The document content.
	 * @param Renderer     $renderer The PDF renderer.
	 * @param PrivateFiles $files    Where the PDFs are kept.
	 * @param PriceDisplay $prices   The price display (lines still without a price).
	 */
	public function __construct(
		private readonly Options $options,
		private readonly Sequence $sequence,
		private readonly Document $document,
		private readonly Renderer $renderer,
		private readonly PrivateFiles $files,
		private readonly PriceDisplay $prices
	) {}

	/**
	 * Why an inquiry cannot get a Proforma now, or '' when it can.
	 *
	 * @param WC_Order $order Inquiry.
	 */
	public function blocker( WC_Order $order ): string {
		if ( '' !== (string) $order->get_meta( self::NUMBER_META ) ) {
			return __( 'This inquiry already has a Proforma invoice.', 'linker-commerce' );
		}
		if ( Statuses::RECEIVED !== $order->get_status() ) {
			return __( 'Only a received inquiry gets a Proforma invoice.', 'linker-commerce' );
		}
		if ( array() === $order->get_items() ) {
			return __( 'The inquiry has no products.', 'linker-commerce' );
		}
		if ( $this->prices->has_unpriced_lines( $order ) ) {
			return __( 'Set a price for every product before issuing the Proforma invoice.', 'linker-commerce' );
		}
		if ( '' === $this->options->bank()['iban'] ) {
			return __( 'Enter the bank account under WooCommerce → Settings → Inquiries before issuing a Proforma invoice.', 'linker-commerce' );
		}
		return '';
	}

	/**
	 * Issues the Proforma invoice of an inquiry.
	 *
	 * @param WC_Order $order Inquiry.
	 * @return string The Proforma number.
	 * @throws RuntimeException When the inquiry cannot get one, or the PDF cannot be stored.
	 */
	public function issue( WC_Order $order ): string {
		$blocker = $this->blocker( $order );
		if ( '' !== $blocker ) {
			throw new RuntimeException( $blocker ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- shown escaped by the caller.
		}
		if ( ! $this->claim( $order->get_id() ) ) {
			// Two staff pressing the button at once: without this, both pass
			// blocker() before either writes the number, and two Proformas with
			// neighbouring numbers and two emails leave (review 2026-10-10).
			throw new RuntimeException( __( 'This inquiry is being issued a Proforma invoice right now; please reload the page in a moment.', 'linker-commerce' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- shown escaped by the caller.
		}
		try {
			return $this->create( $order );
		} finally {
			delete_option( self::CLAIM_PREFIX . $order->get_id() );
		}
	}

	/**
	 * Creates the Proforma invoice; called with the inquiry claimed.
	 *
	 * @param WC_Order $order Inquiry.
	 * @return string The Proforma number.
	 * @throws RuntimeException When no number can be reserved or the PDF cannot be stored.
	 */
	private function create( WC_Order $order ): string {
		// The VAT on the document follows WooCommerce's tax settings for the prices
		// staff set (docs/specs/11-commerce.md, Proforma); a price changed without
		// "Recalculate" would otherwise leave the earlier VAT on the inquiry.
		$order->calculate_totals( true );

		$issued = new DateTimeImmutable( 'now', wp_timezone() );
		$year   = (int) $issued->format( 'Y' );
		for ( $attempt = 0; $attempt < self::NUMBER_ATTEMPTS; ++$attempt ) {
			$next   = $this->sequence->next( $year );
			$number = Sequence::format( $this->options->proforma_prefix(), $year, $next );
			$file   = $this->files->write( $order->get_id(), $number, $this->render( $order, $number, $issued ) );
			if ( $this->sequence->commit( $year, $next ) ) {
				$order->update_meta_data( self::NUMBER_META, $number );
				$order->update_meta_data( self::ISSUED_META, (string) $issued->getTimestamp() );
				$order->update_meta_data( self::FILE_META, $file );
				/* translators: %s: Proforma number. */
				$order->update_status( Statuses::PROFORMA, sprintf( __( 'Proforma invoice %s issued.', 'linker-commerce' ), $number ) );
				return $number;
			}
			// Another request took the number meanwhile; this PDF is discarded.
			$this->files->delete( $file );
		}
		throw new RuntimeException( __( 'No Proforma number could be reserved; please try again.', 'linker-commerce' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- shown escaped by the caller.
	}

	/**
	 * Takes the inquiry's claim, as WordPress's own locks do (WP_Upgrader):
	 * add_option() is atomic on the option table's unique key, so of two
	 * requests only the first inserts. A claim older than CLAIM_STALE belongs
	 * to a dead request and is taken over.
	 *
	 * @param int $order_id Inquiry.
	 */
	private function claim( int $order_id ): bool {
		$claim = self::CLAIM_PREFIX . $order_id;
		$held  = get_option( $claim );
		if ( is_string( $held ) && '' !== $held && time() - (int) $held < self::CLAIM_STALE ) {
			return false;
		}
		if ( false !== $held ) {
			delete_option( $claim );
		}
		return add_option( $claim, (string) time(), '', false );
	}

	/**
	 * The PDF of an inquiry's Proforma, in the inquiry's language.
	 *
	 * @param WC_Order          $order  Inquiry.
	 * @param string            $number Proforma number.
	 * @param DateTimeImmutable $issued Time of issue.
	 */
	private function render( WC_Order $order, string $number, DateTimeImmutable $issued ): string {
		$switch = new LocaleSwitch();
		$switch->to( OrderLocale::of( $order ) );
		try {
			return $this->renderer->pdf( $this->renderer->html( $this->document->data( $order, $number, $issued ) ) );
		} finally {
			$switch->back();
		}
	}
}
