<?php
/**
 * The Quotation is ready, to the customer.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Quotation\Emails;

use DateTimeImmutable;
use Linker\Commerce\Inquiry\AccountLink;
use Linker\Commerce\Inquiry\Statuses;
use Linker\Commerce\Mail\CustomerOrderEmail;
use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Mail\Outbox;
use Linker\Commerce\Mail\Prepared;
use Linker\Commerce\Inquiry\Assessment\Lock;
use Linker\Commerce\Inquiry\Assessment\CurrentSource;
use Linker\Commerce\Quotation\Document;
use Linker\Commerce\Quotation\Issuer;
use Linker\Commerce\Vocabulary\LocaleFormat;
use Linker\Commerce\Quotation\Notice;
use Linker\Commerce\Registration\Approval;
use WC_Order;

/** Notifies the approved owner of an issued or revised quotation. */
final class QuotationIssuedEmail extends CustomerOrderEmail {
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
	/** Explicit unit memory writers do not own a native mysqli connection.
	 *
	 * @var bool
	 */
	private readonly bool $native;

	/**
	 * Email id.
	 */
	public const ID       = Notice::ID;
	public const PENDING  = Issuer::NOTICE_PENDING_META;
	public const ACCEPTED = Notice::ACCEPTED;
	public const JOB      = Notice::JOB;

	/**
	 * Sets up the email.
	 *
	 * @param string        $plugin_file Absolute path of the main plugin file.
	 * @param \Closure|null $write Native transaction, or an explicit unit memory writer.
	 * @param \Closure|null $read Authoritative native reader, or an explicit unit memory reader.
	 */
	public function __construct( string $plugin_file, ?\Closure $write = null, ?\Closure $read = null ) {
		$this->native        = null === $write;
		$this->read          = $read ?? static fn ( int $id ): ?WC_Order => CurrentSource::order( $id );
		$this->write         = $write ?? static fn ( callable $work ): mixed => \Linker\Commerce\Mail\NativeTransaction::run( $work );
		$this->id            = self::ID;
		$this->title         = __( 'Quotation issued', 'linker-commerce' );
		$this->description   = __( 'Sent to the customer when staff issue the Quotation of an inquiry.', 'linker-commerce' );
		$this->template_html = 'emails/linker-quotation-issued.php';
		$this->placeholders  = array(
			'{order_number}'     => '',
			'{quotation_number}' => '',
		);
		add_action( 'woocommerce_order_status_' . Statuses::RECEIVED . '_to_' . Statuses::QUOTATION . '_notification', array( $this, 'trigger' ), 10, 2 );
		parent::__construct( $plugin_file );
	}

	/**
	 * Only the approved owner's login can follow the private link.
	 *
	 * @param WC_Order $order Inquiry.
	 */
	protected function recipient_for_order( WC_Order $order ): string {
		$id = $order->get_customer_id();
		if ( ! $id || ! ( new Approval() )->sees_prices( $id ) ) {
			return '';
		}
		$owner = get_userdata( $id );
		return $owner instanceof \WP_User ? $owner->user_email : '';
	}

	/**
	 * Accept one notice for the pending document revision.
	 *
	 * @param int                $order_id Order id.
	 * @param WC_Order|false|int $order    Order, when the caller has it.
	 */
	public function trigger( $order_id, $order = false ): void {
		unset( $order ); // A callback's object may predate another accepted handoff.
		$job   = 0;
		$fence = $this->native ? \Linker\Commerce\Mail\ConnectionFence::enter() : null;
		try {
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
							if ( ! $order->has_status( Statuses::QUOTATION ) || $order->get_meta( \Linker\Commerce\Inquiry\Assessment\Reviews::ERASED ) || $number === $order->get_meta( self::ACCEPTED ) ) {
								// Retire only a definite terminal/erased/already-ACKed index row.
								// This does not mark a new message sent or free its original job.
								if ( 'yes' === $order->get_meta( self::PENDING ) ) {
									$order->update_meta_data( self::PENDING, 'no' );
									$order->save_meta_data();
								}
								return;
							}
							if ( '' === $number || 'yes' !== $order->get_meta( self::PENDING ) ) {
								return;
							}
							$this->placeholders['{quotation_number}'] = $number;
							$order->update_meta_data( self::PENDING, 'yes' );
							$order->save_meta_data();
							$message = '' === $this->recipient_for_order( $order ) ? null : Prepared::capture( fn () => parent::trigger( $order_id, $order ) );
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
										throw new \RuntimeException( 'quotation_notice_source_missing' );
									}
									$fresh->read_meta_data( true );
									if ( $fresh->get_customer_id() !== $order->get_customer_id() || ! $fresh->has_status( Statuses::QUOTATION ) || $fresh->get_meta( \Linker\Commerce\Inquiry\Assessment\Reviews::ERASED ) || $number !== $fresh->get_meta( Issuer::NUMBER_META ) || $number === $fresh->get_meta( self::ACCEPTED ) ) {
										throw new \RuntimeException( 'quotation_notice_source_changed' );
									}
									$fresh->update_meta_data( self::PENDING, 'no' );
									$fresh->update_meta_data( self::ACCEPTED, $number );
									$fresh->update_meta_data( self::JOB, (string) $id );
									$fresh->save_meta_data();
									$fresh->read_meta_data( true );
									if ( $number !== $fresh->get_meta( self::ACCEPTED ) || $id !== (int) $fresh->get_meta( self::JOB ) || 'no' !== $fresh->get_meta( self::PENDING ) ) {
										throw new \RuntimeException( 'quotation_notice_readback_failed' );
									}
								}
							);
						}
					);
				}
			);
		} finally {
			$fence?->close();
		}
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
					'status'     => Statuses::QUOTATION,
					'limit'      => \Linker\Commerce\Mail\Capacity::LIMITS['critical']['count'],
					'orderby'    => 'ID',
					'order'      => 'ASC',
					'meta_query' => $meta,
				)
			)
			: get_posts(
				array(
					'post_type'      => 'shop_order',
					'post_status'    => 'wc-' . Statuses::QUOTATION,
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
		/* translators: {quotation_number}: Quotation number, {order_number}: inquiry number. */
		return $this->is_revision()
			? __( 'Revised Quotation {quotation_number} for inquiry #{order_number}', 'linker-commerce' )
			: __( 'Your Quotation {quotation_number} for inquiry #{order_number}', 'linker-commerce' );
	}

	/**
	 * Default heading.
	 */
	public function get_default_heading() {
		return $this->is_revision() ? __( 'Your revised Quotation is ready', 'linker-commerce' ) : __( 'Your Quotation is ready', 'linker-commerce' );
	}

	/** A revision ends in the numeric suffix assigned by Issuer. */
	private function is_revision(): bool {
		return 1 === preg_match( '/-R[0-9]+$/D', $this->placeholders['{quotation_number}'] );
	}

	/**
	 * Number, validity and link for the template.
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
			'quotation_number' => $number,
			'valid_until'      => wp_date( LocaleFormat::date_format(), Document::valid_until( $issued )->getTimestamp() ),
			'quotation_url'    => AccountLink::quotation_url( $order ),
		);
	}
}
