<?php
/**
 * German translation exceptions in the team's daily digest.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Translation;

use Linker\Commerce\Digest\Block;

/**
 * Loaded through the commerce filter only when its Block interface exists.
 * Query while rendering, after the email has switched to its own locale.
 */
final class DigestBlock implements Block {

	/**
	 * Stable identifier of the block.
	 */
	public function id(): string {
		return 'german_translation_exceptions';
	}

	/**
	 * Heading and current exception count.
	 */
	public function title(): string {
		return sprintf(
			/* translators: %d: number of English sources whose German could not be updated. */
			__( 'German translation exceptions (%d)', 'linker-i18n' ),
			count( ( new StatusReport() )->issues() )
		);
	}

	/**
	 * Failed or structurally different English sources, including taxonomy terms.
	 *
	 * @return list<array{label: string, url: string, link_text: string, detail: string}>
	 */
	public function entries(): array {
		return array_map(
			static fn( array $issue ): array => array(
				'label'     => $issue['title'],
				'url'       => $issue['edit_url'],
				'link_text' => __( 'Open English source', 'linker-i18n' ),
				'detail'    => $issue['reason'],
			),
			( new StatusReport() )->issues()
		);
	}

	/**
	 * The empty block is still a signal in the daily email.
	 */
	public function empty_text(): string {
		return __( 'No German translation exceptions.', 'linker-i18n' );
	}
}
