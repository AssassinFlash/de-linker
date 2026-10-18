<?php
/**
 * Tests for the pending account status notice.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Account;

use Linker\Commerce\Account\PendingGate;
use Linker\Commerce\Registration\Approval;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * The state notice is local to the account content; approval never takes over a page.
 *
 * @covers \Linker\Commerce\Account\PendingGate
 */
final class PendingGateTest extends TestCase {

	/**
	 * Translation and escaping return their input.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
		WP_Mock::userFunction( 'plugin_dir_path', array( 'return' => '/plugin/' ) );
	}

	/**
	 * The status card names the review and retains the live card design.
	 */
	public function test_render_is_the_review_card(): void {
		$this->approval_meta( array( Approval::STATUS_META => Approval::PENDING ) );
		$this->signed_in( 5 );
		WP_Mock::userFunction( 'wc_get_page_id', array( 'return' => 12 ) );
		WP_Mock::userFunction( 'get_permalink', array( 'return' => 'https://example.test/products/' ) );

		ob_start();
		( new PendingGate( new Approval() ) )->render();
		$html = (string) ob_get_clean();

			$this->assertStringContainsString( 'Your account is under review', $html );
			$this->assertStringContainsString( '<h2>', $html, 'The status belongs within the usable account page.' );
			$this->assertStringNotContainsString( '<h1>', $html );
			$this->assertStringContainsString( 'Under review', $html );
			$this->assertStringContainsString( 'linker-gate-badge is-pending', $html );
			$this->assertStringContainsString( 'https://example.test/products/', $html );
			$this->assertStringNotContainsString( 'Inquiry received', $html );
			$this->assertStringContainsString( 'linker-gate-btn is-primary', $html );
			$this->assertStringNotContainsString( 'style=', $html );
			$css = (string) file_get_contents( dirname( __DIR__, 4 ) . '/content/windpress/auth.css' );
			$this->assertStringContainsString( '.linker-gate {', $css );
			$this->assertStringContainsString( '.linker-gate-badge.is-pending', $css );
	}

	/**
	 * Other states have no pending status notice.
	 *
	 * @dataProvider other_states
	 * @param int    $id     User id.
	 * @param string $status Account state.
	 */
	public function test_other_accounts_have_no_pending_notice( int $id, string $status ): void {
		$this->approval_meta( array( Approval::STATUS_META => $status ) );
		$this->signed_in( $id );

		ob_start();
		( new PendingGate( new Approval() ) )->render();
		$this->assertSame( '', (string) ob_get_clean() );
	}

	/**
	 * Accounts that must not see the pending notice.
	 *
	 * @return array<string, array{int, string}>
	 */
	public static function other_states(): array {
		return array(
			'guest'      => array( 0, Approval::PENDING ),
			'approved'   => array( 5, Approval::APPROVED ),
			'restricted' => array( 5, Approval::RESTRICTED ),
			'rejected'   => array( 5, Approval::REJECTED ),
			'staff'      => array( 6, Approval::APPROVED ),
		);
	}
}
