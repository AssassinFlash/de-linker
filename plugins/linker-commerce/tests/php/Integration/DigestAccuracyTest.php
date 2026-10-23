<?php
/**
 * Digest statistics against native accounts and authenticated dispositions.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Digest\DigestEmail;
use Linker\Commerce\Digest\InquiriesAwaitingProforma;
use Linker\Commerce\Inquiry\Assessment\Queue;
use Linker\Commerce\Inquiry\Assessment\StructuredMeta;
use Linker\Commerce\Inquiry\Statuses;
use Linker\Commerce\Mail\Capture;
use Linker\Commerce\Mail\NativeTransaction;
use Linker\Commerce\Protection\BusinessDisposition;
use Linker\Commerce\Protection\IntakeStore;
use Linker\Commerce\Registration\Approval;
use Linker\Commerce\Registration\PendingApprovals;
use Linker\Commerce\Settings\Options;
use PHPUnit\Framework\TestCase;
use WC_Order;

/** No transport, global pool reset, or modification of pre-existing records.
 *
 * @coversNothing
 */
final class DigestAccuracyTest extends TestCase {
	/** Exact synthetic cleanup.
	 *
	 * @var list<callable():void>
	 */
	private array $cleanup = array();

	/** Raw pre-fixture registry.
	 *
	 * @var array{option_value:string,autoload:string}|null
	 */
	private ?array $intake = null;

	/** Only the integration bootstrap provides the real native APIs. */
	public static function setUpBeforeClass(): void {
		if ( '1' !== getenv( 'LINKER_INTEGRATION' ) ) {
			self::markTestSkipped( 'Requires the existing local WordPress integration instance.' );
		}
	}

	/** Capture exact authoritative state without deleting or resetting any pool. */
	protected function setUp(): void {
		parent::setUp();
		$this->intake = $this->raw_intake();
		WC()->mailer();
		$locale          = static fn (): string => 'en_US';
		add_filter( 'pre_option_linker_commerce_team_locale', $locale );
		$this->cleanup[] = static function () use ( $locale ): void {
			remove_filter( 'pre_option_linker_commerce_team_locale', $locale );
		};
	}

	/** Restore only this fixture's exact registry after deleting its own records.
	 *
	 * @throws \RuntimeException Cleanup or authoritative readback failed.
	 */
	protected function tearDown(): void {
		try {
			foreach ( array_reverse( $this->cleanup ) as $remove ) {
				$remove();
			}
			NativeTransaction::run(
				function (): void {
					global $wpdb;
					if ( $this->raw_intake() !== $this->intake ) {
						// phpcs:disable WordPress.DB.DirectDatabaseQuery -- Exact local fixture compensation, preserving presence/value/autoload.
						if ( null === $this->intake ) {
							$wpdb->delete( $wpdb->options, array( 'option_name' => IntakeStore::OPTION ) );
						} else {
							$wpdb->query( $wpdb->prepare( 'INSERT INTO %i (option_name,option_value,autoload) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE option_value=VALUES(option_value),autoload=VALUES(autoload)', $wpdb->options, IntakeStore::OPTION, $this->intake['option_value'], $this->intake['autoload'] ) );
						}
						// phpcs:enable WordPress.DB.DirectDatabaseQuery
					}
					if ( $this->raw_intake() !== $this->intake ) {
						throw new \RuntimeException( 'digest_fixture_raw_restore_failed' );
					}
				}
			);
			wp_cache_delete( IntakeStore::OPTION, 'options' );
			wp_cache_delete( 'alloptions', 'options' );
			wp_cache_delete( 'notoptions', 'options' );
			self::assertSame( null === $this->intake ? false : maybe_unserialize( $this->intake['option_value'] ), get_option( IntakeStore::OPTION ) );
		} finally {
			$this->cleanup = array();
			wp_set_current_user( 0 );
			parent::tearDown();
		}
	}

