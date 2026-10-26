<?php
/**
 * Private historical input reads cannot expose another account or old results.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

require_once dirname( __DIR__, 4 ) . '/linker-commerce/vendor/autoload.php';

use Linker\Commerce\Account\SavedSolutions;
use Linker\Tools\Planner\Principal;
use Linker\Tools\Planner\SavedSolutionSource;
use WP_Error;
use WP_Mock;
use WP_Mock\Tools\TestCase;
use WP_Post;

/**
 * Historical input reads remain private and do not import calculated results.
 *
 * @covers \Linker\Tools\Planner\SavedSolutionSource
 */
final class SavedSolutionSourceTest extends TestCase {

	/**
	 * The archive is input-only and remains private after ownership/status changes.
	 */
	public function test_only_active_owner_can_read_original_inputs_without_old_results(): void {
		$user  = 5;
		$post  = new WP_Post(
			(object) array(
				'ID'          => 45,
				'post_type'   => SavedSolutions::POST_TYPE,
				'post_status' => 'private',
				'post_author' => '5',
				'post_title'  => 'Original project',
			)
		);
		$input = array(
			'annual_kwh' => 4500,
			'heat_pump'  => true,
			'extra'      => array( 'preserved' => true ),
		);
     // phpcs:ignore WordPress.WP.AlternativeFunctions.json_encode_json_encode -- Deterministic JSON fixture codec without a WordPress runtime.
		$raw = (string) json_encode(
			array(
				'kind'     => 'residential',
				'input'    => $input,
				'snapshot' => array( 'old_result' => 987 ),
			)
		);
		WP_Mock::userFunction(
			'get_current_user_id',
			array(
				'return' => static function () use ( &$user ): int {
					return $user;
				},
			)
		);
		WP_Mock::userFunction(
			'get_post',
			array(
				'args'   => array( 45 ),
				'return' => $post,
			)
		);
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'args'   => array( 45, SavedSolutions::DESIGN_META, true ),
				'return' => $raw,
			)
		);
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'args'   => array( 45, SavedSolutions::ITEMS_META, true ),
				'return' => '[{"product_id":1946,"quantity":1}]',
			)
		);
		WP_Mock::userFunction( '__', array( 'return' => static fn ( string $value ): string => $value ) );
     // phpcs:ignore WordPress.WP.AlternativeFunctions.json_encode_json_encode -- Native encoder fixture without the WordPress runtime.
		WP_Mock::userFunction( 'wp_json_encode', array( 'return' => static fn( $value ) => json_encode( $value ) ) );
		$read    = new SavedSolutionSource();
		$command = array(
			'schema_version' => 1,
			'solution_id'    => 45,
		);
		$source  = $read->read( new Principal( 'user', 'wp:1:user:5' ), $command );
		$this->assertIsArray( $source );
     // phpcs:ignore WordPress.WP.AlternativeFunctions.json_encode_json_encode -- Deterministic JSON fixture codec without a WordPress runtime.
		$this->assertEquals( json_decode( (string) json_encode( $input ) ), $source['input'] );
		$this->assertSame( hash( 'sha256', $raw ), $source['source_sha256'] );
		$this->assertArrayNotHasKey( 'snapshot', $source );
		$this->assertInstanceOf( WP_Error::class, $read->read( new Principal( 'guest', 'guest5' ), $command ) );
		$user = 6;
		$this->assertInstanceOf( WP_Error::class, $read->read( new Principal( 'user', 'wp:1:user:6' ), $command ) );
		$user              = 5;
		$post->post_status = 'trash';
		$this->assertInstanceOf( WP_Error::class, $read->read( new Principal( 'user', 'wp:1:user:5' ), $command ) );
		$this->assertConditionsMet();
	}
}
