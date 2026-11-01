<?php
/** Bounded native recovery, against both Woo storage engines; no transport/provider.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Inquiry\Assessment\AuthorizationStore;
use Linker\Commerce\Inquiry\Assessment\Queue;
use Linker\Commerce\Inquiry\Assessment\Reviews;
use Linker\Commerce\Mail\Outbox;
use Linker\Commerce\Protection\BusinessCapacity;
use WC_Order;

/** Real native pages with source-scoped fixtures.
 *
 * @coversNothing
 */
final class InquiryRecoveryTest extends IntegrationTestCase {
	/** Exact native records owned by this case.
	 *
	 * @var array<int,WC_Order>
	 */
	private array $owned = array();
	/** Native datastore selection, restored without changing persistent settings.
	 *
	 * @return array<string,array{string}> Native storage modes.
	 */
	public static function stores(): array {
		return array(
			'HPOS' => array( 'yes' ),
			'CPT'  => array( 'no' ),
		);
	}

	/** Old sticky entries, moving pages, a failed consumer and repeated calls stay recoverable.
	 *
	 * @dataProvider stores
	 * @param string $hpos Native datastore selection.
	 */
	public function test_native_pages_remain_fair_without_query_hydration( string $hpos ): void {
		$storage = static fn (): string => $hpos;
		$no_sync = static fn (): string => 'no';
		add_filter( 'pre_option_woocommerce_custom_orders_table_enabled', $storage );
		add_filter( 'pre_option_woocommerce_custom_orders_table_data_sync_enabled', $no_sync );
		$this->later(
			static function () use ( $storage, $no_sync ): void {
				remove_filter( 'pre_option_woocommerce_custom_orders_table_enabled', $storage );
				remove_filter( 'pre_option_woocommerce_custom_orders_table_data_sync_enabled', $no_sync );
			}
		);
		foreach ( array( Queue::RECOVERY_OFFSET, Queue::HEARTBEAT ) as $key ) {
			$old = get_option( $key );
			$this->later(
				static function () use ( $key, $old ): void {
					false === $old ? delete_option( $key ) : update_option( $key, $old, false );
				}
			);
		}
		update_option( Queue::RECOVERY_OFFSET, 0, false );
		// This test owns only inquiry recovery; do not rebuild unrelated local sources.
		$mailer = WC()->mailer();
		$emails = $mailer->emails;
		unset( $mailer->emails[ \Linker\Commerce\Proforma\Emails\ProformaIssuedEmail::class ], $mailer->emails[ \Linker\Commerce\Registration\Emails\VatReviewEmail::class ] );
		$this->later(
			static function () use ( $mailer, $emails ): void {
				$mailer->emails = $emails;
			}
		);
		$this->owned = array();
		$only        = function ( array $args ): array {
			if ( isset( $args['meta_query'][0]['key'] ) && Queue::PENDING === $args['meta_query'][0]['key'] ) {
				$args['id'] = array() === $this->owned ? array( PHP_INT_MAX ) : array_keys( $this->owned );
			}
			return $args;
		};
		$only_posts  = function ( \WP_Query $query ): void {
			$meta = $query->get( 'meta_query' );
			if ( is_array( $meta ) && Queue::PENDING === ( $meta[0]['key'] ?? '' ) ) {
				$query->set( 'post__in', array() === $this->owned ? array( PHP_INT_MAX ) : array_keys( $this->owned ) );
			}
		};
		add_filter( 'woocommerce_order_query_args', $only );
		add_action( 'pre_get_posts', $only_posts );
		$this->later(
			static function () use ( $only, $only_posts ): void {
				remove_filter( 'woocommerce_order_query_args', $only );
				remove_action( 'pre_get_posts', $only_posts );
			}
		);
		$queue = new Queue();
		$limit = array_sum( array_column( BusinessCapacity::LIMITS, 'count' ) );
		$read  = new \ReflectionMethod( Queue::class, 'pending_ids' );
		// Check the actual native ID result before entering any consumer, even
		// when empty. A normalized/ignored include must fail without side effects.
		$run = function () use ( $queue, $read, $limit ): int {
			$pending = array_keys( array_filter( $this->owned, static fn ( WC_Order $order ): bool => 'yes' === $order->get_meta( Queue::PENDING ) ) );
			$offset  = (int) get_option( Queue::RECOVERY_OFFSET, 0 );
			$actual  = $read->invoke( null, $offset, $limit );
			self::assertSame( array_slice( $pending, $offset, $limit ), $actual, 'Exact owned IDs before every consumer pass.' );
			if ( array() === $actual && $offset > 0 ) {
				self::assertSame( array_slice( $pending, 0, $limit ), $read->invoke( null, 0, $limit ) );
			}
			return $queue->recover();
		};
		self::assertSame( 0, $run() );
		self::assertSame( 0, get_option( Queue::RECOVERY_OFFSET ) );
		// A nonpending older source distinguishes a true pending-only CPT query.
		for ( $i = 0; $i <= $limit + 2; ++$i ) {
			$order = new WC_Order();
			$order->set_status( 'pending' );
			$order->update_meta_data( Queue::PENDING, 0 === $i ? 'no' : 'yes' );
			$order->update_meta_data( Reviews::ERASED, 'yes' );
			$order->save();
			$id                 = $order->get_id();
			$this->owned[ $id ] = $order;
			$this->later(
				static function () use ( $order, $id ): void {
					foreach ( as_get_scheduled_actions(
						array(
							'hook'     => Queue::PROCESS,
							'args'     => array( $id ),
							'group'    => Outbox::GROUP,
							'per_page' => -1,
						),
						'ids'
					) as $action ) {
						\ActionScheduler::store()->delete_action( (int) $action );}
					delete_option( AuthorizationStore::PREFIX . $id );
					$order->delete( true );
				}
			);
		}
		$ids     = array_slice( array_keys( $this->owned ), 1 );
		$loaded  = array();
		$observe = function ( string $class_name, string $type, int $id ) use ( &$loaded ): string {
			if ( isset( $this->owned[ $id ] ) ) {
				$loaded[] = $id;
			}
			return $class_name;
		};
		add_filter( 'woocommerce_order_class', $observe, 10, 3 );
		$this->later(
			static function () use ( $observe ): void {
				remove_filter( 'woocommerce_order_class', $observe );
			}
		);
		self::assertSame( $limit, $run() );
		self::assertSame( array_slice( $ids, 0, $limit ), $loaded, 'Exactly one fresh consumer hydration per selected ID.' );
		self::assertSame( $limit, get_option( Queue::RECOVERY_OFFSET ) );
		$first = $this->owned[ $ids[0] ];
		$first->update_meta_data( Queue::PENDING, 'complete' );
		$first->save_meta_data();
		$loaded = array();
		self::assertSame( 1, $run() );
		self::assertSame( array( end( $ids ) ), $loaded );
		self::assertSame( 0, get_option( Queue::RECOVERY_OFFSET ) );
		$loaded = array();
		self::assertSame( $limit, $run() );
		self::assertSame( array_slice( $ids, 1, $limit ), $loaded, 'The item shifted left by deletion is revisited on wrap.' );

		$source = $this->owned[ $ids[1] ];
		$later  = $this->owned[ $ids[2] ];
		foreach ( $this->owned as $id => $order ) {
			if ( $order !== $source && $order !== $later ) {
				$order->update_meta_data( Queue::PENDING, 'complete' );
			} else {
				$order->delete_meta_data( Reviews::ERASED );
				self::assertTrue(
					AuthorizationStore::edit(
						$id,
						static function ( array &$state ): void {
							$state = array(
								'status'  => 'pending',
								'next_at' => 0,
							);
						}
					)
				);
			}
			$order->save_meta_data();
		}
		$fail = static function ( $pre, $timestamp, $hook, $args ) use ( $source ) {
			if ( Queue::PROCESS === $hook && array( $source->get_id() ) === $args ) {
				throw new \RuntimeException( 'synthetic_recovery_schedule_failure' );
			}
			return $pre;
		};
		update_option( Queue::RECOVERY_OFFSET, 0, false );
		update_option( Queue::HEARTBEAT, 1, false );
		add_filter( 'pre_as_schedule_single_action', $fail, 10, 4 );
		try {
			$run();
			self::fail( 'Native scheduling failure must propagate.' );
		} catch ( \RuntimeException $error ) {
			self::assertSame( 'synthetic_recovery_schedule_failure', $error->getMessage() );
		} finally {
			remove_filter( 'pre_as_schedule_single_action', $fail, 10 );
		}
		self::assertSame( 1, get_option( Queue::HEARTBEAT ), 'A failed pass cannot refresh readiness.' );
		self::assertSame( 0, get_option( Queue::RECOVERY_OFFSET ) );
		self::assertNotFalse( as_has_scheduled_action( Queue::PROCESS, array( $later->get_id() ), Outbox::GROUP ), 'A failed first source cannot starve a later source on the same short page.' );
		self::assertCount(
			0,
			as_get_scheduled_actions(
				array(
					'hook'   => Queue::PROCESS,
					'args'   => array( $source->get_id() ),
					'group'  => Outbox::GROUP,
					'status' => 'pending',
				),
				'ids'
			)
		);
		self::assertSame( 2, $run() );
		$action = as_has_scheduled_action( Queue::PROCESS, array( $source->get_id() ), Outbox::GROUP );
		self::assertNotFalse( $action );
		$run();
		self::assertSame( $action, as_has_scheduled_action( Queue::PROCESS, array( $source->get_id() ), Outbox::GROUP ), 'Re-entry retains the original unique native work.' );
		self::assertSame( array(), AuthorizationStore::read( $ids[ count( $ids ) - 1 ] ), 'Erased sources never acquire sending permission.' );
	}
}
