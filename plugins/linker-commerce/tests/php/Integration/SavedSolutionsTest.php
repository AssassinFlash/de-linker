<?php
/**
 * Historical saved records and retired design writes.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Account\PrivateFiles;
use Linker\Commerce\Account\SavedSolutions;
use Linker\Commerce\Account\SavedSolutionRemoval;
use Linker\Commerce\Registration\Approval;
use Linker\Commerce\Protection\Identity;
use WP_REST_Request;

/**
 * Existing records retain private removal/Undo; old design writes are retired.
 *
 * @coversNothing
 */
final class SavedSolutionsTest extends IntegrationTestCase {

	/** Owner removal and Undo preserve private data and report; other actors cannot write it. */
	public function test_removal_and_undo_preserve_private_data(): void {
		$owner = $this->customer()->get_id();
		$other = $this->customer()->get_id();
		$files = new PrivateFiles( SavedSolutions::REPORTS_DIRECTORY );
		$store = new SavedSolutions( $files, '' );
		$bytes = "%PDF-1.4\nowned transport fixture\n%%EOF";
		$id    = $store->save(
			$owner,
			'Removal fixture',
			array(),
			array(
				'kind'  => 'residential',
				'input' => array(),
			),
			$bytes
		);
		$keep  = $store->save( $other, 'Other owner fixture', array(), array(), $bytes );
		$this->later(
			static function () use ( $id, $keep ): void {
				wp_delete_post( $id, true );
				wp_delete_post( $keep, true );
			}
		);
		$path = $store->report_path( $id );
		$kept = $store->report_path( $keep );
		$this->assertFileExists( $path );
		$before  = get_post_meta( $id );
		$actions = new SavedSolutionRemoval();

		$this->as_user( $other );
		$this->assertInstanceOf( \WP_Error::class, $actions->remove( $id, wp_create_nonce( SavedSolutionRemoval::REMOVE . '_' . $id ) ) );
		$this->as_user( 0 );
		$this->assertInstanceOf( \WP_Error::class, $actions->remove( $id, wp_create_nonce( SavedSolutionRemoval::REMOVE . '_' . $id ) ) );
		$this->as_user( $owner );
		$this->assertInstanceOf( \WP_Error::class, $actions->remove( $id, 'invalid' ) );
		update_user_meta( $owner, Approval::STATUS_META, Approval::REJECTED );
		$this->assertInstanceOf( \WP_Error::class, $actions->remove( $id, wp_create_nonce( SavedSolutionRemoval::REMOVE . '_' . $id ) ) );
		update_user_meta( $owner, Approval::STATUS_META, Approval::APPROVED );
		$this->assertSame( 'private', get_post_status( $id ) );
		$this->assertSame( $before, get_post_meta( $id ) );

		$nonce = wp_create_nonce( SavedSolutionRemoval::REMOVE . '_' . $id );
		$this->assertTrue( $actions->remove( $id, $nonce ) );
		$this->assertTrue( $actions->remove( $id, $nonce ) );
		$this->assertSame( 'trash', get_post_status( $id ) );
		$this->assertSame( array(), $store->for_customer( $owner ) );
		$this->assertSame( $bytes, file_get_contents( $path ) );
		$this->as_user( $other );
		$this->assertInstanceOf( \WP_Error::class, $actions->restore( $id, wp_create_nonce( SavedSolutionRemoval::UNDO . '_' . $id ) ) );
		$this->as_user( $owner );
		$this->assertTrue( $actions->restore( $id, wp_create_nonce( SavedSolutionRemoval::UNDO . '_' . $id ) ) );
		$this->assertSame( 'private', get_post_status( $id ) );
		foreach ( $before as $key => $value ) {
			$this->assertSame( $value, get_post_meta( $id )[ $key ] );
		}
		$this->assertSame( $bytes, file_get_contents( $path ) );
		wp_delete_post( $id, true );
		$this->assertFileDoesNotExist( $path );
		$this->assertFileExists( $kept );
		$this->assertSame( 'private', get_post_status( $keep ) );
	}
	/** Native guest admission sees a browser cookie, as a real REST request does. */
	protected function setUp(): void {
		parent::setUp();
		$cookies                     = $_COOKIE;
		$_COOKIE[ Identity::COOKIE ] = bin2hex( random_bytes( 16 ) );
		$this->later(
			static function () use ( $cookies ): void {
				$_COOKIE = $cookies;
			}
		);
	}

	/** Public legacy writes cannot create records, including from cached clients. */
	public function test_retired_design_writes_leave_historical_records_intact(): void {
		$query  = array(
			'post_type'      => SavedSolutions::POST_TYPE,
			'post_status'    => 'any',
			'posts_per_page' => -1,
			'fields'         => 'ids',
		);
		$before = get_posts( $query );
		foreach ( array( '/linker/v1/solutions', '/linker/v1/solutions/draft' ) as $path ) {
			$response = rest_do_request( new WP_REST_Request( 'POST', $path ) );
			$this->assertSame( 410, $response->get_status() );
			$data = $response->get_data();
			$this->assertSame( 'linker_planner_required', $data['code'] );
		}
		$this->assertSame( $before, get_posts( $query ) );
	}
}