	/** Native subject, title and visible badge agree, including decorative rows.
	 *
	 * @dataProvider account_sets
	 * @phpstan-param list<string> $states
	 * @param array $states Fixture approval states.
	 * @param int   $pending Applications awaiting staff approval.
	 * @param int   $restricted Accounts awaiting customer information.
	 */
	public function test_pending_count_matches_native_subject_title_and_badge( array $states, int $pending, int $restricted ): void {
		$ids = array();
		foreach ( $states as $state ) {
			$id = wp_insert_user(
				array(
					'user_login' => 'digest-' . wp_generate_uuid4(),
					'user_pass'  => wp_generate_password(),
					'user_email' => 'digest-' . wp_generate_uuid4() . '@example.test',
					'role'       => 'customer',
				)
			);
			self::assertIsInt( $id );
			$ids[] = $id;
			update_user_meta( $id, Approval::STATUS_META, $state );
			$this->cleanup[] = static function () use ( $id ): void {
				require_once ABSPATH . 'wp-admin/includes/user.php';
				wp_delete_user( $id );
			};
		}
		$only_owned = static function ( \WP_User_Query $query ) use ( $ids ): void {
			if ( 'customer' === $query->get( 'role' ) ) {
				$query->set( 'include', array() === $ids ? array( 0 ) : $ids );
			}
		};
		add_action( 'pre_get_users', $only_owned );
		$this->cleanup[] = static function () use ( $only_owned ): void {
			remove_action( 'pre_get_users', $only_owned );
		};
		$block           = new PendingApprovals();
		$email           = new DigestEmail( WP_PLUGIN_DIR . '/linker-commerce/linker-commerce.php', new Options() );
		// Exercise the existing subject placeholder through Woo's native renderer.
		$settings        = static fn (): array => array(
			'enabled' => 'yes',
			'subject' => 'Daily digest, {date}{summary}',
		);
		add_filter( 'pre_option_woocommerce_linker_digest_settings', $settings );
		$this->cleanup[] = static function () use ( $settings ): void {
			remove_filter( 'pre_option_woocommerce_linker_digest_settings', $settings );
		};
		$message         = Capture::run( $email, static fn () => $email->send_report( array( $block ) ) );
		self::assertNotNull( $message );
		self::assertSame( 0 === $pending ? '' : '：' . $pending . ' 个待审客户', $email->placeholders['{summary}'] );
		self::assertSame( 'Daily digest, ' . $email->placeholders['{date}'] . $email->placeholders['{summary}'], $message->subject );
		self::assertStringContainsString( 'Accounts waiting for approval (' . $pending . ')', $message->body );
		self::assertMatchesRegularExpression( '/class="linker-digest-num"[^>]*>\s*' . $pending . '<\/td>/', $message->body );
		self::assertStringContainsString( 'Restricted, awaiting customer information: ' . $restricted, $message->body );
		if ( 0 === $pending ) {
			self::assertStringContainsString( $block->empty_text(), $message->body );
		}
	}

	/** Native account combinations.
	 *
	 * @return array<string,array{list<string>,int,int}>
	 */
	public static function account_sets(): array {
		return array(
			'empty'           => array( array(), 0, 0 ),
			'restricted only' => array( array( Approval::RESTRICTED ), 0, 1 ),
			'one pending'     => array( array( Approval::PENDING ), 1, 0 ),
			'multiple mixed'  => array( array( Approval::PENDING, Approval::PENDING, Approval::RESTRICTED ), 2, 1 ),
		);
	}

