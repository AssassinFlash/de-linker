<?php
/**
 * Ability linker/size-hint.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Abilities;

/**
 * Opens the Solution Configurator with the stated fields pre-filled. The
 * engine itself runs on the configurator page (docs/specs/14-solution-configurator.md);
 * this ability only builds that URL. Backup values follow the configurator's
 * residential form: none / needed / needed_accessory_ok.
 */
final class SizeHint {

	/**
	 * Ability name.
	 */
	public const NAME = 'linker/size-hint';

	/**
	 * Path of the Solution Configurator (docs/specs/12-site-chrome.md: the page
	 * moved to this address on the owner's 2026-10-12 ruling; the old one
	 * redirects).
	 */
	private const PATH = '/solution-configurator/';

	/**
	 * Backup values the configurator form accepts.
	 */
	private const BACKUP = array( 'none', 'needed', 'needed_accessory_ok' );

	/**
	 * Arguments for wp_register_ability(), apart from the category.
	 *
	 * @return array<string, mixed>
	 */
	public function args(): array {
		return array(
			'label'               => __( 'Open the Solution Configurator with these inputs', 'linker-commerce' ),
			'description'         => __( 'Returns a short summary and the Solution Configurator URL with the given fields pre-filled.', 'linker-commerce' ),
			'input_schema'        => array(
				'type'                 => 'object',
				'properties'           => array(
					'pv_kwp'          => array(
						'type'    => 'number',
						'minimum' => 0,
					),
					'annual_load_kwh' => array(
						'type'    => 'number',
						'minimum' => 0,
					),
					'phase'           => array(
						'type' => 'integer',
						'enum' => array( 1, 3 ),
					),
					'backup'          => array(
						'type' => 'string',
						'enum' => self::BACKUP,
					),
					'plz'             => array(
						'type'    => 'string',
						'pattern' => '^[0-9]{5}$',
					),
					'lang'            => array(
						'type' => 'string',
						'enum' => array( 'en', 'de' ),
					),
				),
				'additionalProperties' => false,
				// A GET with no parameters means "empty input" (the abilities
				// REST controller reads null without a declared default).
				'default'              => array(),
			),
			'output_schema'       => array(
				'type'                 => 'object',
				'properties'           => array(
					'summary'          => array(
						'type'        => 'string',
						'description' => __( 'What will be pre-filled on the configurator.', 'linker-commerce' ),
					),
					'configurator_url' => array(
						'type'        => 'string',
						'description' => __( 'Solution Configurator URL with the fields as query arguments.', 'linker-commerce' ),
					),
				),
				'required'             => array( 'summary', 'configurator_url' ),
				'additionalProperties' => false,
			),
			'execute_callback'    => array( $this, 'execute' ),
			'permission_callback' => array( $this, 'can_execute' ),
			'meta'                => RestMeta::readonly(),
		);
	}

	/**
	 * Anyone may open the configurator.
	 */
	public function can_execute(): bool {
		return true;
	}

	/**
	 * The configurator URL with the given fields as query arguments.
	 *
	 * `lang` is accepted and ignored. It is not a configurator field, so it
	 * never appears in the URL (#365, #393).
	 *
	 * @param array<string, mixed>|object $input Optional pv_kwp, annual_load_kwh, phase, backup, plz, lang.
	 * @return array{summary: string, configurator_url: string}
	 */
	public function execute( $input = array() ): array {
		$input = (array) $input;
		unset( $input['lang'] );
		$query = array();
		$parts = array();
		if ( is_numeric( $input['pv_kwp'] ?? null ) && (float) $input['pv_kwp'] > 0 ) {
			$query['pv_kwp'] = (string) (float) $input['pv_kwp'];
			$parts[]         = $query['pv_kwp'] . ' kWp PV';
		}
		if ( is_numeric( $input['annual_load_kwh'] ?? null ) && (float) $input['annual_load_kwh'] > 0 ) {
			$query['annual_kwh'] = (string) (float) $input['annual_load_kwh'];
			$parts[]             = $query['annual_kwh'] . ' kWh/year';
		}
		if ( isset( $input['phase'] ) && in_array( (int) $input['phase'], array( 1, 3 ), true ) ) {
			$query['phase'] = (string) (int) $input['phase'];
			$parts[]        = 1 === (int) $input['phase'] ? 'single-phase' : 'three-phase';
		}
		if ( is_string( $input['backup'] ?? null ) && in_array( $input['backup'], self::BACKUP, true ) ) {
			$query['backup'] = $input['backup'];
			$parts[]         = 'backup=' . $input['backup'];
		}
		if ( is_string( $input['plz'] ?? null ) && 1 === preg_match( '/^[0-9]{5}$/', $input['plz'] ) ) {
			$query['plz'] = $input['plz'];
			$parts[]      = 'PLZ ' . $input['plz'];
		}
		$path = self::PATH;
		$url  = function_exists( 'home_url' ) ? home_url( $path ) : $path;
		if ( array() !== $query ) {
			$url = add_query_arg( $query, $url );
		}

		return array(
			'summary'          => array() === $parts
				? 'Open the Solution Configurator.'
				: 'Open the Solution Configurator with ' . implode( ', ', $parts ) . '.',
			'configurator_url' => $url,
		);
	}
}
