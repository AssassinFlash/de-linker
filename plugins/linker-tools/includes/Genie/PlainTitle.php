<?php
/**
 * A WordPress title as plain text.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Genie;

/**
 * WordPress keeps post titles and term names entity-encoded ("EMS &amp;
 * Monitoring", "C&amp;I battery cabinet"); Genie's page context and the
 * preview card both need the plain text, and escape it once on output.
 */
final class PlainTitle {

	/**
	 * The title without tags and entities, trimmed.
	 *
	 * @param string $title A post title or term name.
	 */
	public static function of( string $title ): string {
		return trim( html_entity_decode( wp_strip_all_tags( $title ), ENT_QUOTES | ENT_HTML5, 'UTF-8' ) );
	}
}
