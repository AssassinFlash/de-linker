<?php
/**
 * Tests for the digest email.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Digest;

use Linker\Commerce\Digest\DigestEmail;
use Linker\Commerce\Registration\Approval;
use Linker\Commerce\Registration\PendingApprovals;
use Linker\Commerce\Settings\Options;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;
use WP_User;

/**
 * Tests for DigestEmail: the subject and heading, the date placeholder, and
 * the team mailbox as recipient with the blind copies.
 *
 * @covers \Linker\Commerce\Digest\DigestEmail
 * @covers \Linker\Commerce\Mail\TeamEmail
 */
final class DigestEmailTest extends TestCase {

	/**
	 * The digest goes to the team mailbox in the site's language, dated, with
	 * the blind copies; no reply-to (there is no customer to reply to).
	 */
	public function test_sends_dated_to_the_team_mailbox(): void {
		$this->plain_text();
		$this->reload_plugin_textdomain();
		WP_Mock::userFunction( 'plugin_dir_path', array( 'return' => '/plugin/' ) );
		WP_Mock::userFunction( 'sanitize_email', array( 'return' => static fn ( string $email ): string => $email ) );
		WP_Mock::userFunction( 'is_email', array( 'return' => static fn ( string $email ): bool => false !== filter_var( $email, FILTER_VALIDATE_EMAIL ) ) );
		$this->options(
			array(
				Options::TEAM_TO    => 'sales@de-linker.com',
				Options::NOTIFY_BCC => "one@example.test\ntwo@example.test",
				'WPLANG'            => '',
				'date_format'       => 'F j, Y',
			)
		);
		WP_Mock::userFunction(
			'wp_date',
			array(
				'return' => static fn ( string $format ): string => 'H:i' === $format ? '09:00' : 'October 11, 2026',
			)
		);
		$this->allow_locale_switch( 'en_US' );
		WP_Mock::expectAction( 'linker_test_email_sent', 'linker_digest', 'sales@sunriverinverter.com' );

		$email = new DigestEmail( '/plugin/linker-commerce.php', new Options() );
		$email->send_report( array() );

		$this->assertSame( 'linker_digest', $email->id );
		$this->assertSame( '/plugin/templates/', $email->template_base );
		$this->assertFalse( $email->is_customer_email() );
		$this->assertSame( 'October 11, 2026', $email->placeholders['{date}'] );
		$header = "Content-Type: text/html\r\nX-Linker-Internal: yes\r\nBcc: one@example.test, two@example.test\r\n";
		$this->filter_returns( 'woocommerce_email_headers', $header, array( $header, 'linker_digest', false, $email ) );
		$this->assertSame( $header, $email->get_headers() );
		$this->assertConditionsMet();
	}

	/**
	 * Subject and heading defaults; the subject carries the date placeholder.
	 */
	public function test_subject_and_heading(): void {
		$this->plain_text();
		$this->reload_plugin_textdomain();
		WP_Mock::userFunction( 'plugin_dir_path', array( 'return' => '/plugin/' ) );
		$this->options(
			array(
				Options::TEAM_TO => 'sales@de-linker.com',
				'WPLANG'         => '',
			)
		);

		$email = new DigestEmail( '/plugin/linker-commerce.php', new Options() );

		$this->assertSame( 'Daily digest, {date}', $email->get_default_subject() );
		$this->assertSame( 'Daily digest', $email->get_default_heading() );
		$this->assertSame( 'html', $email->get_email_type() );
		$this->assertSame( array( 'html' => 'HTML' ), $email->get_email_type_options() );
	}

	/**
	 * The presentation is added only while this email is rendering.
	 */
	public function test_styles_attach_only_to_the_digest(): void {
		$other = (object) array( 'id' => 'customer_note' );
		$this->assertSame( 'base', DigestEmail::append_styles( 'base', $other ) );

		$ours = (object) array( 'id' => 'linker_digest' );
		$css  = DigestEmail::append_styles( 'base', $ours );

		$this->assertStringContainsString( 'linker-digest-card', $css );
		$this->assertStringStartsWith( 'base', $css );
	}

