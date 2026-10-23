<?php
/**
 * The Proforma invoice is ready, to the customer.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Proforma\Emails;

use DateTimeImmutable;
use Linker\Commerce\Account\DocumentDownload;
use Linker\Commerce\Inquiry\Statuses;
use Linker\Commerce\Mail\CustomerOrderEmail;
use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Mail\Outbox;
use Linker\Commerce\Mail\Prepared;
use Linker\Commerce\Inquiry\Assessment\Lock;
use Linker\Commerce\Inquiry\Assessment\CurrentSource;
use Linker\Commerce\Proforma\Document;
use Linker\Commerce\Proforma\Issuer;
use Linker\Commerce\Vocabulary\LocaleFormat;
use WC_Order;

/**
 * Sent when staff issue the Proforma: number, validity and a link to the PDF in
 * the account. The PDF is not attached and the email names no bank account:
 * the account copy is the one a customer can trust for the bank details
 * (docs/specs/11-commerce.md, journey step 5; account-workspace.md §0.2).
 */
final class ProformaIssuedEmail extends CustomerOrderEmail {
	/** Short native writer; unit template tests supply an explicit memory callback.
	 *
	 * @var \Closure(callable():void):mixed
	 */
	private readonly \Closure $write;
	/** Native fresh-source reader, or explicit in-memory source for template units.
	 *
	 * @var \Closure(int):?WC_Order
	 */
	private readonly \Closure $read;

	/**
	 * Email id.
	 */
	public const ID       = 'linker_proforma_issued';
	public const PENDING  = Issuer::NOTICE_PENDING_META;
	public const ACCEPTED = '_linker_proforma_notice_number';
	public const JOB      = '_linker_proforma_notice_job';

	/**
	 * Sets up the email.
	 *
	 * @param string        $plugin_file Absolute path of the main plugin file.
	 * @param \Closure|null $write Native transaction, or an explicit unit memory writer.
	 * @param \Closure|null $read Authoritative native reader, or an explicit unit memory reader.
	 */
	public function __construct( string $plugin_file, ?\Closure $write = null, ?\Closure $read = null ) {
		$this->read          = $read ?? static fn ( int $id ): ?WC_Order => CurrentSource::order( $id );
		$this->write         = $write ?? static fn ( callable $work ): mixed => \Linker\Commerce\Mail\NativeTransaction::run( $work );
		$this->id            = self::ID;
		$this->title         = __( 'Proforma invoice issued', 'linker-commerce' );
		$this->description   = __( 'Sent to the customer when staff issue the Proforma invoice of an inquiry.', 'linker-commerce' );
		$this->template_html = 'emails/linker-proforma-issued.php';
		$this->placeholders  = array(
			'{order_number}'    => '',
			'{proforma_number}' => '',
		);
		add_action( 'woocommerce_order_status_' . Statuses::RECEIVED . '_to_' . Statuses::PROFORMA . '_notification', array( $this, 'trigger' ), 10, 2 );
		parent::__construct( $plugin_file );
	}

