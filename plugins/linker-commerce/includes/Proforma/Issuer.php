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
 *
 * The customer account reads the number and the PDF, not the status word. A
 * status set to "Proforma invoice issued" without those (the order screen's
 * status dropdown) therefore issues the same document, once, on the way in.
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
	/** Durable source index is owned by Issuer even before WC's mailer is loaded. */
	public const NOTICE_PENDING_META = '_linker_proforma_notice_pending';

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
	 * Issues the Proforma of an inquiry that has just been marked issued.
	 *
	 * WooCommerce's order screen can set the status without the Issue button.
	 * The customer account then has a "Proforma invoice issued" inquiry and
	 * nothing to download, because the number and the PDF are written only
	 * here. Called from the status transition, after the status is already
	 * the new one, so the received-status check of issue() does not apply.
	 * One number, one PDF: an inquiry that already has either is left as it is.
	 *
	 * @param int $order_id Inquiry.
	 */
	public function ensure_issued( int $order_id ): void {
		$order = wc_get_order( $order_id );
		if ( ! $order instanceof WC_Order || ! $order->has_status( Statuses::PROFORMA ) ) {
			return;
		}
		if ( '' !== (string) $order->get_meta( self::NUMBER_META ) || '' !== (string) $order->get_meta( self::FILE_META ) ) {
			return;
		}
		$reason = $this->material_blocker( $order );
		if ( '' !== $reason ) {
			$order->add_order_note( $reason );
			$order->save();
			return;
		}
		if ( ! $this->claim( $order->get_id() ) ) {
			return;
		}
		try {
			$this->create( $order, false );
		} catch ( RuntimeException $error ) {
			$order->add_order_note( $error->getMessage() );
			$order->save();
		} finally {
			delete_option( self::CLAIM_PREFIX . $order->get_id() );
		}
	}

	/**
	 * Why an inquiry cannot get a Proforma now, or '' when it can.
	 *
	 * An inquiry that already has a Proforma is refused with that reason before
	 * the received-status rule: issuing moves the inquiry to "Proforma invoice
	 * issued", so a second issue() would otherwise answer with the status error
	 * although "already has one" is the truth. Both errors stay reachable — a
	 * non-received inquiry without a Proforma still gets the status error. The
	 * status rule itself stays: the Issue button is only for a received inquiry,
	 * and a status change into "Proforma invoice issued" is the other way in,
	 * checked by ensure_issued() instead of this rule.
	 *
	 * @param WC_Order $order Inquiry.
	 */
	public function blocker( WC_Order $order ): string {
		if ( '' !== (string) $order->get_meta( self::NUMBER_META ) || '' !== (string) $order->get_meta( self::FILE_META ) ) {
			return __( 'This inquiry already has a Proforma invoice.', 'linker-commerce' );
		}
		if ( Statuses::RECEIVED !== $order->get_status() ) {
			return __( 'Only a received inquiry gets a Proforma invoice.', 'linker-commerce' );
		}
		return $this->material_blocker( $order );
	}

	/**
	 * Why the document itself cannot be built, or '' when it can.
	 *
	 * Shared by the Issue button and a status change into "Proforma invoice
	 * issued": an empty inquiry, a line without a price, or a missing bank
	 * account. The bank account is owner data (WooCommerce → Settings →
	 * Inquiries); it is never invented. An inquiry that already has a Proforma
	 * never reaches these checks: blocker() refuses it first, and
	 * ensure_issued() leaves it alone.
	 *
	 * @param WC_Order $order Inquiry.
	 */
	private function material_blocker( WC_Order $order ): string {
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
	 * @param WC_Order $order       Inquiry.
	 * @param bool     $move_status Whether to move the inquiry to "Proforma invoice issued".
	 *                              False when the status transition already did that.
	 * @return string The Proforma number.
	 * @throws RuntimeException When no number can be reserved or the PDF cannot be stored.
	 */
	private function create( WC_Order $order, bool $move_status = true ): string {
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
				// The issued native source is recoverable before any status listener
				// can interrupt execution; never depend on reaching an email callback.
				$order->update_meta_data( self::NOTICE_PENDING_META, 'yes' );
				$order->update_meta_data( self::NUMBER_META, $number );
				$order->update_meta_data( self::ISSUED_META, (string) $issued->getTimestamp() );
				$order->update_meta_data( self::FILE_META, $file );
				/* translators: %s: Proforma number. */
				$note = sprintf( __( 'Proforma invoice %s issued.', 'linker-commerce' ), $number );
				// The Issue button moves the status, which is what emails the customer.
				// A status that is already issued must be saved, or the number and
				// the PDF exist only in this request and the account still has neither.
				if ( $move_status ) {
					$order->update_status( Statuses::PROFORMA, $note );
				} else {
					$order->add_order_note( $note );
					$order->save();
				}
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
