<?php
/**
 * Registration of this plugin's abilities.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Abilities;

use Linker\Commerce\Account\PrivateFiles;
use Linker\Commerce\Account\SavedSolutions;

/**
 * Registers the ability category and every ability of this plugin with the
 * WordPress Abilities API. Each ability class supplies its own arguments; the
 * category is assigned here, so all of them land in it.
 */
final class Registrar {

	/**
	 * Category slug of this plugin's abilities.
	 */
	public const CATEGORY = 'linker';

	/**
	 * Sets up the registrar.
	 *
	 * @param string              $plugin_file Absolute path of the main plugin file.
	 * @param SavedSolutions|null $solutions   The plugin's one store of saved solutions, shared with the account module; a test may omit it.
	 */
	public function __construct(
		private readonly string $plugin_file,
		private readonly ?SavedSolutions $solutions = null
	) {}

	/**
	 * Registers the category; runs on wp_abilities_api_categories_init.
	 */
	public function register_category(): void {
		if ( ! function_exists( 'wp_register_ability_category' ) ) {
			return;
		}

		wp_register_ability_category(
			self::CATEGORY,
			array(
				'label'       => __( 'Linker', 'linker-commerce' ),
				'description' => __( 'Products and inquiries of de-linker.com.', 'linker-commerce' ),
			)
		);
	}

	/**
	 * Registers the abilities; runs on wp_abilities_api_init.
	 */
	public function register_abilities(): void {
		if ( ! function_exists( 'wp_register_ability' ) ) {
			return;
		}

		foreach ( $this->abilities() as $ability ) {
			wp_register_ability( $ability::NAME, array( 'category' => self::CATEGORY ) + $ability->args() );
		}
	}

	/**
	 * Every ability of this plugin, name => instance. One class per ability
	 * (docs/specs/13-genie.md). Write actions are not in this list. The document
	 * search is the Genie service's own tool (docs/specs/10-knowledge-index.md).
	 *
	 * @return array<string, CheckCompatibility|CompareProducts|GetCommerceVersion|GetProduct|HandoffTeam|InquiryStatus|ReadSolution|SearchProducts|SizeHint>
	 */
	public function abilities(): array {
		return array(
			GetCommerceVersion::NAME => new GetCommerceVersion( $this->plugin_file ),
			SearchProducts::NAME     => new SearchProducts(),
			GetProduct::NAME         => new GetProduct(),
			CompareProducts::NAME    => new CompareProducts(),
			CheckCompatibility::NAME => new CheckCompatibility(),
			SizeHint::NAME           => new SizeHint(),
			InquiryStatus::NAME      => new InquiryStatus(),
			ReadSolution::NAME       => new ReadSolution(
				$this->solutions ?? new SavedSolutions( new PrivateFiles( SavedSolutions::REPORTS_DIRECTORY ), '' )
			),
			HandoffTeam::NAME        => new HandoffTeam(),
		);
	}
}