	/**
	 * Decorative rows do not count as pending applications in the subject.
	 *
	 * @dataProvider account_sets
	 * @phpstan-param list<string> $states
	 * @param array $states Native approval states.
	 * @param int   $pending Number actually awaiting staff approval.
	 */
	public function test_summary_placeholder_builds_counts( array $states, int $pending ): void {
		$this->plain_text();
		$this->reload_plugin_textdomain();
		WP_Mock::userFunction( 'plugin_dir_path', array( 'return' => '/plugin/' ) );
		WP_Mock::userFunction( 'sanitize_email', array( 'return' => static fn ( string $email ): string => $email ) );
		WP_Mock::userFunction( 'is_email', array( 'return' => static fn ( string $email ): bool => false !== filter_var( $email, FILTER_VALIDATE_EMAIL ) ) );
		$this->options(
			array(
				Options::TEAM_TO              => 'sales@de-linker.com',
				'linker_commerce_team_locale' => 'zh_CN',
				'WPLANG'                      => '',
			)
		);
		WP_Mock::userFunction(
			'wp_date',
			array(
				'return' => static fn ( string $format ): string => 'H:i' === $format ? '09:00' : '2026年10月22日',
			)
		);
		$this->allow_locale_switch( 'zh_CN' );
		WP_Mock::expectAction( 'linker_test_email_sent', 'linker_digest', 'sales@sunriverinverter.com' );

		$users = array();
		foreach ( $states as $index => $state ) {
			$user                  = new WP_User();
			$user->ID              = $index + 1;
			$user->roles           = array( 'customer' );
			$user->display_name    = 'Fixture customer';
			$user->user_registered = '2026-10-23 08:00:00';
			$users[ $user->ID ]    = $user;
		}
		WP_Mock::userFunction( 'get_users', array( 'return' => array_values( $users ) ) );
		WP_Mock::userFunction( 'get_userdata', array( 'return' => static fn ( int $id ): ?WP_User => $users[ $id ] ?? null ) );
		WP_Mock::userFunction( 'get_user_meta', array( 'return' => static fn ( int $id, string $key ): string => Approval::STATUS_META === $key ? ( $states[ $id - 1 ] ?? '' ) : '' ) );
		WP_Mock::userFunction( 'get_current_blog_id', array( 'return' => 1 ) );
		WP_Mock::userFunction( 'wp_cache_get_last_changed', array( 'return' => 'fixture' ) );
		WP_Mock::userFunction( 'number_format_i18n', array( 'return' => static fn ( int $count ): string => (string) $count ) );
		WP_Mock::userFunction( 'mysql2date', array( 'return' => static fn ( string $format, string $date ): string => $date ) );
		WP_Mock::userFunction( 'admin_url', array( 'return' => 'https://example.test/wp-admin/' ) );
		WP_Mock::userFunction( 'add_query_arg', array( 'return' => 'https://example.test/wp-admin/?fixture=1' ) );
		$accounts = new PendingApprovals();

		$email = new DigestEmail( '/plugin/linker-commerce.php', new Options() );
		$email->send_report( array( $accounts ) );

		$this->assertSame( 0 === $pending ? '' : '：' . $pending . ' 个待审客户', $email->placeholders['{summary}'] );
		$this->assertSame( 'Accounts waiting for approval (' . $pending . ')', $accounts->title() );
		$this->assertConditionsMet();
	}

	/**
	 * Native pending applications and decorative restricted/empty rows.
	 *
	 * @return array<string, array{list<string>, int}>
	 */
	public static function account_sets(): array {
		return array(
			'empty'           => array( array(), 0 ),
			'restricted only' => array( array( Approval::RESTRICTED ), 0 ),
			'one pending'     => array( array( Approval::PENDING ), 1 ),
			'multiple mixed'  => array( array( Approval::PENDING, Approval::PENDING, Approval::RESTRICTED ), 2 ),
		);
	}
}
