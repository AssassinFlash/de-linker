<?php
/**
 * Fake credentials only: precedence, file parsing and unavailable files.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Unit\Translation;

use Linker\I18n\Translation\Credentials;
use WP_Mock\Tools\TestCase;

// phpcs:disable WordPress.WP.AlternativeFunctions, WordPress.PHP.DiscouragedPHPFunctions.runtime_configuration_putenv, WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- isolated fake process/config fixtures; previous values are restored without printing.

/**
 * Isolated fake process and file credentials.
 *
 * @covers \Linker\I18n\Translation\Credentials
 */
final class CredentialsTest extends TestCase {

	/** Temporary config directory.
	 *
	 * @var string
	 */
	private string $directory;
	/** Saved process value, never printed.
	 *
	 * @var string|false
	 */
	private string|false $previous_process;
	/**
	 * Existing process value, restored without printing it.
	 *
	 * @var mixed
	 */
	private $previous_environment;

	/**
	 * The config location is injected; the real HOME file is never read.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->previous_process     = getenv( 'DEEPSEEK_API_KEY' );
		$this->previous_environment = $_ENV['DEEPSEEK_API_KEY'] ?? null;
		putenv( 'DEEPSEEK_API_KEY' );
		unset( $_ENV['DEEPSEEK_API_KEY'] );
		$this->directory = sys_get_temp_dir() . '/i253-key-' . bin2hex( random_bytes( 8 ) );
		mkdir( $this->directory, 0700 );
	}

	/**
	 * Removes fake files and restores the process.
	 */
	public function tearDown(): void {
		if ( is_file( $this->directory . '/deepseek.env' ) ) {
			unlink( $this->directory . '/deepseek.env' );
		}
		rmdir( $this->directory );
		putenv( false === $this->previous_process ? 'DEEPSEEK_API_KEY' : 'DEEPSEEK_API_KEY=' . $this->previous_process );
		if ( null === $this->previous_environment ) {
			unset( $_ENV['DEEPSEEK_API_KEY'] );
		} else {
			$_ENV['DEEPSEEK_API_KEY'] = $this->previous_environment;
		}
		parent::tearDown();
	}

	/**
	 * Process env, then $_ENV, then the private file.
	 */
	public function test_credential_precedence(): void {
		file_put_contents( $this->directory . '/deepseek.env', "DEEPSEEK_API_KEY='file-key'\n" );
		$_ENV['DEEPSEEK_API_KEY'] = 'array-key';
		putenv( 'DEEPSEEK_API_KEY=process-key' );
		$this->assertSame( 'process-key', Credentials::deepseek_key( $this->directory ) );
		putenv( 'DEEPSEEK_API_KEY' );
		$this->assertSame( 'array-key', Credentials::deepseek_key( $this->directory ) );
		unset( $_ENV['DEEPSEEK_API_KEY'] );
		$this->assertSame( 'file-key', Credentials::deepseek_key( $this->directory ) );
	}

	/**
	 * An env file is data: unrelated assignments and shell commands do not run.
	 */
	public function test_file_is_parsed_without_execution_or_unrelated_values(): void {
		file_put_contents( $this->directory . '/deepseek.env', "# comment\nOTHER=value\nDEEPSEEK_API_KEY=\"fake=key\"\n" );
		$this->assertSame( 'fake=key', Credentials::deepseek_key( $this->directory ) );
		file_put_contents( $this->directory . '/deepseek.env', "OTHER=secret\n" );
		$this->assertSame( '', Credentials::deepseek_key( $this->directory ) );
	}

	/**
	 * Missing files and empty values do not make a client available.
	 */
	public function test_missing_or_empty_configuration(): void {
		$this->assertSame( '', Credentials::deepseek_key( $this->directory ) );
		$_ENV['DEEPSEEK_API_KEY'] = array();
		file_put_contents( $this->directory . '/deepseek.env', "DEEPSEEK_API_KEY=\"\"\n" );
		$this->assertSame( '', Credentials::deepseek_key( $this->directory ) );
	}

	/**
	 * A non-readable private file is unavailable without leaking its contents.
	 */
	public function test_unreadable_file_is_unavailable(): void {
		$path = $this->directory . '/deepseek.env';
		file_put_contents( $path, 'DEEPSEEK_API_KEY=fake-unreadable-key' );
		chmod( $path, 0000 );
		try {
			$this->assertSame( '', Credentials::deepseek_key( $this->directory ) );
		} finally {
			chmod( $path, 0600 );
		}
	}
}
