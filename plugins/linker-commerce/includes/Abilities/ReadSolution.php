<?php
/**
 * Ability linker/read-solution.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Abilities;

use Linker\Commerce\Account\SavedSolutions;
use Linker\Commerce\Health\Monitor;
use WP_Error;

/**
 * The current customer's own saved solution, read for Genie (#496).
 *
 * The design report's "Ask Genie" saves the solution through the configurator's
 * own route first and opens the dock with the saved solution's id in the page
 * context. This ability is the one reader of that reference: it loads the
 * solution post, checks that the post is the current customer's own (another
 * customer's id answers 403, as every account route does; a guest answers 401
 * through the permission callback), re-runs the sizing engine from the stored
 * `_linker_solution_design` in the turn's language, and returns the figures and
 * the selection basis. The service tags the figures as `solution.nK` and
 * hydrates them (#234's page precedent).
 *
 * The engine address is the instance option `linker_engine_url`, the one
 * Health\Monitor checks and Configurator\EngineProxy forwards to; the pinned
 * certificate rides the site's HTTP API (mu-plugins/linker-engine-pin.php).
 * The answer carries no price and no amount of money: the saved description
 * holds products and quantities, the engine holds no prices, and a product card
 * the answer shows takes its price line from the customer's own product ability.
 * Logged-in only; the token path is `UserContext::ABILITIES`.
 */
final class ReadSolution {

	/**
	 * Ability name.
	 */
	public const NAME = 'linker/read-solution';

	/**
	 * The engine path that reproduces a residential design.
	 */
	private const ENGINE_PATH = '/design/residential';

	/**
	 * Seconds to wait for the engine. The Genie service waits 20 s for one
	 * ability call (abilities.py), and one turn has the shell's 60 s budget;
	 * fifteen keeps the call inside the first. The configurator's browser route
	 * allows the engine 60 s because a roof outline can spend seconds in the
	 * LoD2 source, which this read never asks for.
	 */
	private const TIMEOUT_SECONDS = 15.0;

	/**
	 * The languages the engine writes its result in.
	 */
	private const LANGUAGES = array( 'en', 'de' );

	/**
	 * Sets up the ability.
	 *
	 * @param SavedSolutions                                                  $solutions The store of saved solutions.
	 * @param callable(string, string): (array{0:int,1:string}|WP_Error)|null $fetch Optional engine double for tests: URL, JSON body.
	 */
	public function __construct(
		private readonly SavedSolutions $solutions,
		private mixed $fetch = null
	) {}

	/**
	 * Arguments for wp_register_ability(), apart from the category.
	 *
	 * @return array<string, mixed>
	 */
	public function args(): array {
		$range = array(
			'type'                 => 'object',
			'properties'           => array(
				'low'  => array( 'type' => 'number' ),
				'high' => array( 'type' => 'number' ),
			),
			'required'             => array( 'low', 'high' ),
			'additionalProperties' => false,
		);
		$item  = array(
			'type'                 => 'object',
			'properties'           => array(
				'product_id' => array( 'type' => 'integer' ),
				'quantity'   => array( 'type' => 'integer' ),
				'model'      => array( 'type' => 'string' ),
			),
			'required'             => array( 'product_id', 'quantity', 'model' ),
			'additionalProperties' => false,
		);

		return array(
			'label'               => __( 'Read a saved solution', 'linker-commerce' ),
			'description'         => __( 'Returns this account\'s own saved solution: its figures from the sizing engine and its selection basis. Requires a logged-in customer; another customer\'s solution is refused.', 'linker-commerce' ),
			'input_schema'        => array(
				'type'                 => 'object',
				'properties'           => array(
					'solution_id' => array(
						'type'    => 'integer',
						'minimum' => 1,
					),
					'lang'        => array(
						'type' => 'string',
						'enum' => self::LANGUAGES,
					),
				),
				'required'             => array( 'solution_id' ),
				'additionalProperties' => false,
			),
			'output_schema'       => array(
				'type'                 => 'object',
				'properties'           => array(
					'id'       => array( 'type' => 'integer' ),
					'title'    => array( 'type' => 'string' ),
					'created'  => array( 'type' => 'string' ),
					'status'   => array(
						'type' => 'string',
						'enum' => array( 'solution', 'no_candidate' ),
					),
					'yield'    => array(
						'type'                 => 'object',
						'properties'           => array(
							'kwh_year_low'  => array( 'type' => 'number' ),
							'kwh_year_high' => array( 'type' => 'number' ),
							'kwh_year_mean' => array( 'type' => 'number' ),
						),
						'required'             => array( 'kwh_year_low', 'kwh_year_high', 'kwh_year_mean' ),
						'additionalProperties' => false,
					),
					'storage'  => array(
						'type'                 => 'object',
						'properties'           => array(
							'usable_kwh'  => array( 'type' => array( 'number', 'null' ) ),
							'recommended' => array( 'type' => 'boolean' ),
						),
						'required'             => array( 'usable_kwh', 'recommended' ),
						'additionalProperties' => false,
					),
					'metrics'  => array(
						'type'       => array( 'object', 'null' ),
						'properties' => array(
							'autarky_low'           => array( 'type' => 'number' ),
							'autarky_high'          => array( 'type' => 'number' ),
							'self_consumption_low'  => array( 'type' => 'number' ),
							'self_consumption_high' => array( 'type' => 'number' ),
						),
					),
					'selected' => array(
						'type'       => array( 'object', 'null' ),
						'properties' => array(
							'inverter'         => array( 'type' => 'string' ),
							'battery'          => array( 'type' => array( 'string', 'null' ) ),
							'battery_quantity' => array( 'type' => array( 'integer', 'null' ) ),
						),
					),
					'basis'    => array(
						'type'  => 'array',
						'items' => array( 'type' => 'string' ),
					),
					'warnings' => array(
						'type'  => 'array',
						'items' => array( 'type' => 'string' ),
					),
					'items'    => array(
						'type'  => 'array',
						'items' => $item,
					),
				),
				'required'             => array( 'id', 'title', 'created', 'status', 'yield', 'storage', 'metrics', 'selected', 'basis', 'warnings', 'items' ),
				'additionalProperties' => false,
			),
			'execute_callback'    => array( $this, 'execute' ),
			'permission_callback' => array( $this, 'can_execute' ),
			'meta'                => RestMeta::readonly(),
		);
	}

