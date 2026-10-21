<?php
/**
 * Tests for linker/read-solution.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Abilities;

use Linker\Commerce\Abilities\ReadSolution;
use Linker\Commerce\Account\PrivateFiles;
use Linker\Commerce\Account\SavedSolutions;
use Linker\Commerce\Tests\TestCase;
use WP_Error;
use WP_Mock;
use WP_Post;

/**
 * Tests for ReadSolution.
 *
 * @covers \Linker\Commerce\Abilities\ReadSolution
 */
final class ReadSolutionTest extends TestCase {

	/**
	 * Currency marks, and the amount the engine fixture would carry if a price
	 * leaked. A rule's bare "1.00" is a value, not money.
	 */
	private const MONEY = '/(?:€|\bEUR\b|1[.,]680)/';

	/**
	 * The stored configurator design of the saved solution.
	 */
	private const DESIGN = array(
		'kind'  => 'residential',
		'input' => array(
			'locale'     => 'en',
			'plz'        => '80538',
			'annual_kwh' => 5000,
			'pv_kwp'     => 10,
			'phase'      => 3,
		),
	);

	/**
	 * The engine's answer for that design, reduced to the fields the reader copies.
	 *
	 * @var array<string, mixed>
	 */
	private const RESULT = array(
		'status'   => 'solution',
		'yield'    => array(
			'kwh_year_range' => array(
				'low'  => 10034.0,
				'high' => 12164.0,
			),
			'kwh_year_mean'  => 11190.0,
		),
		'storage'  => array(
			'recommended' => true,
			'basis'       => array(
				array( 'text' => '2 kWp per MWh, at least 0.5' ),
				array( 'text' => '1.5 kWh × 10 kWp = 15 kWh' ),
			),
		),
		'metrics'  => array(
			'usable_kwh'             => 5.8,
			'autarky_range'          => array(
				'low'  => 0.6142,
				'high' => 0.7142,
			),
			'self_consumption_range' => array(
				'low'  => 0.3279,
				'high' => 0.3767,
			),
		),
		'selected' => array(
			'inverter'       => array(
				'id'    => 3556,
				'brand' => 'GoodWe',
				'model' => 'GW10K-ETA-G20',
			),
			'inverter_rules' => array(
				array( 'text' => '3-phase, as selected' ),
				array( 'text' => '1.00, at most 2.00 per the manufacturer' ),
			),
			'battery'        => array(
				'product'  => array(
					'id'    => 3611,
					'brand' => 'GoodWe',
					'model' => 'GW6.0-BAT-D-G20',
				),
				'quantity' => 1,
				'release'  => array(
					'verdict'    => 'released',
					'conditions' => array( 'The datasheet lists 12 pcs (p. 3).' ),
				),
			),
			'lines'          => array(
				array(
					'role'    => 'inverter',
					'product' => array(
						'id'    => 3556,
						'brand' => 'GoodWe',
						'model' => 'GW10K-ETA-G20',
					),
				),
				array(
					'role'    => 'battery',
					'product' => array(
						'id'    => 3611,
						'brand' => 'GoodWe',
						'model' => 'GW6.0-BAT-D-G20',
					),
				),
			),
		),
		'warnings' => array(),
	);