	/**
	 * Sends the email about an inquiry that already has a Proforma number.
	 *
	 * WooCommerce fires this on the status transition, before Issuer::ensure_issued()
	 * writes the number (woocommerce_order_status_{to} runs first; the email action
	 * is the from_to hook). A blocked inquiry — no bank account, an empty inquiry,
	 * a line without a price — keeps the new status and never gets a number. Sending
	 * then names an empty number, a validity of 1970-01-30 (issued meta 0 plus the
	 * 30-day term) and a download that 404s. No number, no mail. The Issue button
	 * writes the number before it changes the status, so that path still sends.
	 *
	 * @param int                $order_id Order id.
	 * @param WC_Order|false|int $order    Order, when the caller has it.
	 */
	public function trigger( $order_id, $order = false ): void {
		unset( $order ); // A callback's object may predate another accepted handoff.
		$job = 0;
		Lock::run(
			'release-' . (int) $order_id,
			function () use ( $order_id, &$job ): void {
				( $this->write )(
					function () use ( $order_id, &$job ): void {
						$order = ( $this->read )( (int) $order_id );
						if ( ! $order instanceof WC_Order ) {
							return;
						}
						$order->read_meta_data( true );
						$number = (string) $order->get_meta( Issuer::NUMBER_META );
						if ( ! $order->has_status( Statuses::PROFORMA ) || $order->get_meta( \Linker\Commerce\Inquiry\Assessment\Reviews::ERASED ) || $number === $order->get_meta( self::ACCEPTED ) ) {
							// Retire only a definite terminal/erased/already-ACKed index row.
							// This does not mark a new message sent or free its original job.
							if ( 'yes' === $order->get_meta( self::PENDING ) ) {
								$order->update_meta_data( self::PENDING, 'no' );
								$order->save_meta_data();
							}
							return;
						}
						if ( '' === $number ) {
							return;
						}
						$this->placeholders['{proforma_number}'] = $number;
						$order->update_meta_data( self::PENDING, 'yes' );
						$order->save_meta_data();
						$message = Prepared::capture( fn () => parent::trigger( $order_id, $order ) );
						if ( null === $message ) {
							// Native disabled/no-recipient policy explicitly skipped this notice.
							$order->update_meta_data( self::PENDING, 'no' );
							$order->update_meta_data( self::ACCEPTED, $number );
							$order->save_meta_data();
							return;
						}
						$job = ( new JobStore() )->create(
							$message,
							0,
							function ( int $id ) use ( $order, $number ): void {
								$fresh = ( $this->read )( $order->get_id() );
								if ( ! $fresh instanceof WC_Order ) {
									throw new \RuntimeException( 'proforma_notice_source_missing' );
								}
								$fresh->read_meta_data( true );
								if ( ! $fresh->has_status( Statuses::PROFORMA ) || $fresh->get_meta( \Linker\Commerce\Inquiry\Assessment\Reviews::ERASED ) || $number !== $fresh->get_meta( Issuer::NUMBER_META ) || $number === $fresh->get_meta( self::ACCEPTED ) ) {
									throw new \RuntimeException( 'proforma_notice_source_changed' );
								}
								$fresh->update_meta_data( self::PENDING, 'no' );
								$fresh->update_meta_data( self::ACCEPTED, $number );
								$fresh->update_meta_data( self::JOB, (string) $id );
								$fresh->save_meta_data();
								$fresh->read_meta_data( true );
								if ( $number !== $fresh->get_meta( self::ACCEPTED ) || $id !== (int) $fresh->get_meta( self::JOB ) || 'no' !== $fresh->get_meta( self::PENDING ) ) {
									throw new \RuntimeException( 'proforma_notice_readback_failed' );
								}
							}
						);
					}
				);
			}
		);
		if ( $job > 0 ) {
			$deliver = static function () use ( $job ): void {
				/** This action is documented in Mail\Module::register(). */
				do_action( Outbox::HOOK, $job ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound, WooCommerce.Commenting.CommentHooks.MissingHookComment -- Existing same-job consumer, outside the source lock and only after committed ownership.
			};
			if ( ! \Linker\Commerce\Mail\NativeTransaction::after_commit( $deliver ) && ! \Linker\Commerce\Mail\Capacity::transaction_active() ) {
				$deliver();
			}
		}
	}

	/** Rebuild only explicitly pending new notices, never historical held jobs. */
	public static function recover(): void {
		$emails = WC()->mailer()->get_emails();
		$email  = $emails[ self::class ] ?? null;
		if ( ! $email instanceof self ) {
			return;
		}
		// One critical-pool-sized batch per existing minute recovery heartbeat.
		$meta = array(
			array(
				'key'   => self::PENDING,
				'value' => 'yes',
			),
			array(
				'relation' => 'OR',
				array(
					'key'     => \Linker\Commerce\Inquiry\Assessment\Reviews::ERASED,
					'compare' => 'NOT EXISTS',
				),
				array(
					'key'   => \Linker\Commerce\Inquiry\Assessment\Reviews::ERASED,
					'value' => '',
				),
			),
		);
		// Woo's meta_query is HPOS-only. Classic storage uses WP's native
		// postmeta query, otherwise 64 older rows can starve the pending source.
		// phpcs:disable WordPress.DB.SlowDBQuery -- One critical-pool-sized pending-only native source query.
		$orders = \Automattic\WooCommerce\Utilities\OrderUtil::custom_orders_table_usage_is_enabled()
			? wc_get_orders(
				array(
					'status'     => Statuses::PROFORMA,
					'limit'      => \Linker\Commerce\Mail\Capacity::LIMITS['critical']['count'],
					'orderby'    => 'ID',
					'order'      => 'ASC',
					'meta_query' => $meta,
				)
			)
			: get_posts(
				array(
					'post_type'      => 'shop_order',
					'post_status'    => 'wc-' . Statuses::PROFORMA,
					'posts_per_page' => \Linker\Commerce\Mail\Capacity::LIMITS['critical']['count'],
					'fields'         => 'ids',
					'orderby'        => 'ID',
					'order'          => 'ASC',
					'meta_query'     => $meta,
				)
			);
		// phpcs:enable
		foreach ( is_array( $orders ) ? $orders : array() as $source ) {
			$email->trigger( $source instanceof WC_Order ? $source->get_id() : $source );
		}
	}

	/**
	 * Default subject.
	 */
	public function get_default_subject() {
		/* translators: {proforma_number}: Proforma number, {order_number}: inquiry number. */
		return __( 'Your Proforma invoice {proforma_number} for inquiry #{order_number}', 'linker-commerce' );
	}

	/**
	 * Default heading.
	 */
	public function get_default_heading() {
		return __( 'Your Proforma invoice is ready', 'linker-commerce' );
	}

	/**
	 * Number, validity and link for the template.
	 *
	 * An inquiry that reached "Proforma invoice issued" without a number (no
	 * bank account, an empty inquiry, a line without a price) must not render
	 * the letter: issued meta 0 plus the 30-day term is 1970-01-30, and the
	 * download answers 404. trigger() already refuses to send; this is the
	 * same refusal for any other caller of the body.
	 *
	 * @return array<string, mixed>
	 */
	protected function template_args(): array {
		$order = $this->object;
		if ( ! $order instanceof WC_Order ) {
			return array();
		}
		$number = (string) $order->get_meta( Issuer::NUMBER_META );
		if ( '' === $number ) {
			return array();
		}
		$issued = ( new DateTimeImmutable() )->setTimestamp( (int) $order->get_meta( Issuer::ISSUED_META ) );
		return array(
			'proforma_number' => $number,
			'valid_until'     => wp_date( LocaleFormat::date_format(), Document::valid_until( $issued )->getTimestamp() ),
			'download_url'    => DocumentDownload::proforma_url( $order ),
			'inquiry_url'     => $order->get_view_order_url(),
		);
	}
}
