<?php
/**
 * Ability linker/handoff-team.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Abilities;

use Linker\Commerce\Settings\Options;

/**
 * One sentence pointing company, service and logistics questions at the team
 * mailbox (owner 2026-10-05, AGENTS.md §2). The mailbox is Options::team_mailbox(),
 * not a second copy of the address.
 */
final class HandoffTeam {

	/**
	 * Ability name.
	 */
	public const NAME = 'linker/handoff-team';

	/**
	 * Arguments for wp_register_ability(), apart from the category.
	 *
	 * @return array<string, mixed>
	 */
	public function args(): array {
		return array(
			'label'               => __( 'Hand off to the Linker team', 'linker-commerce' ),
			'description'         => __( 'Returns the team-mailbox sentence in English and German, and a mailto link that carries the conversation summary.', 'linker-commerce' ),
			'input_schema'        => array(
				'type'                 => 'object',
				'properties'           => array(
					'summary' => array(
						'type'        => 'string',
						'description' => __( 'Short summary of the conversation for the team.', 'linker-commerce' ),
					),
				),
				'additionalProperties' => false,
			),
			'output_schema'       => array(
				'type'                 => 'object',
				'properties'           => array(
					'sentence_en' => array(
						'type'        => 'string',
						'description' => __( 'English sentence naming the team mailbox.', 'linker-commerce' ),
					),
					'sentence_de' => array(
						'type'        => 'string',
						'description' => __( 'German sentence naming the team mailbox.', 'linker-commerce' ),
					),
					'mailto'      => array(
						'type'        => 'string',
						'description' => __( 'mailto URL with the summary in the body.', 'linker-commerce' ),
					),
				),
				'required'             => array( 'sentence_en', 'sentence_de', 'mailto' ),
				'additionalProperties' => false,
			),
			'execute_callback'    => array( $this, 'execute' ),
			'permission_callback' => array( $this, 'can_execute' ),
			'meta'                => RestMeta::readonly(),
		);
	}

	/**
	 * Anyone may ask for the team mailbox sentence.
	 */
	public function can_execute(): bool {
		return true;
	}

	/**
	 * The bilingual sentence and a mailto link.
	 *
	 * @param array<string, mixed>|object $input Input with optional summary.
	 * @return array{sentence_en: string, sentence_de: string, mailto: string}
	 */
	public function execute( $input = array() ): array {
		$input   = (array) $input;
		$summary = is_string( $input['summary'] ?? null ) ? trim( $input['summary'] ) : '';
		$to      = ( new Options() )->team_mailbox();
		$mailto  = 'mailto:' . $to;
		if ( '' !== $summary ) {
			$mailto .= '?body=' . rawurlencode( $summary );
		}

		return array(
			'sentence_en' => sprintf( 'Our team will answer that at %s.', $to ),
			'sentence_de' => sprintf( 'Unser Team beantwortet das unter %s.', $to ),
			'mailto'      => $mailto,
		);
	}
}
