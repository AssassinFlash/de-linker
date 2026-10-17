<?php
/**
 * The digest reports missing internal authentication once.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Health;

use Linker\Commerce\Health\InternalMail;
use Linker\Commerce\Mail\InternalSmtp;
use Linker\Commerce\Tests\TestCase;

/**
 * Tests the digest block through its public entries interface.
 *
 * @covers \Linker\Commerce\Health\InternalMail
 */
final class InternalMailTest extends TestCase {

	/**
	 * Missing credentials produce one visible item, with no extra alert email.
	 */
	public function test_missing_credentials_are_visible_once_in_the_digest(): void {
		$this->plain_text();
		$block = new InternalMail( new InternalSmtp( '/nonexistent/linker-smtp-test.env' ) );
		$this->assertCount( 1, $block->entries() );
		$this->assertSame( 'Internal mail not authenticated.', $block->entries()[0]['label'] );
	}
}