	/**
	 * Translation returns its source.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
	}

	/**
	 * A guest cannot run the ability.
	 */
	public function test_guests_cannot_run_it(): void {
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => false ) );
		$this->assertFalse( ( new ReadSolution( $this->store() ) )->can_execute() );
	}

	/**
	 * A signed-in customer may run the ability.
	 */
	public function test_customers_can_run_it(): void {
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => true ) );
		$this->assertTrue( ( new ReadSolution( $this->store() ) )->can_execute() );
	}

	/**
	 * Without an ID the ability refuses before touching the store.
	 */
	public function test_a_solution_id_is_required(): void {
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => true ) );
		$error = ( new ReadSolution( $this->store() ) )->execute( array() );
		$this->assertInstanceOf( WP_Error::class, $error );
		$this->assertSame( 'linker_solution_id', $error->get_error_code() );
		$this->assertSame( 400, $error->get_error_data()['status'] );
	}

	/**
	 * Another customer's saved solution answers 403, never its data.
	 */
	public function test_another_customers_solution_is_refused(): void {
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => true ) );
		WP_Mock::userFunction(
			'get_current_user_id',
			array(
				'times'  => '0+',
				'return' => 6,
			)
		);
		$this->solution( 45, 5, self::DESIGN );
		$error = ( new ReadSolution( $this->store() ) )->execute( array( 'solution_id' => 45 ) );
		$this->assertInstanceOf( WP_Error::class, $error );
		$this->assertSame( 403, $error->get_error_data()['status'] );
		$this->assertStringContainsString( 'another account', $error->get_error_message() );
	}

	/**
	 * A solution that does not exist answers 404.
	 */
	public function test_an_unknown_solution_is_not_found(): void {
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => true ) );
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 5 ) );
		WP_Mock::userFunction( 'get_post', array( 'return' => null ) );
		$error = ( new ReadSolution( $this->store() ) )->execute( array( 'solution_id' => 46 ) );
		$this->assertInstanceOf( WP_Error::class, $error );
		$this->assertSame( 404, $error->get_error_data()['status'] );
	}

	/**
	 * A stored design the residential engine cannot reproduce answers 422.
	 */
	public function test_a_non_residential_design_is_unsupported(): void {
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => true ) );
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 5 ) );
		$this->solution(
			45,
			5,
			array(
				'kind'  => 'commercial',
				'input' => array( 'kva' => 100 ),
			)
		);
		$error = ( new ReadSolution( $this->store() ) )->execute( array( 'solution_id' => 45 ) );
		$this->assertInstanceOf( WP_Error::class, $error );
		$this->assertSame( 422, $error->get_error_data()['status'] );
	}

	/**
	 * The customer's own solution: the engine runs the stored design in the turn's
	 * language, and the answer carries the figures, the basis and the saved items.
	 */
	public function test_reads_the_owners_solution_from_the_stored_design(): void {
		$this->owner_signed_in();
		$this->solution( 45, 5, self::DESIGN );
		$seen_url  = '';
		$seen_body = '';
		$read      = new ReadSolution(
			$this->store(),
			static function ( string $url, string $body ) use ( &$seen_url, &$seen_body ): array {
				$seen_url  = $url;
				$seen_body = $body;
				return array( 200, (string) json_encode( self::RESULT ) );
			}
		);

		$answer = $read->execute(
			array(
				'solution_id' => '45',
				'lang'        => 'de',
			)
		);

		$this->assertIsArray( $answer );
		$this->assertSame( 'https://engine.test:8443/design/residential', $seen_url );
		$sent = (array) json_decode( $seen_body, true );
		$this->assertSame( self::DESIGN['input']['plz'], $sent['plz'] );
		$this->assertSame( 'de', $sent['locale'], 'the turn language, not the stored one' );

		$this->assertSame( 45, $answer['id'] );
		$this->assertSame( 'GoodWe GW10K-ETA-G20, 80538', $answer['title'] );
		$this->assertSame( '2026-10-21', $answer['created'] );
		$this->assertSame( 'solution', $answer['status'] );
		$this->assertSame( 10034.0, $answer['yield']['kwh_year_low'] );
		$this->assertSame( 12164.0, $answer['yield']['kwh_year_high'] );
		$this->assertSame( 5.8, $answer['storage']['usable_kwh'] );
		$this->assertSame( 0.6142, $answer['metrics']['autarky_low'] );
		$this->assertSame( 'GoodWe GW10K-ETA-G20', $answer['selected']['inverter'] );
		$this->assertSame( 'GoodWe GW6.0-BAT-D-G20', $answer['selected']['battery'] );
		$this->assertSame( 1, $answer['selected']['battery_quantity'] );
		$this->assertSame(
			array(
				'3-phase, as selected',
				'1.00, at most 2.00 per the manufacturer',
				'2 kWp per MWh, at least 0.5',
				'1.5 kWh × 10 kWp = 15 kWh',
				'The datasheet lists 12 pcs (p. 3).',
			),
			$answer['basis']
		);
		$this->assertSame(
			array(
				array(
					'product_id' => 3556,
					'quantity'   => 1,
					'model'      => 'GoodWe GW10K-ETA-G20',
				),
				array(
					'product_id' => 3611,
					'quantity'   => 1,
					'model'      => 'GoodWe GW6.0-BAT-D-G20',
				),
			),
			$answer['items']
		);
		$this->assertSame( array(), $answer['warnings'] );
	}

	/**
	 * No price and no amount of money rides in the answer, whatever the engine
	 * returned: the reader copies named fields only.
	 */
	public function test_no_amount_of_money_reaches_the_answer(): void {
		$this->owner_signed_in();
		$this->solution( 45, 5, self::DESIGN );
		$result                      = self::RESULT;
		$result['price']             = '€ 1,680.00';
		$result['selected']['price'] = '€ 1,680.00';
		$result['items']             = array( array( 'price' => '€ 1,680.00' ) );
		$read                        = new ReadSolution(
			$this->store(),
			static function ( string $url, string $body ) use ( $result ): array {
				unset( $url, $body );
				return array( 200, (string) json_encode( $result ) );
			}
		);

		$answer = $read->execute( array( 'solution_id' => 45 ) );

		$this->assertIsArray( $answer );
		$this->assertDoesNotMatchRegularExpression( self::MONEY, (string) json_encode( $answer ) );
	}

	/**
	 * A design with no complete solution still names the yield and says so.
	 */
	public function test_a_design_without_a_solution_is_reported_as_such(): void {
		$this->owner_signed_in();
		$this->solution( 45, 5, self::DESIGN );
		$result             = self::RESULT;
		$result['status']   = 'no_candidate';
		$result['metrics']  = null;
		$result['selected'] = null;
		$read               = new ReadSolution(
			$this->store(),
			static function ( string $url, string $body ) use ( $result ): array {
				unset( $url, $body );
				return array( 200, (string) json_encode( $result ) );
			}
		);

		$answer = $read->execute( array( 'solution_id' => 45 ) );

		$this->assertIsArray( $answer );
		$this->assertSame( 'no_candidate', $answer['status'] );
		$this->assertNull( $answer['metrics'] );
		$this->assertNull( $answer['selected'] );
		$this->assertSame( 12164.0, $answer['yield']['kwh_year_high'] );
	}

	/**
	 * The engine's failure is a 502 the service logs, never a solution.
	 */
	public function test_an_engine_failure_is_an_upstream_error(): void {
		$this->owner_signed_in();
		$this->solution( 45, 5, self::DESIGN );
		$cases = array(
			array(
				static function ( string $url, string $body ): WP_Error {
					unset( $url, $body );
					return new WP_Error( 'http_request_failed', 'timeout' );
				},
				'linker_solution_engine',
				502,
			),
			array(
				static function ( string $url, string $body ): array {
					unset( $url, $body );
					return array( 503, '{"detail":"yield_unavailable"}' );
				},
				'linker_solution_engine',
				502,
			),
			array(
				static function ( string $url, string $body ): array {
					unset( $url, $body );
					return array( 200, 'not json' );
				},
				'linker_solution_engine',
				502,
			),
			array(
				// The engine now refuses a stored design it no longer accepts:
				// a deterministic answer, not a failed turn (the service's 4xx).
				static function ( string $url, string $body ): array {
					unset( $url, $body );
					return array( 422, '{"detail":{"error":"invalid_input","field":"plz"}}' );
				},
				'linker_solution_unsupported',
				422,
			),
		);
		foreach ( $cases as $case ) {
			$error = ( new ReadSolution( $this->store(), $case[0] ) )->execute( array( 'solution_id' => 45 ) );
			$this->assertInstanceOf( WP_Error::class, $error );
			$this->assertSame( $case[1], $error->get_error_code() );
			$this->assertSame( $case[2], $error->get_error_data()['status'] );
		}
	}

	/**
	 * The store of a test.
	 */
	private function store(): SavedSolutions {
		return new SavedSolutions( new PrivateFiles( SavedSolutions::REPORTS_DIRECTORY ), '/plugin/templates/' );
	}

	/**
	 * The signed-in customer 5, the language option and the engine host.
	 */
	private function owner_signed_in(): void {
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => true ) );
		WP_Mock::userFunction(
			'get_current_user_id',
			array(
				'times'  => '0+',
				'return' => 5,
			)
		);
		WP_Mock::userFunction( 'get_option', array( 'return' => static fn ( string $key, $fallback = false ) => 'linker_engine_url' === $key ? 'https://engine.test:8443/' : $fallback ) );
		WP_Mock::userFunction( 'get_post_field', array( 'return' => 'GoodWe GW10K-ETA-G20, 80538' ) );
		WP_Mock::userFunction( 'get_post_time', array( 'return' => '2026-10-21' ) );
		WP_Mock::userFunction( 'wp_json_encode', array( 'return' => static fn ( $value ) => json_encode( $value ) ) );
	}

	/**
	 * A saved solution post of customer $owner with $design, and its saved items.
	 *
	 * @param int                  $id     Solution.
	 * @param int                  $owner  Its customer.
	 * @param array<string, mixed> $design The stored design.
	 */
	private function solution( int $id, int $owner, array $design ): void {
		$meta = array(
			SavedSolutions::DESIGN_META => (string) json_encode( $design ),
			SavedSolutions::ITEMS_META  => (string) json_encode(
				array(
					array(
						'product_id' => 3556,
						'quantity'   => 1,
					),
					array(
						'product_id' => 3611,
						'quantity'   => 1,
					),
				)
			),
		);
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'times'  => '0+',
				'return' => static fn ( int $post_id, string $key ) => $id === $post_id ? ( $meta[ $key ] ?? '' ) : '',
			)
		);
		$post = new WP_Post(
			(object) array(
				'ID'          => $id,
				'post_type'   => SavedSolutions::POST_TYPE,
				'post_author' => (string) $owner,
			)
		);
		WP_Mock::userFunction(
			'get_post',
			array(
				'times'  => '0+',
				'return' => static fn ( int $post_id ) => $id === $post_id ? $post : null,
			)
		);
	}
}
