<?php
/**
 * Genie quality verdicts in the team's daily digest.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Genie;

use Linker\Commerce\Digest\Block;

/**
 * Loaded through the commerce filter only when its Block interface exists.
 * The summary is read while rendering, after the email switched to its locale.
 */
final class QualityDigestBlock implements Block {

	/**
	 * Stable identifier of the block.
	 */
	public function id(): string {
		return 'linker_genie_quality';
	}

	/**
	 * Heading of the block.
	 */
	public function title(): string {
		return __( 'Genie quality check', 'linker-tools' );
	}

	/**
	 * The last 24 hours' verdicts, linked to the quality page.
	 *
	 * @return list<array{label: string, url: string, link_text: string, detail: string}>
	 */
	public function entries(): array {
		// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound, WooCommerce.Commenting.CommentHooks.MissingHookComment -- the hook name is this plugin's summary contract, prefixed linker_tools_, documented in QualityStore.
		$summary = apply_filters( QualityStore::SUMMARY_FILTER, array(), time() - QualityStore::SUMMARY_WINDOW );
		if ( ! is_array( $summary ) || '' === (string) ( $summary['line'] ?? '' ) ) {
			return array();
		}
		return array(
			array(
				'label'     => (string) $summary['line'],
				'url'       => (string) ( $summary['url'] ?? '' ),
				'link_text' => __( 'Open', 'linker-tools' ),
				'detail'    => '',
			),
		);
	}

	/**
	 * The empty sentence; the store always returns a line, so this is inert.
	 */
	public function empty_text(): string {
		return '';
	}
}
