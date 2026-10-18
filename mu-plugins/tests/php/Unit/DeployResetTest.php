<?php
/**
 * Tests for the deploy's one-time opcode-cache reset.
 *
 * @package Linker\Mu
 */

declare( strict_types = 1 );

namespace Linker\Mu\Tests\Unit;

use Linker\Mu\DeployReset;
use PHPUnit\Framework\TestCase;

// phpcs:disable WordPress.WP.AlternativeFunctions -- this test runs outside WordPress and writes real token files.

require_once dirname( __DIR__, 3 ) . '/linker-deploy-reset.php';

/**
 * Only the deploy, holding the one-time token it wrote on the host, can clear
 * the cache, and only once (#308).
 *
 * @covers \Linker\Mu\DeployReset
 */
final class DeployResetTest extends TestCase {

	/**
	 * The token file of this test.
	 *
	 * @var string
	 */
	private string $file = '';

	/**
	 * How many times the reset ran.
	 *
	 * @var int
	 */
	private int $resets = 0;

	/**
	 * A token file of this test's own.
	 */
	protected function setUp(): void {
		parent::setUp();
		$this->file   = sys_get_temp_dir() . '/linker-deploy-reset-' . bin2hex( random_bytes( 4 ) ) . '.token';
		$this->resets = 0;
		file_put_contents( $this->file, "s3cret-token\n" );
	}

	/**
	 * Remove what the test left.
	 */
	protected function tearDown(): void {
		if ( is_file( $this->file ) ) {
			unlink( $this->file );
		}
		parent::tearDown();
	}

	/**
	 * The reset under test, counted.
	 */
	private function reset(): bool {
		++$this->resets;
		return true;
	}

	/**
	 * An ordinary request is not a reset request: nothing runs, the token stays.
	 */
	public function test_an_ordinary_request_is_left_alone(): void {
		$outcome = DeployReset::decide( array( 'REQUEST_METHOD' => 'GET' ), $this->file, fn(): bool => $this->reset() );

		self::assertNull( $outcome );
		self::assertSame( 0, $this->resets );
		self::assertFileExists( $this->file );
	}

	/**
	 * A wrong token changes nothing and keeps the real token for the deploy.
	 */
	public function test_a_wrong_token_is_refused_and_the_token_kept(): void {
		$server  = array(
			'REQUEST_METHOD'              => 'POST',
			'HTTP_X_LINKER_OPCACHE_RESET' => 'guess',
		);
		$outcome = DeployReset::decide( $server, $this->file, fn(): bool => $this->reset() );

		self::assertNull( $outcome );
		self::assertSame( 0, $this->resets );
		self::assertFileExists( $this->file );
	}

	/**
	 * The right token resets once and is gone, so a replay does nothing.
	 */
	public function test_the_right_token_resets_once(): void {
		$server = array(
			'REQUEST_METHOD'              => 'POST',
			'HTTP_X_LINKER_OPCACHE_RESET' => 's3cret-token',
		);

		self::assertSame( 'done', DeployReset::decide( $server, $this->file, fn(): bool => $this->reset() ) );
		self::assertSame( 1, $this->resets );
		self::assertFileDoesNotExist( $this->file );

		self::assertNull( DeployReset::decide( $server, $this->file, fn(): bool => $this->reset() ) );
		self::assertSame( 1, $this->resets );
	}

	/**
	 * A GET with the right token is not enough: the deploy posts.
	 */
	public function test_a_get_with_the_token_does_nothing(): void {
		$server = array(
			'REQUEST_METHOD'              => 'GET',
			'HTTP_X_LINKER_OPCACHE_RESET' => 's3cret-token',
		);

		self::assertNull( DeployReset::decide( $server, $this->file, fn(): bool => $this->reset() ) );
		self::assertSame( 0, $this->resets );
	}

	/**
	 * Without a token file there is nothing to match, whatever is sent.
	 */
	public function test_no_token_file_means_no_reset(): void {
		unlink( $this->file );
		$server = array(
			'REQUEST_METHOD'              => 'POST',
			'HTTP_X_LINKER_OPCACHE_RESET' => '',
		);

		self::assertNull( DeployReset::decide( $server, $this->file, fn(): bool => $this->reset() ) );
		self::assertSame( 0, $this->resets );
	}

	/**
	 * A host without the opcode cache answers so, and the token is still used up.
	 */
	public function test_an_unavailable_cache_is_reported(): void {
		$server = array(
			'REQUEST_METHOD'              => 'POST',
			'HTTP_X_LINKER_OPCACHE_RESET' => 's3cret-token',
		);

		self::assertSame( 'unavailable', DeployReset::decide( $server, $this->file, static fn(): bool => false ) );
		self::assertFileDoesNotExist( $this->file );
	}
}
