<?php
/**
 * Tests for the test-mode rewrite of every outgoing mail path.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Mail;

use Linker\Commerce\Mail\TestMode;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * The seam is the wp_mail filter, the last arguments a caller can still change
 * before WordPress builds the message. While the switch is on, every path that
 * reaches wp_mail() — a direct call, a WooCommerce email, the old plugin's VAT
 * review mail, and the copies that plugin queues because the business inbox was
 * a recipient — leaves with the tester address alone.
 *
 * @covers \Linker\Commerce\Mail\TestMode
 */
final class RewriteTest extends TestCase {

	/**
	 * Options by name.
	 *
	 * @var array<string, mixed>
	 */
	private array $options = array();

	/**
	 * Callbacks of the wp_mail filter, in the order WordPress would run them.
	 *
	 * @var list<array{0: callable, 1: int}>
	 */
	private array $filters = array();

	/**
	 * An in-memory option store and the WordPress address rule.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::userFunction( 'get_option', array( 'return' => fn ( string $name, $default_value = false ) => $this->options[ $name ] ?? $default_value ) );
		WP_Mock::userFunction( 'sanitize_email', array( 'return' => static fn ( string $email ): string => str_contains( $email, '@' ) ? trim( $email ) : '' ) );
		WP_Mock::userFunction(
			'is_email',
			array( 'return' => static fn ( string $email ): string|false => 1 === preg_match( '/^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/', $email ) ? $email : false )
		);
	}

	/**
	 * While the switch is on, every path's wp_mail() arguments name the tester
	 * address and nothing else.
	 *
	 * @dataProvider paths
	 *
	 * @param array<string, mixed> $args The arguments a path hands to wp_mail().
	 */
	public function test_every_path_reaches_only_the_tester( array $args ): void {
		$this->options[ TestMode::OPTION ] = 'tester@example.test';
		$this->hook( ( new TestMode() )->rewrite( ... ) );

		$rewritten = $this->apply( $args );

		$this->assertSame( array( 'tester@example.test' ), $this->addresses( $rewritten['to'] ?? array() ) );
		$this->assertSame( array(), $this->copies( $rewritten['headers'] ?? array() ), 'Cc and Bcc are dropped, not redirected.' );
	}

	/**
	 * The paths that left the instance: the old plugin's VAT review mail, the
	 * copies it queues for the three owner inboxes, a customer approval mail,
	 * and a team notification that already carries a blind copy.
	 *
	 * @return array<string, array{0: array<string, mixed>}>
	 */
	public function paths(): array {
		return array(
			'the old plugin VAT review mail'        => array(
				array(
					'to'      => array( 'sales@de-linker.com' ),
					'subject' => 'Linker VAT check needs review: DE123456789',
					'message' => 'A Linker partner VAT check needs review.',
					'headers' => array(),
				),
			),
			'a copy the old plugin queues for an owner inbox' => array(
				array(
					'to'      => '857558227@qq.com',
					'subject' => 'Linker VAT check needs review: DE123456789',
					'message' => 'A Linker partner VAT check needs review.',
					'headers' => array(),
				),
			),
			'the other owner copies'                => array(
				array(
					'to'      => array( 'chester@de-linker.com', 'sales@sunriverinverter.com' ),
					'subject' => 'Linker VAT check needs review: DE123456789',
					'message' => 'A Linker partner VAT check needs review.',
					'headers' => array(),
				),
			),
			'a customer approval mail'              => array(
				array(
					'to'      => 'buyer@example.test',
					'subject' => 'Your partner account is approved',
					'message' => '<p>Approved</p>',
					'headers' => array( 'Content-Type: text/html; charset=UTF-8' ),
				),
			),
			'a team notification with a blind copy' => array(
				array(
					'to'      => 'sales@de-linker.com',
					'subject' => 'New customer: Example GmbH',
					'message' => '<p>Registered</p>',
					'headers' => "Bcc: archive@example.test\r\nContent-Type: text/html; charset=UTF-8",
				),
			),
		);
	}

	/**
	 * While the switch is off the same paths keep the recipients they were given.
	 */
	public function test_off_leaves_every_path_alone(): void {
		$this->hook( ( new TestMode() )->rewrite( ... ) );

		$args = array(
			'to'      => array( 'sales@de-linker.com' ),
			'subject' => 'Linker VAT check needs review: DE123456789',
			'message' => 'A Linker partner VAT check needs review.',
			'headers' => array( 'Bcc: 857558227@qq.com' ),
		);

		$this->assertSame( $args, $this->apply( $args ) );
	}