	/**
	 * Only a logged-in customer may read a saved solution; a guest answers 401.
	 */
	public function can_execute(): bool {
		return is_user_logged_in();
	}

	/**
	 * This account's own saved solution, read from the stored design.
	 *
	 * @param array<string, mixed>|object $input solution_id, and lang when the turn is German.
	 * @return array<string, mixed>|WP_Error
	 */
	public function execute( $input = array() ) {
		$input = (array) $input;
		$id    = (int) ( $input['solution_id'] ?? 0 );
		$lang  = isset( $input['lang'] ) && in_array( $input['lang'], self::LANGUAGES, true ) ? (string) $input['lang'] : 'en';
		if ( $id < 1 ) {
			return new WP_Error( 'linker_solution_id', __( 'A solution ID is required.', 'linker-commerce' ), array( 'status' => 400 ) );
		}
		if ( ! is_user_logged_in() ) {
			return new WP_Error( 'linker_solution_login', __( 'Sign in to read your saved solution.', 'linker-commerce' ), array( 'status' => 401 ) );
		}
		$owner = $this->solutions->owner( $id );
		if ( $owner < 1 ) {
			return new WP_Error( 'linker_solution_missing', __( 'The saved solution was not found.', 'linker-commerce' ), array( 'status' => 404 ) );
		}
		if ( get_current_user_id() !== $owner ) {
			return new WP_Error( 'linker_solution_owner', __( 'This saved solution belongs to another account.', 'linker-commerce' ), array( 'status' => 403 ) );
		}
		$design = json_decode( (string) get_post_meta( $id, SavedSolutions::DESIGN_META, true ), true );
		$stored = is_array( $design ) && is_array( $design['input'] ?? null ) ? $design['input'] : array();
		if ( ! is_array( $design ) || 'residential' !== ( $design['kind'] ?? '' ) || array() === $stored ) {
			return new WP_Error( 'linker_solution_unsupported', __( 'This saved solution cannot be read by the sizing engine.', 'linker-commerce' ), array( 'status' => 422 ) );
		}
		// The engine writes its rule texts and warnings in the request's language:
		// the stored input keeps the design, and the turn decides the language.
		$stored['locale'] = $lang;
		$body             = wp_json_encode( $stored );
		if ( ! is_string( $body ) ) {
			return new WP_Error( 'linker_solution_encoding', __( 'The saved design could not be read.', 'linker-commerce' ), array( 'status' => 500 ) );
		}
		$answer = $this->call( $this->engine_url(), $body );
		if ( $answer instanceof WP_Error ) {
			return new WP_Error( 'linker_solution_engine', __( 'The sizing engine did not answer.', 'linker-commerce' ), array( 'status' => 502 ) );
		}
		list( $status, $payload ) = $answer;
		$result                   = json_decode( $payload, true );
		if ( $status >= 400 && $status < 500 ) {
			// The engine refused the stored design (its 422): a deterministic
			// input problem, not an outage. A 5xx is the outage. The service
			// treats 5xx as a failed turn and 4xx as the caller's answer, so
			// this stays non-fatal and the model can say it cannot read it.
			return new WP_Error( 'linker_solution_unsupported', __( 'This saved solution cannot be read by the sizing engine.', 'linker-commerce' ), array( 'status' => 422 ) );
		}
		if ( $status < 200 || $status >= 300 || ! is_array( $result ) ) {
			return new WP_Error( 'linker_solution_engine', __( 'The sizing engine did not answer.', 'linker-commerce' ), array( 'status' => 502 ) );
		}

		return $this->output( $id, $result );
	}

