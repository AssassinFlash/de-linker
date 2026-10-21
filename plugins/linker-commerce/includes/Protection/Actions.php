<?php
/**
 * Server-owned scopes of the public-entry protection.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

/** The scope list follows the actual entry inventory in the issue 508 decision. */
final class Actions {
	public const ALL = array(
		'contact',
		'inquiry',
		'registration',
		'login',
		'password_reset',
		'comment',
		'genie',
		'genie_contact',
		'genie_inquiry',
		'conversation_mail',
		'conversation_create',
		'conversation_write',
		'vote',
		'design',
		'roof',
		'report_pdf',
		'solution_save',
		'draft_write',
	);

	/**
	 * Never mint an arbitrary browser-selected privileged scope.
	 *
	 * @param string $action Expected public operation.
	 */
	public static function valid( string $action ): bool {
		return in_array( $action, self::ALL, true );
	}
}