	/**
	 * While the switch is on, the legacy plugin's copy queue is taken off
	 * wp_mail, so a business notification is not fanned out into one message
	 * per owner inbox before the rewrite runs.
	 */
	public function test_the_switch_silences_the_legacy_copy_queue(): void {
		$this->options[ TestMode::OPTION ] = 'tester@example.test';
		$queued                            = array();
		$other                             = static function ( array $args ): array {
			return $args;
		};
		$queue                             = static function ( array $args ) use ( &$queued ): array {
			// The call the silence looks for in a closure's body. The stub is
			// loaded below, before this closure runs; its result is unused.
			$queued[] = tv_b2b_queue_business_mail_copies( $args )['to'] ?? '';
			return $args;
		};
		// phpcs:disable WordPress.WP.GlobalVariablesOverride.Prohibited -- the test's own hook table.
		$GLOBALS['wp_filter']['wp_mail'] = (object) array(
			'callbacks' => array(
				100 => array(
					'tv_b2b_queue_business_mail_copies' => array( 'function' => 'tv_b2b_queue_business_mail_copies' ),
					'spl_queue'                         => array( 'function' => $queue ),
					'spl_other'                         => array( 'function' => $other ),
				),
			),
		);

		if ( ! function_exists( 'tv_b2b_queue_business_mail_copies' ) ) {
			require_once __DIR__ . '/legacy-copy-queue-stub.php';
		}

		( new TestMode() )->silence_copy_queues();

		$callbacks = $GLOBALS['wp_filter']['wp_mail']->callbacks[100];
		$this->assertArrayNotHasKey( 'tv_b2b_queue_business_mail_copies', $callbacks );
		$this->assertCount( 1, $callbacks, 'A filter that does not queue copies stays.' );
		$this->assertSame( $other, array_values( $callbacks )[0]['function'] );

		foreach ( $callbacks as $registered ) {
			$registered['function']( array( 'to' => 'sales@de-linker.com' ) );
		}
		$this->assertSame( array(), $queued, 'The closure that queues the owner copies no longer runs.' );
	}

	/**
	 * Subject, body, content type and attachments survive the rewrite.
	 */
	public function test_the_rewrite_keeps_the_message(): void {
		$this->options[ TestMode::OPTION ] = 'tester@example.test';
		$this->hook( ( new TestMode() )->rewrite( ... ) );

		$rewritten = $this->apply(
			array(
				'to'          => 'buyer@example.test',
				'subject'     => 'Your partner account is approved',
				'message'     => '<p>Approved</p>',
				'headers'     => array( 'Content-Type: text/html; charset=UTF-8', 'Bcc: archive@example.test' ),
				'attachments' => array( '/tmp/proforma.pdf' ),
			)
		);

		$this->assertSame( 'Your partner account is approved', $rewritten['subject'] );
		$this->assertSame( '<p>Approved</p>', $rewritten['message'] );
		$this->assertSame( array( '/tmp/proforma.pdf' ), $rewritten['attachments'] );
		$this->assertSame( array( 'Content-Type: text/html; charset=UTF-8' ), $this->lines( $rewritten['headers'] ) );
	}

	/**
	 * Registers a wp_mail filter the way WordPress does, at the given priority.
	 *
	 * @param callable $callback Callback.
	 * @param int      $priority Priority.
	 */
	private function hook( callable $callback, int $priority = 10 ): void {
		$this->filters[] = array( $callback, $priority );
	}

	/**
	 * Runs the registered filters over one wp_mail() call's arguments.
	 *
	 * @param array<string, mixed> $args Arguments.
	 * @return array<string, mixed>
	 */
	private function apply( array $args ): array {
		usort( $this->filters, static fn ( array $left, array $right ): int => $left[1] <=> $right[1] );
		foreach ( $this->filters as $filter ) {
			$args = $filter[0]( $args );
		}
		return $args;
	}

	/**
	 * Bare addresses of a wp_mail() To value.
	 *
	 * @param mixed $to To.
	 * @return list<string>
	 */
	private function addresses( mixed $to ): array {
		$found = array();
		foreach ( $this->lines( is_string( $to ) ? str_replace( ',', "\n", $to ) : $to ) as $line ) {
			if ( 1 === preg_match( '/<([^>]+)>/', $line, $match ) ) {
				$line = $match[1];
			}
			if ( '' !== $line ) {
				$found[] = $line;
			}
		}
		return $found;
	}

	/**
	 * Addresses named by Cc or Bcc headers.
	 *
	 * @param mixed $headers Headers.
	 * @return list<string>
	 */
	private function copies( mixed $headers ): array {
		$found = array();
		foreach ( $this->lines( $headers ) as $header ) {
			$name = strtolower( ltrim( $header ) );
			if ( str_starts_with( $name, 'cc:' ) || str_starts_with( $name, 'bcc:' ) ) {
				$found = array_merge( $found, $this->addresses( trim( substr( $header, strpos( $header, ':' ) + 1 ) ) ) );
			}
		}
		return $found;
	}

	/**
	 * Header or address lines of a string or a list.
	 *
	 * @param mixed $value Value.
	 * @return list<string>
	 */
	private function lines( mixed $value ): array {
		if ( is_array( $value ) ) {
			$parts = $value;
		} elseif ( is_string( $value ) ) {
			$parts = explode( "\n", str_replace( array( "\r\n", "\r" ), "\n", $value ) );
		} else {
			return array();
		}
		$lines = array();
		foreach ( $parts as $part ) {
			$part = trim( (string) $part );
			if ( '' !== $part ) {
				$lines[] = $part;
			}
		}
		return $lines;
	}
}
