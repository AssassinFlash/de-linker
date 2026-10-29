<?php
/**
 * What a native refusal proved about the write, shared by both browser doors.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

/**
 * One table decides the recovery hint and the contact door's sentence, so a new
 * native code cannot inherit an unrelated outcome by falling into a default.
 *
 * The table is checked against every code the two doors can return by
 * tests/php/Unit/Protection/OutcomeTest.php, which reads the emitters instead of
 * repeating them here.
 */
final class Outcome {
	/** Nothing was written; the next attempt starts from a fresh check. */
	public const REFUSED = 'refused';
	/** A native record may exist under this UUID, so it stays recoverable. */
	public const UNCONFIRMED = 'unconfirmed';

	/**
	 * Native code to `array( partition, contact state )`.
	 *
	 * Contact states are the ones Contact\Form::state_message() renders; a code
	 * that cannot reach the contact door still names the state it would produce,
	 * so the table stays one answer per code.
	 */
	private const TABLE = array(
		// Verification itself refused the request before any native write.
		'linker_admission_configuration'      => array( self::REFUSED, 'verification_unavailable' ),
		'linker_admission_proof'              => array( self::REFUSED, 'verification_failed' ),
		'linker_admission_proof_reused'       => array( self::REFUSED, 'verification_failed' ),
		'linker_admission_payload_changed'    => array( self::REFUSED, 'verification_failed' ),
		'linker_admission_input'              => array( self::REFUSED, 'verification_failed' ),
		// The journal refuses the new receipt, so no work was dispatched.
		'linker_admission_quota'              => array( self::REFUSED, 'throttled' ),
		// The site cannot take another request at all: journal or business capacity.
		'linker_admission_capacity'           => array( self::REFUSED, 'reception_full' ),
		'linker_admission_cookie'             => array( self::REFUSED, 'reception_full' ),
		'linker_business_capacity'            => array( self::REFUSED, 'reception_full' ),
		// Field, nonce, honeypot and draft validation precede every native write.
		'linker_inquiry_invalid'              => array( self::REFUSED, 'invalid' ),
		'linker_inquiry_empty'                => array( self::REFUSED, 'invalid' ),
		'linker_inquiry_throttled'            => array( self::REFUSED, 'throttled' ),
		'linker_draft_changed'                => array( self::REFUSED, 'invalid' ),
		// The inquiry door's read-only draft check, before admission reserves.
		'planning_context_unavailable'        => array( self::REFUSED, 'invalid' ),
		'linker_contact_invalid'              => array( self::REFUSED, 'invalid' ),
		'linker_contact_throttled'            => array( self::REFUSED, 'throttled' ),
		'linker_contact_name'                 => array( self::REFUSED, 'invalid' ),
		'linker_contact_email'                => array( self::REFUSED, 'invalid' ),
		'linker_contact_message'              => array( self::REFUSED, 'invalid' ),
		'linker_contact_consent'              => array( self::REFUSED, 'invalid' ),
		'linker_contact_selection'            => array( self::REFUSED, 'invalid' ),
		// The bounded review store refused before it created its entry.
		'linker_intake_size'                  => array( self::REFUSED, 'review_size' ),
		'linker_intake_full'                  => array( self::REFUSED, 'review_full' ),
		'linker_intake_grouped'               => array( self::REFUSED, 'grouped' ),
		// A receipt exists and its native result is reserved/dispatched/unverified,
		// or the journal itself could not be read. Neither proves absence.
		'linker_admission_pending'            => array( self::UNCONFIRMED, 'pending' ),
		'linker_admission_already_reserved'   => array( self::UNCONFIRMED, 'pending' ),
		'linker_admission_already_dispatched' => array( self::UNCONFIRMED, 'pending' ),
		'linker_admission_already_unresolved' => array( self::UNCONFIRMED, 'pending' ),
		'linker_admission_already_completed'  => array( self::UNCONFIRMED, 'pending' ),
		'linker_admission_already_cancelled'  => array( self::UNCONFIRMED, 'pending' ),
		'linker_admission_already_expired'    => array( self::UNCONFIRMED, 'pending' ),
		'linker_admission_already_erased'     => array( self::UNCONFIRMED, 'pending' ),
		'linker_admission_unknown_receipt'    => array( self::UNCONFIRMED, 'pending' ),
		'linker_admission_erased'             => array( self::UNCONFIRMED, 'pending' ),
		'linker_admission_storage'            => array( self::UNCONFIRMED, 'pending' ),
		'linker_admission_busy'               => array( self::UNCONFIRMED, 'pending' ),
		'linker_admission_unavailable'        => array( self::UNCONFIRMED, 'pending' ),
		'linker_inquiry_pending'              => array( self::UNCONFIRMED, 'pending' ),
		// The native writer created its checkout order but could not prove it.
		'linker_inquiry_create'               => array( self::UNCONFIRMED, 'pending' ),
		// The review store may have started its writer.
		'linker_intake_busy'                  => array( self::UNCONFIRMED, 'pending' ),
		'linker_intake_pending'               => array( self::UNCONFIRMED, 'pending' ),
	);

	/**
	 * Which partition a native code belongs to.
	 *
	 * An unrecognized code keeps recovery: only a code this table proved
	 * pre-write may ask a customer for a new check.
	 *
	 * @param string $code Native error code.
	 */
	public static function of( string $code ): string {
		return self::TABLE[ $code ][0] ?? self::UNCONFIRMED;
	}

	/**
	 * The contact form's state for a native refusal.
	 *
	 * @param string $code Native error code.
	 */
	public static function contact_state( string $code ): string {
		// An unrecognized outcome is never a verification verdict.
		return self::TABLE[ $code ][1] ?? 'pending';
	}

	/**
	 * The classified codes, for the coverage test and for review.
	 *
	 * @return array<string, array{0:string,1:string}>
	 */
	public static function table(): array {
		return self::TABLE;
	}
}
