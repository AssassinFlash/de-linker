<?php
/**
 * Issuing a Quotation.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Quotation;

use DateTimeImmutable;
use Linker\Commerce\Gating\PriceDisplay;
use Linker\Commerce\Inquiry\OrderLocale;
use Linker\Commerce\Inquiry\Statuses;
use Linker\Commerce\Mail\LocaleSwitch;
use Linker\Commerce\Settings\Options;
use Linker\Commerce\Account\PrivateFiles;
use Linker\Commerce\Registration\Approval;
use RuntimeException;
use WC_Order;

/** Issues and revises priced documents in the inquiry's language. */
final class Issuer {

	/**
	 * Directory under uploads of the PDFs: wp-content/uploads/quotation/<inquiry>/
	 * (docs/specs/11-commerce.md, module Quotation).
	 */
	public const DIRECTORY = 'quotation';

	/**
	 * Order meta of an issued Quotation.
	 */
	public const NUMBER_META  = '_linker_quotation_number';
	public const ISSUED_META  = '_linker_quotation_issued';
	public const FILE_META    = '_linker_quotation_file';
	public const HISTORY_META = '_linker_quotation_history';
	/** Durable source index is owned by Issuer even before WC's mailer is loaded. */
	public const NOTICE_PENDING_META = '_linker_quotation_notice_pending';

	/**
	 * Attempts at a free number when other requests issue at the same moment.
	 */
	private const NUMBER_ATTEMPTS = 5;

	/**
	 * Option prefix of the per-inquiry claim, and how long a claim from a
	 * request that died (fatal error, killed PHP-FPM worker) still counts,
	 * after which the next attempt takes the inquiry over.
	 */
	private const CLAIM_PREFIX = 'linker_quotation_claim_';
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
	 * Issues the Quotation of an inquiry that has just been marked issued.
	 *
	 * The status selector and the issue button share the same approval, pricing
	 * and numbering rules. A transition never creates a revision.
	 *
	 * @param int $order_id Inquiry.
	 */
	public function ensure_issued( int $order_id ): void {
		$order = wc_get_order( $order_id );
		if ( ! $order instanceof WC_Order || ! $order->has_status( Statuses::QUOTATION ) ) {
			return;
		}
		if ( '' !== (string) $order->get_meta( self::NUMBER_META ) || '' !== (string) $order->get_meta( self::FILE_META ) ) {
			return;
		}
		try {
			$this->issue( $order );
		} catch ( RuntimeException $error ) {
			$order->add_order_note( $error->getMessage() );
		}
	}

	/**
	 * Why an inquiry cannot get a Quotation now, or '' when it can.
	 *
	 * @param WC_Order $order Inquiry.
	 */
	public function blocker( WC_Order $order ): string {
		if ( '' !== (string) $order->get_meta( self::NUMBER_META ) || '' !== (string) $order->get_meta( self::FILE_META ) ) {
			return __( 'This inquiry already has a Quotation.', 'linker-commerce' );
		}
		if ( ! in_array( $order->get_status(), array( Statuses::RECEIVED, Statuses::QUOTATION ), true ) ) {
			return __( 'Only a received inquiry gets a Quotation.', 'linker-commerce' );
		}
		return $this->material_blocker( $order );
	}

	/**
	 * Why the document itself cannot be built, or '' when it can.
	 *
	 * @param WC_Order $order Inquiry.
	 */
	private function material_blocker( WC_Order $order ): string {
		if ( $order->get_customer_id() > 0 && ( ! ( new Approval() )->sees_prices( $order->get_customer_id() ) || ! get_userdata( $order->get_customer_id() ) ) ) {
			return __( 'Approve this account before issuing its Quotation. The customer needs approval to download the PDF.', 'linker-commerce' );
		}
		if ( array() === $order->get_items() ) {
			return __( 'The inquiry has no products.', 'linker-commerce' );
		}
		if ( $this->prices->has_unpriced_lines( $order ) ) {
			return __( 'Set a price for every product before issuing the Quotation.', 'linker-commerce' );
		}

		return '';
	}

	/**
	 * Issues the Quotation of an inquiry.
	 *
	 * @param WC_Order $order Inquiry.
	 * @return string The Quotation number.
	 * @throws RuntimeException When the inquiry cannot get one, or the PDF cannot be stored.
	 */
	public function issue( WC_Order $order ): string {
		return $this->publish( $order, '' );
	}

