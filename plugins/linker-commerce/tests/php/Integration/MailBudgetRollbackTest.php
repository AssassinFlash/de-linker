<?php
/** Native restart-safe rollback rehearsal.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Mail\BudgetRollback;
use Linker\Commerce\Mail\OptionBudgetLedger;
use Linker\Commerce\Mail\Throttle;

/** Neither transport's charged attempts disappear during rollback or roll-forward.
 *
 * @coversNothing
 */
final class MailBudgetRollbackTest extends IntegrationTestCase {
	/** Pause, project twice, append an old-code send, then reconcile and resume. */
	public function test_interrupted_projection_is_idempotent_and_preserves_new_records(): void {
		$now    = time();
		$legacy = array( $now - 500, $now - 300 );
		update_option( Throttle::OPTION, $legacy, false );
		$t = new Throttle();
		$this->assertSame( $now, $t->reserve( $now, Throttle::SMTP ) );
		$this->assertSame( $now, $t->reserve( $now, Throttle::PHP ) );
		$migration = new BudgetRollback();
		$this->assertInstanceOf( \WP_Error::class, $migration->transfer() );
		$this->assertTrue( $migration->pause() );
		$paused_ledger = get_option( OptionBudgetLedger::OPTION );
		$this->assertGreaterThan( $now, $t->reserve( $now, Throttle::SMTP, true ) );
		$this->assertEquals( json_decode( $paused_ledger, true ), json_decode( get_option( OptionBudgetLedger::OPTION ), true ) );
		$first = $migration->transfer();
		$this->assertIsArray( $first );
		$this->assertSame( 2, $first['appended'] );
		$this->assertSame( array_merge( $legacy, array( $now, $now ) ), get_option( Throttle::OPTION ) );
		// A caller interrupted after commit can safely run the exact command again.
		$again = ( new BudgetRollback() )->transfer();
		$this->assertIsArray( $again );
		$this->assertSame( 0, $again['appended'] );
		$projected   = get_option( Throttle::OPTION );
		$projected[] = $now + 1; // A subsequent old-code send; never overwrite it.
		update_option( Throttle::OPTION, $projected, false );
		$again = $migration->transfer();
		$this->assertIsArray( $again );
		$this->assertSame( 0, $again['appended'] );
		$this->assertSame( $projected, get_option( Throttle::OPTION ) );
		// Another old-code send after the last projection is imported into both pools.
		$projected[] = $now + 2;
		update_option( Throttle::OPTION, $projected, false );
		$resumed = $migration->transfer( true );
		$this->assertIsArray( $resumed );
		$this->assertSame( 1, $resumed['imported'] );
		$this->assertSame( 0, $resumed['appended'] );
		$this->assertFalse( $resumed['paused'] );
		$this->assertSame( $projected, get_option( Throttle::OPTION ) );
		$state = json_decode( get_option( OptionBudgetLedger::OPTION ), true );
		$this->assertCount( 2, array_filter( $state['entries'], static fn ( array $entry ): bool => 'attempt' === ( $entry['origin'] ?? '' ) ) );
		$this->assertCount( 2, array_filter( $state['entries'], static fn ( array $entry ): bool => $now + 2 === $entry['time'] ) );
		$this->assertSame( $now + 3, $t->reserve( $now + 3, Throttle::SMTP, true ) );
	}

	/** An interrupted transaction rolls back both option writes; retry remains safe. */
	public function test_failed_second_write_rolls_back_legacy_append(): void {
		global $wpdb;
		$now = time();
		update_option( Throttle::OPTION, array( $now - 300 ), false );
		$this->assertSame( $now, ( new Throttle() )->reserve( $now, Throttle::SMTP ) );
		$migration = new BudgetRollback();
		$this->assertTrue( $migration->pause() );
		$before_legacy = get_option( Throttle::OPTION );
		$before_new    = get_option( OptionBudgetLedger::OPTION );
		$fail          = static function ( string $query ): string {
			return str_contains( $query, 'UPDATE ' ) && str_contains( $query, OptionBudgetLedger::OPTION ) ? 'INVALID TEST-OWNED BUDGET WRITE' : $query;
		};
		$previous      = $wpdb->suppress_errors( true );
		add_filter( 'query', $fail );
		try {
			$this->assertInstanceOf( \WP_Error::class, $migration->transfer() );
		} finally {
			remove_filter( 'query', $fail );
			$wpdb->suppress_errors( $previous );
		}
		foreach ( array( Throttle::OPTION, OptionBudgetLedger::OPTION ) as $key ) {
			wp_cache_delete( $key, 'options' );
		}
		$this->assertSame( $before_legacy, get_option( Throttle::OPTION ) );
		$this->assertSame( $before_new, get_option( OptionBudgetLedger::OPTION ) );
		$result = $migration->transfer();
		$this->assertIsArray( $result );
		$this->assertSame( 1, $result['appended'] );
	}

	/** The migration cannot commit an enclosing business transaction. */
	public function test_enclosing_transaction_is_left_intact(): void {
		global $wpdb;
		$migration = new BudgetRollback();
		$this->assertTrue( $migration->pause() );
		// phpcs:disable WordPress.DB.DirectDatabaseQuery -- Test the native transaction boundary itself.
		$wpdb->query( 'START TRANSACTION' );
		$wpdb->query( $wpdb->prepare( "INSERT INTO {$wpdb->options} (option_name,option_value,autoload) VALUES (%s,'sentinel','off')", 'linker_commerce_budget_nested_test' ) );
		try {
			$result = $migration->transfer();
			$this->assertInstanceOf( \WP_Error::class, $result );
			$this->assertSame( 'mail_budget_transaction_active', $result->get_error_code() );
			$this->assertSame( 'sentinel', $wpdb->get_var( $wpdb->prepare( "SELECT option_value FROM {$wpdb->options} WHERE option_name=%s", 'linker_commerce_budget_nested_test' ) ) );
		} finally {
			$wpdb->query( 'ROLLBACK' );
		}
		$this->assertNull( $wpdb->get_var( $wpdb->prepare( "SELECT option_value FROM {$wpdb->options} WHERE option_name=%s", 'linker_commerce_budget_nested_test' ) ) );
		// phpcs:enable
	}
	/** An outer business transaction queues work rather than refunding an actual mail attempt. */
	public function test_reservation_does_not_join_an_outer_business_transaction(): void {
		global $wpdb;
		$now    = time();
		$before = get_option( OptionBudgetLedger::OPTION );
		// phpcs:disable WordPress.DB.DirectDatabaseQuery -- Own the test transaction and prove the budget never commits or joins it.
		$wpdb->query( 'START TRANSACTION' );
		try {
			$this->assertSame( $now + 1, ( new Throttle() )->reserve( $now, Throttle::SMTP ) );
			$this->assertSame( $now, ( new Throttle() )->next_slot( $now, Throttle::SMTP ) );
		} finally {
			$wpdb->query( 'ROLLBACK' ); }
		// phpcs:enable
		$this->assertSame( $before, get_option( OptionBudgetLedger::OPTION ) );
		$this->assertSame( $now, ( new Throttle() )->reserve( $now, Throttle::SMTP ) );
	}
}