	/** Only authenticated disposition excludes a received inquiry; corruption restores visibility. */
	public function test_only_authenticated_native_disposition_excludes_an_inquiry(): void {
		wp_set_current_user( 1 );
		self::assertTrue( current_user_can( 'manage_woocommerce' ) );
		$order = $this->source();
		$body  = BusinessDisposition::body( $order );
		self::assertTrue( $this->listed( $order ), 'An unprocessed inquiry must remain visible.' );
		$result = BusinessDisposition::run( $order->get_id(), hash( 'sha256', $body ), wp_generate_uuid4() );
		self::assertIsArray( $result );
		self::assertSame( 'applied', $result['status'] );
		self::assertTrue( BusinessDisposition::processed( $order ) );
		$order->read_meta_data( true );
		$valid = $order->get_meta( BusinessDisposition::META );
		self::assertFalse( $this->listed( $order ), 'A retained received status must not turn an audited disposition into PI work.' );
		$readback = wc_get_order( $order->get_id() );
		self::assertInstanceOf( WC_Order::class, $readback );
		self::assertSame( Statuses::RECEIVED, $readback->get_status() );
		self::assertSame( $body, BusinessDisposition::body( $readback ) );

		$copy = $this->source();
		StructuredMeta::update( $copy, BusinessDisposition::META, $valid );
		$copy->save_meta_data();
		self::assertTrue( $this->listed( $copy ), 'A replayed marker from another order is not an employee disposition.' );
		$invalid        = $valid;
		$invalid['mac'] = str_repeat( '0', 64 );
		StructuredMeta::update( $order, BusinessDisposition::META, $invalid );
		$order->save_meta_data();
		self::assertTrue( $this->listed( $order ), 'A forged/corrupt marker must remain visible.' );
		StructuredMeta::update( $order, BusinessDisposition::META, $valid );
		$order->save_meta_data();
		wp_update_comment(
			array(
				'comment_ID'      => $result['note'],
				'comment_content' => 'Synthetic altered audit.',
			)
		);
		self::assertTrue( $this->listed( $order ), 'An invalid native audit must remain visible.' );
		$copy->delete_meta_data( BusinessDisposition::META );
		StructuredMeta::update( $copy, Queue::META, array( 'result' => array( 'label' => 'spam' ) ) );
		$copy->save_meta_data();
		self::assertTrue( $this->listed( $copy ), 'A model label is not a staff disposition.' );
	}

	/** Native synthetic old inquiry, without triggering a customer submission or transport. */
	private function source(): WC_Order {
		$order = new WC_Order();
		$order->set_date_created( time() - 25 * HOUR_IN_SECONDS );
		$order->set_customer_note( 'Вам перевод 123 руб. забрать тут https://fredmer.buzz/synthetic-digest' );
		$order->update_meta_data( '_linker_inquiry_source', 'contact' );
		$order->set_status( Statuses::RECEIVED );
		StructuredMeta::update( $order, Queue::META, array( 'snapshot' => array( 'submission' => array( 'message' => $order->get_customer_note() ) ) ) );
		$order->save();
		$this->cleanup[] = static function () use ( $order ): void {
			$order->delete( true );
		};
		return $order;
	}

	/** Read whether the actual digest includes this fixture.
	 *
	 * @param WC_Order $order Test-owned source.
	 */
	private function listed( WC_Order $order ): bool {
		$label  = 'Inquiry #' . $order->get_order_number() . ' – ';
		$writes = array();
		$trace  = static function ( string $sql ) use ( &$writes ): string {
			if ( 1 === preg_match( '/^\s*(INSERT|UPDATE|DELETE|REPLACE|ALTER|DROP|TRUNCATE)\b/i', $sql ) ) {
				$writes[] = $sql;
			}
			return $sql;
		};
		add_filter( 'query', $trace );
		try {
			$entries = ( new InquiriesAwaitingProforma() )->entries();
		} finally {
			remove_filter( 'query', $trace );
		}
		self::assertSame( array(), $writes, 'Digest reads must not write any order, audit, queue or capacity SQL.' );
		foreach ( $entries as $entry ) {
			if ( str_starts_with( $entry['label'], $label ) ) {
				return true;
			}
		}
		return false;
	}

	/** Raw authoritative presence, exact bytes and autoload.
	 *
	 * @return array{option_value:string,autoload:string}|null
	 * @throws \RuntimeException The raw source could not be read.
	 */
	private function raw_intake(): ?array {
		global $wpdb;
		// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- Exact fixture readback; object cache cannot prove compensation.
		$row = $wpdb->get_row( $wpdb->prepare( 'SELECT option_value,autoload FROM %i WHERE option_name=%s', $wpdb->options, IntakeStore::OPTION ), ARRAY_A );
		if ( '' !== $wpdb->last_error ) {
			throw new \RuntimeException( 'digest_fixture_intake_unreadable' );
		}
		return $row;
	}
}
