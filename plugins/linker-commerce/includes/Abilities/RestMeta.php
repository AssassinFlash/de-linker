<?php
/**
 * REST metadata shared by the read-only abilities.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Abilities;

/**
 * The Abilities API `meta` block every Genie ability sends: read-only, shown
 * on REST (so OPTIONS exposes the JSON Schema). Write actions are not
 * abilities (docs/specs/13-genie.md).
 */
final class RestMeta {

	/**
	 * Metadata for a read-only REST ability.
	 *
	 * @return array{annotations: array{readonly: true, destructive: false, idempotent: true}, show_in_rest: true}
	 */
	public static function readonly(): array {
		return array(
			'annotations'  => array(
				'readonly'    => true,
				'destructive' => false,
				'idempotent'  => true,
			),
			'show_in_rest' => true,
		);
	}
}
