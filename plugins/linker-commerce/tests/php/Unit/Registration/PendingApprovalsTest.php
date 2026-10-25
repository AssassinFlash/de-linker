<?php
/**
 * Tests for the waiting-accounts block of the daily digest.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Registration;

use Linker\Commerce\Registration\Approval;
use Linker\Commerce\Registration\PendingApprovals;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;
use WP_User;

/**
 * Tests for PendingApprovals: the block's identity, the set it lists (every
 * pending plain customer, oldest first) and the entry it puts in
 * the digest's hand.
 *
 * @covers \Linker\Commerce\Registration\PendingApprovals
 */
final class PendingApprovalsTest extends TestCase {

	/**
	 * User meta by user id and key: the approval states under test and the
	 * company of the first account.
	 *
	 * @var array<int, array<string, string>>
	 */
	private array $store = array(
		5 => array( 'billing_company' => 'Solarbau Beispiel GmbH' ),
	);

	/**
	 * An in-memory WordPress user store: 5 and 8 are customers.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
		WP_Mock::userFunction(
			'get_users',
			array(
				'args'   => array(
					array(
						'role'    => 'customer',
						'orderby' => 'registered',
						'order'   => 'ASC',
					),
				),
				'return' => fn (): array => array( $this->user( 5 ), $this->user( 8 ) ),
			)
		);
		WP_Mock::userFunction( 'get_user_meta', array( 'return' => fn ( int $user_id, string $key ): string => $this->store[ $user_id ][ $key ] ?? '' ) );
		WP_Mock::userFunction(
			'get_userdata',
			array(
				'return' => static function ( int $user_id ): ?WP_User {
					if ( ! in_array( $user_id, array( 5, 8 ), true ) ) {
						return null;
					}
					$user        = new WP_User();
					$user->ID    = $user_id;
					$user->roles = array( 'customer' );
					return $user;
				},
			)
		);
		WP_Mock::userFunction( 'admin_url', array( 'return' => static fn ( string $path ): string => 'https://example.test/wp-admin/' . $path ) );
		WP_Mock::userFunction( 'add_query_arg', array( 'return' => static fn ( string $key, int|string $value, string $url ): string => $url . '&' . $key . '=' . $value ) );
		WP_Mock::userFunction( 'get_current_blog_id', array( 'return' => 1 ) );
		WP_Mock::userFunction( 'wp_cache_get_last_changed', array( 'return' => fn (): string => json_encode( $this->store, JSON_THROW_ON_ERROR ) ) );
		WP_Mock::userFunction( 'number_format_i18n', array( 'return' => static fn ( int $count ): string => (string) $count ) );
		WP_Mock::userFunction( 'mysql2date', array( 'return' => static fn ( string $format, string $date ): string => $date ) );
	}

	/**
	 * The block's identity on the digest's contract.
	 */
	public function test_the_block_names_itself(): void {
		$block = new PendingApprovals( new Approval() );

		$this->assertSame( 'pending_accounts', $block->id() );
		$this->assertSame( 'Accounts waiting for approval (2)', $block->title() );
		$this->assertSame( 'No account is waiting for approval.', $block->empty_text() );
	}

	/**
	 * A customer without a state waits (the default is pending); approved
	 * accounts, restrictions and rejections are not new applications.
	 */
	public function test_it_lists_only_pending_accounts(): void {
		$block = new PendingApprovals( new Approval() );

		$this->assertCount( 2, $this->pending_entries( $block ), 'No state recorded: both customers wait.' );
		$this->assertSame( 2, $block->pending_count() );

		$this->store[5][ Approval::STATUS_META ] = Approval::APPROVED;
		$this->store[8][ Approval::STATUS_META ] = Approval::APPROVED;
		$this->assertSame( array(), $this->pending_entries( $block ) );

		$this->store[8][ Approval::STATUS_META ] = Approval::RESTRICTED;
		$this->assertSame( array(), $this->pending_entries( $block ) );
		$this->assertSame( 0, $block->pending_count(), 'Restricted summary and empty sentence are not applications.' );
		$this->assertStringContainsString( 'awaiting customer information: 1', $block->entries()[1]['label'] );
		$this->assertStringContainsString( '&status=restricted', $block->entries()[1]['url'] );
		$this->store[8][ Approval::STATUS_META ] = Approval::REJECTED;
		$this->assertSame( array(), $this->pending_entries( $block ) );
		$this->assertSame( 'Accounts waiting for approval (0)', $block->title() );
		$this->assertSame( $block->empty_text(), $block->entries()[0]['label'] );
		$this->assertStringContainsString( 'awaiting customer information: 0', $block->entries()[1]['label'] );
		$this->store[8][ Approval::STATUS_META ] = Approval::PENDING;
		$this->assertSame( 1, $block->pending_count() );
			/** The block's entries, in the digest's entry shape. @var list<array{label: string, url: string, link_text: string, detail: string}> $entries */
		$entries = $this->pending_entries( $block );
		$this->assertSame(
			array(
				array(
					'label'     => 'Maria Beispiel',
					'url'       => 'https://example.test/wp-admin/admin.php?page=linker-accounts&focus=8',
					'link_text' => 'Open the customer',
					'detail'    => 'Registered on 2026-10-09 08:15:00',
				),
			),
			$entries,
			'Without a company the display name stands in; the entry carries the way to the account.'
		);
	}

	/**
	 * An account with a company is listed under it.
	 */
	public function test_the_company_is_the_label(): void {
		$this->store[8][ Approval::STATUS_META ] = Approval::APPROVED;

		$entries = $this->pending_entries( new PendingApprovals( new Approval() ) );

		$this->assertCount( 1, $entries, 'The account waits.' );
		$this->assertSame(
			array( 'Solarbau Beispiel GmbH', 'https://example.test/wp-admin/admin.php?page=linker-accounts&focus=5' ),
			array( $entries[0]['label'] ?? '', $entries[0]['url'] ?? '' ),
			'The company is the label and the profile is the way to the account.'
		);
	}

	/**
	 * Application rows, distinct from the restricted summary and empty sentence.
	 *
	 * @param PendingApprovals $block Digest block.
	 * @return list<array{label: string, url: string, link_text: string, detail: string}>
	 */
	private function pending_entries( PendingApprovals $block ): array {
		return array_values( array_filter( $block->entries(), static fn ( array $entry ): bool => str_contains( $entry['url'], '&focus=' ) ) );
	}

	/**
	 * A user with the given id.
	 *
	 * @param int $user_id User.
	 */
	private function user( int $user_id ): WP_User {
		$user                  = new WP_User();
		$user->ID              = $user_id;
		$user->roles           = array( 'customer' );
		$user->display_name    = 'Maria Beispiel';
		$user->user_registered = '2026-10-09 08:15:00';
		return $user;
	}
}