	/**
	 * Issue a correction against the version staff actually reviewed.
	 *
	 * @param WC_Order $order Inquiry.
	 * @param string   $previous Number shown on the order screen.
	 * @throws RuntimeException When the reviewed revision has no number.
	 */
	public function revise( WC_Order $order, string $previous ): string {
		if ( '' === $previous ) {
			throw new RuntimeException( __( 'Reload this inquiry to revise its current Quotation.', 'linker-commerce' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Escaped by the order screen.
		}
		return $this->publish( $order, $previous );
	}

	/**
	 * Check all issue conditions while holding the native per-inquiry claim.
	 *
	 * @param WC_Order $order Inquiry.
	 * @param string   $previous Expected revision parent, empty for first issue.
	 * @throws RuntimeException When another issue won or the inquiry is ineligible.
	 */
	private function publish( WC_Order $order, string $previous ): string {
		$order_id = $order->get_id();
		if ( ! $this->claim( $order_id ) ) {
			// Two staff pressing the button at once: without this, both pass
			// blocker() before either writes the number, and two Quotations with
			// neighbouring numbers and two emails leave (review 2026-10-10).
			throw new RuntimeException( __( 'This inquiry is being issued a Quotation right now; please reload the page in a moment.', 'linker-commerce' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- shown escaped by the caller.
		}
		try {
			$order = wc_get_order( $order->get_id() );
			if ( ! $order instanceof WC_Order ) {
				throw new RuntimeException( __( 'Inquiry not found.', 'linker-commerce' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped
			}
			$order->read_meta_data( true );
			$blocker = '' === $previous ? $this->blocker( $order ) : $this->revision_blocker( $order, $previous );
			if ( '' !== $blocker ) {
				throw new RuntimeException( $blocker ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Escaped by the order screen.
			}
			if ( '' !== $previous && 'yes' === $order->get_meta( self::NOTICE_PENDING_META ) ) {
				Notice::notify( $order->get_id() );
				$order = wc_get_order( $order_id );
				if ( ! $order instanceof WC_Order || 'yes' === $order->get_meta( self::NOTICE_PENDING_META ) ) {
					throw new RuntimeException( __( 'The previous Quotation notification is still being queued. Please try again shortly.', 'linker-commerce' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped
				}
			}
			return $this->create( $order, $previous );
		} finally {
			delete_option( self::CLAIM_PREFIX . $order_id );
		}
	}

	/**
	 * Why a correction cannot be issued against this document.
	 *
	 * @param WC_Order $order Inquiry.
	 * @param string   $previous Previously issued number.
	 */
	public function revision_blocker( WC_Order $order, string $previous ): string {
		if ( Statuses::QUOTATION !== $order->get_status() || '' === $previous || $previous !== $order->get_meta( self::NUMBER_META ) || ! $order->get_meta( self::FILE_META ) ) {
			return __( 'Reload this inquiry to revise its current Quotation.', 'linker-commerce' );
		}
		return $this->material_blocker( $order );
	}

	/**
	 * PDF of the saved order. Preview never reserves a number or recalculates the order.
	 *
	 * @param WC_Order $order Inquiry.
	 */
	public function preview( WC_Order $order ): string {
		return $this->render( $order, '', new DateTimeImmutable( 'now', wp_timezone() ) );
	}

	/**
	 * Store the next document while holding the per-inquiry claim.
	 *
	 * @param WC_Order $order Inquiry.
	 * @param string   $previous Previously issued number, empty for the first issue.
	 * @throws RuntimeException When no number can be reserved.
	 */
	private function create( WC_Order $order, string $previous ): string {
		// The VAT on the document follows WooCommerce's tax settings for the prices
		// staff set (docs/specs/11-commerce.md, Quotation); a price changed without
		// "Recalculate" would otherwise leave the earlier VAT on the inquiry.
		$order->calculate_totals( true );

		$issued = new DateTimeImmutable( 'now', wp_timezone() );
		if ( '' !== $previous ) {
			$history   = $order->get_meta( self::HISTORY_META );
			$history   = is_array( $history ) ? $history : array();
			$history[] = array(
				'number' => $previous,
				'issued' => (string) $order->get_meta( self::ISSUED_META ),
				'file'   => (string) $order->get_meta( self::FILE_META ),
			);
			$number    = $history[0]['number'] . '-R' . ( count( $history ) + 1 );
			$file      = $this->files->write( $order->get_id(), $number, $this->render( $order, $number, $issued ) );
			$order->update_meta_data( self::HISTORY_META, $history );
		} else {
			[ $number, $file ] = $this->first_document( $order, $issued );
		}
		$order->update_meta_data( self::NOTICE_PENDING_META, $order->get_customer_id() > 0 ? 'yes' : 'no' );
		$order->update_meta_data( self::NUMBER_META, $number );
		$order->update_meta_data( self::ISSUED_META, (string) $issued->getTimestamp() );
		$order->update_meta_data( self::FILE_META, $file );
		/* translators: %s: Quotation number. */
		$note = sprintf( __( 'Quotation %s issued.', 'linker-commerce' ), $number );
		if ( Statuses::RECEIVED === $order->get_status() ) {
			$order->update_status( Statuses::QUOTATION, $note );
		} else {
			$order->save();
			$order->add_order_note( $note );
			if ( $order->get_customer_id() > 0 ) {
				Notice::notify( $order->get_id() );
			}
		}
		return $number;
	}

	/**
	 * Allocate one annual number for an inquiry's first PDF.
	 *
	 * @param WC_Order          $order Inquiry.
	 * @param DateTimeImmutable $issued Date of issue.
	 * @return array{string,string} Number and private path.
	 * @throws RuntimeException When no number can be reserved.
	 */
	private function first_document( WC_Order $order, DateTimeImmutable $issued ): array {
		$year = (int) $issued->format( 'Y' );
		for ( $attempt = 0; $attempt < self::NUMBER_ATTEMPTS; ++$attempt ) {
			$next   = $this->sequence->next( $year );
			$number = Sequence::format( $this->options->quotation_prefix(), $year, $next );
			$file   = $this->files->write( $order->get_id(), $number, $this->render( $order, $number, $issued ) );
			if ( $this->sequence->commit( $year, $next ) ) {
				return array( $number, $file );
			}
			$this->files->delete( $file );
		}
		throw new RuntimeException( __( 'No Quotation number could be reserved; please try again.', 'linker-commerce' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Escaped by the caller.
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
	 * The PDF of an inquiry's Quotation, in the inquiry's language.
	 *
	 * @param WC_Order          $order  Inquiry.
	 * @param string            $number Quotation number.
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