	/**
	 * The engine's address, from the instance option Health\Monitor checks.
	 */
	private function engine_url(): string {
		return rtrim( (string) get_option( Monitor::ENGINE_URL_OPTION, '' ), '/' ) . self::ENGINE_PATH;
	}

	/**
	 * One POST to the engine, or the test double.
	 *
	 * @param string $url  Absolute engine URL.
	 * @param string $body JSON body.
	 * @return array{0:int,1:string}|WP_Error
	 */
	private function call( string $url, string $body ) {
		if ( is_callable( $this->fetch ) ) {
			return ( $this->fetch )( $url, $body );
		}
		// #521: a saved design read can recompute. The trusted Tools adapter
		// shares sizing quotas/deduplication; no browser can supply this permit.
		$mode_environment = getenv( 'LINKER_PUBLIC_PROTECTION_MODE' );
		$guard_mode       = defined( 'LINKER_PUBLIC_PROTECTION_MODE' ) ? constant( 'LINKER_PUBLIC_PROTECTION_MODE' ) : ( is_string( $mode_environment ) ? $mode_environment : 'off' );
		if ( 'off' !== $guard_mode ) {
			/**
			 * Server-only account-owned engine request; Tools returns the native result.
			 *
			 * @since 0.1.0
			 */
			return apply_filters( 'linker_tools_engine_request', new WP_Error( 'linker_engine_admission', 'Sizing could not be admitted.' ), $url, $body ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- Trusted Tools resource seam.
		}
		$response = wp_remote_post(
			$url,
			array(
				'timeout' => self::TIMEOUT_SECONDS,
				'headers' => array(
					'Content-Type'              => 'application/json',
					'X-Linker-Service-Token'    => defined( 'LINKER_GENIE_SERVICE_TOKEN' ) ? (string) constant( 'LINKER_GENIE_SERVICE_TOKEN' ) : '',
					'X-Linker-Resource-Subject' => \Linker\Commerce\Protection\Identity::account( get_current_user_id() ),
				),
				'body'    => $body,
			)
		);
		if ( is_wp_error( $response ) ) {
			return $response;
		}
		return array(
			(int) wp_remote_retrieve_response_code( $response ),
			(string) wp_remote_retrieve_body( $response ),
		);
	}

	/**
	 * The engine's result reduced to what Genie reads: figures, basis, items.
	 * Only these fields are copied, so no price or amount can ride along.
	 *
	 * @param int                  $id     Solution id.
	 * @param array<string, mixed> $result Engine's ResidentialResult.
	 * @return array<string, mixed>
	 */
	private function output( int $id, array $result ): array {
		$yield    = is_array( $result['yield'] ?? null ) ? $result['yield'] : array();
		$range    = is_array( $yield['kwh_year_range'] ?? null ) ? $yield['kwh_year_range'] : array();
		$storage  = is_array( $result['storage'] ?? null ) ? $result['storage'] : array();
		$metrics  = is_array( $result['metrics'] ?? null ) ? $result['metrics'] : null;
		$selected = is_array( $result['selected'] ?? null ) ? $result['selected'] : null;
		$items    = array();
		foreach ( $this->solutions->items( $id ) as $item ) {
			$items[] = array(
				'product_id' => $item['product_id'],
				'quantity'   => $item['quantity'],
				'model'      => $this->item_model( $selected, $item['product_id'] ),
			);
		}
		$battery = is_array( $selected['battery'] ?? null ) ? $selected['battery'] : null;

		return array(
			'id'       => $id,
			// The stored title, not get_the_title(): a private post's title is
			// prefixed "Private:" for display, and that prefix is not the
			// customer's name for their solution.
			'title'    => (string) get_post_field( 'post_title', $id ),
			'created'  => (string) get_post_time( 'Y-m-d', false, $id ),
			'status'   => 'solution' === ( $result['status'] ?? '' ) ? 'solution' : 'no_candidate',
			'yield'    => array(
				'kwh_year_low'  => (float) ( $range['low'] ?? 0 ),
				'kwh_year_high' => (float) ( $range['high'] ?? 0 ),
				'kwh_year_mean' => (float) ( $yield['kwh_year_mean'] ?? 0 ),
			),
			'storage'  => array(
				'usable_kwh'  => $metrics && is_numeric( $metrics['usable_kwh'] ?? null ) ? (float) $metrics['usable_kwh'] : null,
				'recommended' => (bool) ( $storage['recommended'] ?? false ),
			),
			'metrics'  => $metrics ? array(
				'autarky_low'           => (float) ( $this->range_value( $metrics, 'autarky_range', 'low' ) ),
				'autarky_high'          => (float) ( $this->range_value( $metrics, 'autarky_range', 'high' ) ),
				'self_consumption_low'  => (float) ( $this->range_value( $metrics, 'self_consumption_range', 'low' ) ),
				'self_consumption_high' => (float) ( $this->range_value( $metrics, 'self_consumption_range', 'high' ) ),
			) : null,
			'selected' => $selected ? array(
				'inverter'         => $this->product_name( $selected['inverter'] ?? null ),
				'battery'          => $battery ? $this->product_name( $battery['product'] ?? null ) : null,
				'battery_quantity' => $battery ? (int) ( $battery['quantity'] ?? 0 ) : null,
			) : null,
			'basis'    => $this->basis( $selected, $storage ),
			'warnings' => $this->texts( $result['warnings'] ?? null ),
			'items'    => $items,
		);
	}

	/**
	 * The selection basis the design report shows: the inverter's rules, the
	 * storage sizing's rules, and the battery's release conditions.
	 *
	 * @param array<string, mixed>|null $selected The engine's selection, null for no candidate.
	 * @param array<string, mixed>      $storage  The engine's storage result.
	 * @return list<string>
	 */
	private function basis( ?array $selected, array $storage ): array {
		$lines          = array();
		$inverter_rules = is_array( $selected['inverter_rules'] ?? null ) ? $selected['inverter_rules'] : array();
		$storage_rules  = is_array( $storage['basis'] ?? null ) ? $storage['basis'] : array();
		foreach ( array( $inverter_rules, $storage_rules ) as $rules ) {
			foreach ( $rules as $rule ) {
				if ( is_array( $rule ) && is_string( $rule['text'] ?? null ) && '' !== $rule['text'] ) {
					$lines[] = $rule['text'];
				}
			}
		}
		$battery = is_array( $selected['battery'] ?? null ) ? $selected['battery'] : array();
		$release = is_array( $battery['release'] ?? null ) ? $battery['release'] : array();
		return array_merge( $lines, $this->texts( $release['conditions'] ?? null ) );
	}

	/**
	 * The model of a saved item, from the engine's Stückliste lines; '' when the
	 * engine no longer selects that product.
	 *
	 * @param array<string, mixed>|null $selected The engine's selection.
	 * @param int                       $product_id Saved product.
	 */
	private function item_model( ?array $selected, int $product_id ): string {
		foreach ( is_array( $selected['lines'] ?? null ) ? $selected['lines'] : array() as $line ) {
			if ( is_array( $line ) && is_array( $line['product'] ?? null ) && (int) ( $line['product']['id'] ?? 0 ) === $product_id ) {
				return $this->product_name( $line['product'] );
			}
		}
		return '';
	}

	/**
	 * A product reference as the report writes it: "Brand Model".
	 *
	 * @param mixed $product A ProductRef.
	 */
	private function product_name( mixed $product ): string {
		$product = is_array( $product ) ? $product : array();
		return trim( (string) ( $product['brand'] ?? '' ) . ' ' . (string) ( $product['model'] ?? '' ) );
	}

	/**
	 * One low/high value of a range in the engine's result.
	 *
	 * @param array<string, mixed> $metrics The engine's metrics.
	 * @param string               $range   The range's key.
	 * @param string               $end     `low` or `high`.
	 */
	private function range_value( array $metrics, string $range, string $end ): float {
		$found = is_array( $metrics[ $range ] ?? null ) ? $metrics[ $range ] : array();
		return is_numeric( $found[ $end ] ?? null ) ? (float) $found[ $end ] : 0.0;
	}

	/**
	 * The strings of a list, ignoring everything that is not one.
	 *
	 * @param mixed $value A list from the engine's result.
	 * @return list<string>
	 */
	private function texts( mixed $value ): array {
		$texts = array();
		foreach ( is_array( $value ) ? $value : array() as $item ) {
			if ( is_string( $item ) && '' !== $item ) {
				$texts[] = $item;
			}
		}
		return $texts;
	}
}
