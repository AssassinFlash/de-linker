<?php
/**
 * The linker/read-solution ability on the abilities REST route.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Abilities\ReadSolution;
use Linker\Commerce\Account\PrivateFiles;
use Linker\Commerce\Account\SavedSolutions;
use Linker\Tools\Genie\UserContext;
use WP_REST_Request;

/**
 * The design report's "Ask Genie" hands Genie a saved solution's id (#496).
 * This is the route that reads it: a guest is refused (401), another customer's
 * solution is refused (403), an unknown one is 404, and the owner gets the
 * figures from the stored historical snapshot without recalculation. The engine is a pre_http_request double; no outside call is made.
 *
 * @coversNothing
 */
final class ReadSolutionRestTest extends IntegrationTestCase {

	/**
	 * Currency marks and the amount the engine result would carry if a price leaked.
	 */
	private const MONEY = '/(?:€|\bEUR\b|1[.,]680)/';

	/**
	 * The engine's answer for the stored design, as the service reads it.
	 *
	 * @var array<string, mixed>
	 */
	private const RESULT = array(
		'status'   => 'solution',
		'yield'    => array(
			'kwh_year_range' => array(
				'low'  => 10034,
				'high' => 12164,
			),
			'kwh_year_mean'  => 11190,
		),
		'storage'  => array(
			'recommended' => true,
			'basis'       => array( array( 'text' => '2 kWp per MWh, at least 0.5' ) ),
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
			'inverter_rules' => array( array( 'text' => '3-phase, as selected' ) ),
			'battery'        => array(
				'product'  => array(
					'id'    => 3611,
					'brand' => 'GoodWe',
					'model' => 'GW6.0-BAT-D-G20',
				),
				'quantity' => 1,
				'release'  => array(
					'verdict'    => 'released',
					'conditions' => array(),
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
	 * The engine's URL in the instance option, and every request the double saw.
	 *
	 * @var list<array{url: string, body: array<string, mixed>}>
	 */
	private array $engine = array();

	/**
	 * What the engine double answers.
	 *
	 * @var array<string, mixed>
	 */
	private array $engine_result = self::RESULT;

	/**
	 * The engine option before the test, restored afterwards.
	 *
	 * @var mixed
	 */
	private mixed $engine_option = false;

	/**
	 * The engine double, and the option it reads.
	 */
	protected function setUp(): void {
		parent::setUp();
		$this->engine_option = get_option( 'linker_engine_url' );
		update_option( 'linker_engine_url', 'http://engine.test:8443', false );
		$this->later(
			function (): void {
				if ( false === $this->engine_option ) {
					delete_option( 'linker_engine_url' );
				} else {
					update_option( 'linker_engine_url', $this->engine_option, false );
				}
			}
		);
		$http = function ( $pre, $args, $url ) {
			if ( false !== $pre || 'http://engine.test:8443/design/residential' !== $url ) {
				return $pre;
			}
			$this->engine[] = array(
				'url'  => (string) $url,
				'body' => (array) json_decode( (string) ( $args['body'] ?? '' ), true ),
			);
			return array(
				'headers'  => array(),
				'body'     => (string) wp_json_encode( $this->engine_result ),
				'response' => array(
					'code'    => 200,
					'message' => 'OK',
				),
				'cookies'  => array(),
				'filename' => null,
			);
		};
		add_filter( 'pre_http_request', $http, 10, 3 );
		$this->later(
			static function () use ( $http ): void {
				remove_filter( 'pre_http_request', $http, 10 );
			}
		);
	}

	/** The engine fixture must preserve other requests and existing native responses. */
	public function test_engine_double_preserves_other_requests_and_prior_responses(): void {
		$prior = array(
			'response' => array( 'code' => 200 ),
			'body'     => '{"valid":true}',
		);
		// phpcs:disable WooCommerce.Commenting.CommentHooks, WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- Drive WordPress's actual HTTP short-circuit filter without issuing any network request.
		$this->assertFalse( apply_filters( 'pre_http_request', false, array(), 'http://127.0.0.1:9/unrelated' ) );
		$this->assertSame( $prior, apply_filters( 'pre_http_request', $prior, array(), 'http://127.0.0.1:9/unrelated' ) );
		$this->assertSame( $prior, apply_filters( 'pre_http_request', $prior, array(), 'http://engine.test:8443/design/residential' ) );
		// phpcs:enable
		$this->assertSame( array(), $this->engine );
	}

	/**
	 * A guest is refused by the permission callback; the Genie token path is the
	 * customer's own identity.
	 */
	public function test_a_guest_is_refused_and_the_owners_token_signs_in(): void {
		$owner = $this->customer();
		$id    = $this->saved( $owner->get_id() );

		$this->as_user( 0 );
		$this->assertSame( 401, $this->read( $id )['status'] );

		$token = $this->token( $owner );
		$open  = $this->read( $id, 'en', $token );
		$this->assertSame( 200, $open['status'] );
		$this->assertSame( $id, $open['data']['id'] );
		$this->assertSame( 12164.0, $open['data']['yield']['kwh_year_high'] );
	}

	/**
	 * Another customer's solution is refused, and no engine call is made for it.
	 */
	public function test_another_customers_solution_is_forbidden(): void {
		$owner = $this->customer();
		$other = $this->customer();
		$id    = $this->saved( $owner->get_id() );

		$this->as_user( $other->get_id() );
		$refused = $this->read( $id );
		$this->assertSame( 403, $refused['status'] );
		$this->assertSame( array(), $this->engine );
	}

	/**
	 * An unknown id is 404; a missing id is the route's own 400.
	 */
	public function test_an_unknown_or_missing_solution_is_refused(): void {
		$owner = $this->customer();
		$this->as_user( $owner->get_id() );
		$this->assertSame( 404, $this->read( 999999 )['status'] );
		$this->assertSame( 400, $this->read( 0 )['status'] );
		$this->assertSame( array(), $this->engine );
	}

	/**
	 * The owner's own solution: the engine runs the stored design in the turn's
	 * language, and the answer passes the ability's own output schema.
	 */
	public function test_the_owner_reads_the_figures_from_the_stored_design(): void {
		$owner = $this->customer();
		$id    = $this->saved( $owner->get_id() );
		$this->as_user( $owner->get_id() );

		$read = $this->read( $id, 'de' );

		$this->assertSame( 200, $read['status'], (string) wp_json_encode( $read['data'] ) );
		$this->assertSame( array(), $this->engine );
		$this->assertTrue( $read['data']['historical'] );
		$data = $read['data'];
		$this->assertSame( 'solution', $data['status'] );
		$this->assertSame( 10034.0, $data['yield']['kwh_year_low'] );
		$this->assertSame( 5.8, $data['storage']['usable_kwh'] );
		$this->assertSame( 0.6142, $data['metrics']['autarky_low'] );
		$this->assertSame( 'GoodWe GW10K-ETA-G20', $data['selected']['inverter'] );
		$this->assertSame( array( '3-phase, as selected', '2 kWp per MWh, at least 0.5' ), $data['basis'] );
		$this->assertSame( 3556, $data['items'][0]['product_id'] );
	}

	/**
	 * A stored design that no longer produces a complete solution is a 200 with
	 * the yield, no selection and no metrics: the null fields pass the schema.
	 */
	public function test_a_design_without_a_solution_passes_the_schema(): void {
		$owner = $this->customer();
		$id    = $this->saved( $owner->get_id() );
		$this->as_user( $owner->get_id() );
		$this->engine_result['status']   = 'no_candidate';
		$this->engine_result['metrics']  = null;
		$this->engine_result['selected'] = null;
		$design                          = json_decode( (string) get_post_meta( $id, SavedSolutions::DESIGN_META, true ), true );
		$design['snapshot']              = $this->engine_result;
		update_post_meta( $id, SavedSolutions::DESIGN_META, wp_slash( (string) wp_json_encode( $design ) ) );

		$read = $this->read( $id );

		$this->assertSame( 200, $read['status'], (string) wp_json_encode( $read['data'] ) );
		$this->assertSame( 'no_candidate', $read['data']['status'] );
		$this->assertNull( $read['data']['metrics'] );
		$this->assertNull( $read['data']['selected'] );
		$this->assertSame( 12164.0, $read['data']['yield']['kwh_year_high'] );
	}

	/**
	 * No price and no amount of money in the answer, whatever the engine returned.
	 */
	public function test_no_amount_of_money_reaches_the_route(): void {
		$owner = $this->customer();
		$id    = $this->saved( $owner->get_id() );
		$this->as_user( $owner->get_id() );

		$read = $this->read( $id );

		$this->assertSame( 200, $read['status'] );
		$this->assertDoesNotMatchRegularExpression( self::MONEY, $read['raw'] );
	}

	/** Legacy records do not invoke an engine or read a withdrawn product. */
	public function test_missing_snapshot_is_explicit_and_preserves_the_saved_record(): void {
		$owner = $this->customer();
		$id    = $this->saved( $owner->get_id() );
		$this->as_user( $owner->get_id() );
		$design = json_decode( (string) get_post_meta( $id, SavedSolutions::DESIGN_META, true ), true );
		unset( $design['snapshot'] );
		update_post_meta( $id, SavedSolutions::DESIGN_META, wp_slash( (string) wp_json_encode( $design ) ) );
		$this->assertSame( 422, $this->read( $id )['status'] );
		$this->assertSame( array(), $this->engine );
		$this->assertNotNull( get_post( $id ) );
	}

	/**
	 * One saved solution of $customer with the design the engine can reproduce.
	 *
	 * @param int $customer Account.
	 */
	private function saved( int $customer ): int {
		$solutions = new SavedSolutions( new PrivateFiles( SavedSolutions::REPORTS_DIRECTORY ), '/plugin/templates/' );
		$id        = $solutions->save(
			$customer,
			'GoodWe GW10K-ETA-G20, 80538',
			array(
				array(
					'product_id' => 3556,
					'quantity'   => 1,
				),
				array(
					'product_id' => 3611,
					'quantity'   => 1,
				),
			),
			array(
				'snapshot' => self::RESULT + array( 'price' => '€ 1,680.00' ),
				'kind'     => 'residential',
				'input'    => array(
					'locale'     => 'en',
					'plz'        => '80538',
					'annual_kwh' => 5000,
					'pv_kwp'     => 10,
					'phase'      => 3,
				),
			)
		);
		$this->assertNotSame( 0, $id );
		$this->later(
			static function () use ( $id ): void {
				wp_delete_post( $id, true );
			}
		);
		return $id;
	}

	/**
	 * A token for $customer, minted and then signed out, so the header is the
	 * only identity on the next request.
	 *
	 * @param \WC_Customer $customer Account.
	 */
	private function token( \WC_Customer $customer ): string {
		$this->as_user( $customer->get_id() );
		$token = ( new UserContext() )->mint();
		$this->as_user( 0 );
		$this->assertNotSame( '', $token );
		return $token;
	}

	/**
	 * The raw route answer.
	 *
	 * @param int         $id    Solution.
	 * @param string      $lang  Turn language.
	 * @param string|null $token Customer token, or null for the current session.
	 * @return array{status: int, raw: string, data: array<string, mixed>}
	 */
	private function read( int $id, string $lang = 'en', ?string $token = null ): array {
		$request = new WP_REST_Request( 'GET', '/wp-abilities/v1/abilities/' . ReadSolution::NAME . '/run' );
		$request->set_query_params(
			array(
				'input' => array(
					'solution_id' => $id,
					'lang'        => $lang,
				),
			)
		);
		if ( null !== $token ) {
			$this->assertFalse( is_user_logged_in(), 'A token is ignored while a cookie session exists.' );
			$request->set_header( UserContext::HEADER, $token );
		}
		$server   = rest_get_server();
		$response = $server->dispatch( $request );
		$data     = $response->get_data();
		$raw      = wp_json_encode( $server->response_to_data( $response, false ) );
		$this->assertIsArray( $data );
		$this->assertIsString( $raw );

		return array(
			'status' => $response->get_status(),
			'raw'    => (string) $raw,
			'data'   => $data,
		);
	}
}
