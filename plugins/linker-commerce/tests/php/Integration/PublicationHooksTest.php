<?php
/**
 * Publication events preserve native metadata and ignore unrelated private stores.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Mail\Message;

/**
 * Real WordPress actions must observe persisted facts without replacing filter values.
 *
 * @coversNothing
 */
final class PublicationHooksTest extends IntegrationTestCase {
	/** Restore this fixture's pending marker after its own objects are removed. */
	protected function setUp(): void {
		parent::setUp();
		$pending = get_option( 'linker_publication_pending' );
		$this->later(
			static function () use ( $pending ): void {
				if ( false === $pending ) {
					delete_option( 'linker_publication_pending' );
				} else {
					update_option( 'linker_publication_pending', $pending, false );
				}
			}
		);
	}

	/** Queued mail writes must not query the independent publication scheduler. */
	public function test_private_mail_metadata_does_not_touch_publication_preparation(): void {
		$id = ( new JobStore() )->create( new Message( array( self::TESTER ), 'Synthetic hook fixture', 'Local fixture.', array(), array() ) );
		$this->assertGreaterThan( 0, $id );
		delete_option( 'linker_publication_pending' );
		$queries = 0;
		$observe = static function ( string $sql ) use ( &$queries ): string {
			if ( str_contains( $sql, 'actionscheduler_actions' ) ) {
				++$queries;
			}
			return $sql;
		};
		add_filter( 'query', $observe, 998 );
		try {
			update_post_meta( $id, '_linker_hook_fixture', 'private metadata' );
		} finally {
			remove_filter( 'query', $observe, 998 );
		}
		$this->assertSame( 0, $queries );
		$this->assertFalse( get_option( 'linker_publication_pending' ) );
		$this->assertSame( 'private metadata', get_post_meta( $id, '_linker_hook_fixture', true ) );
	}

	/** A real native metadata filter must retain the entire original array. */
	public function test_native_pdf_attachment_metadata_is_preserved(): void {
		$id       = $this->attachment();
		$metadata = array(
			'width'  => 40,
			'height' => 20,
			'file'   => 'publication-hook-fixture.pdf',
			'sizes'  => array(),
		);
		delete_option( 'linker_publication_pending' );
		$this->assertNotFalse( wp_update_attachment_metadata( $id, $metadata ) );
		$this->assertSame( $metadata, get_post_meta( $id, '_wp_attachment_metadata', true ) );
		$this->assertTrue( get_option( 'linker_publication_pending' ) );
		delete_option( 'linker_publication_pending' );
		update_post_meta( $id, '_linker_document_public', '0' );
		$this->assertTrue( get_option( 'linker_publication_pending' ) );
	}

	/** All native product metadata operations continue to notify the queue. */
	public function test_product_metadata_and_status_transitions_still_notify(): void {
		$product = $this->product( '100' );
		$id      = $product->get_id();
		delete_option( 'linker_publication_pending' );
		add_post_meta( $id, '_linker_hook_fixture', 'first', true );
		$this->assertTrue( get_option( 'linker_publication_pending' ) );
		delete_option( 'linker_publication_pending' );
		update_post_meta( $id, '_linker_hook_fixture', 'second' );
		$this->assertTrue( get_option( 'linker_publication_pending' ) );
		delete_option( 'linker_publication_pending' );
		delete_post_meta( $id, '_linker_hook_fixture' );
		$this->assertTrue( get_option( 'linker_publication_pending' ) );
		delete_option( 'linker_publication_pending' );
		$product->set_status( 'draft' );
		$product->save();
		$this->assertTrue( get_option( 'linker_publication_pending' ) );
	}

	/**
	 * An attachment without an original-file path cannot delete an existing upload.
	 */
	private function attachment(): int {
		$id = wp_insert_attachment(
			array(
				'post_title'     => 'Publication hook fixture',
				'post_mime_type' => 'application/pdf',
				'post_status'    => 'inherit',
			),
			false,
			0,
			true
		);
		$this->assertIsInt( $id );
		$this->later(
			static function () use ( $id ): void {
				wp_delete_attachment( $id, true );
			}
		);
		return $id;
	}
}
