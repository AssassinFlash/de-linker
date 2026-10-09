<?php
/**
 * Ability linker/get-commerce-version.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Abilities;

/**
 * Reports which version of Linker Commerce is installed, read from the plugin header.
 */
final class GetCommerceVersion {

	/**
	 * Ability name.
	 */
	public const NAME = 'linker/get-commerce-version';

	/**
	 * Sets up the ability.
	 *
	 * @param string $plugin_file Absolute path of the main plugin file.
	 */
	public function __construct( private readonly string $plugin_file ) {}

	/**
	 * Arguments for wp_register_ability(), apart from the category.
	 *
	 * @return array<string, mixed>
	 */
	public function args(): array {
		return array(
			'label'               => __( 'Get Linker Commerce version', 'linker-commerce' ),
			'description'         => __( 'Returns the version of the Linker Commerce plugin installed on this site.', 'linker-commerce' ),
			'output_schema'       => array(
				'type'                 => 'object',
				'properties'           => array(
					'version' => array(
						'type'        => 'string',
						'description' => __( 'Version from the plugin header.', 'linker-commerce' ),
					),
				),
				'required'             => array( 'version' ),
				'additionalProperties' => false,
			),
			'execute_callback'    => array( $this, 'execute' ),
			'permission_callback' => array( $this, 'can_execute' ),
			'meta'                => array(
				'annotations'  => array(
					'readonly'    => true,
					'destructive' => false,
					'idempotent'  => true,
				),
				'show_in_rest' => true,
			),
		);
	}

	/**
	 * Reads the version from the plugin header.
	 *
	 * @return array{version: string}
	 */
	public function execute(): array {
		$headers = get_file_data( $this->plugin_file, array( 'version' => 'Version' ) );

		return array( 'version' => $headers['version'] );
	}

	/**
	 * Limits the ability to administrators: a version number tells an attacker which exploits apply.
	 */
	public function can_execute(): bool {
		return current_user_can( 'manage_options' );
	}
}
