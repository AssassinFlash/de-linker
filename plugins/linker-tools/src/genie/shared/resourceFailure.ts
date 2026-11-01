import { __ } from '@wordpress/i18n';

/**
 * The visitor withdrew this attempt before it was sent: closing the surface,
 * switching conversation, or losing the draft owner. Nothing reached the
 * server, so this is a neutral end of the attempt, never a failure to explain.
 *
 * @param error The rejection from sendTurn, or a resource fetch.
 */
export function isVerificationCancellation( error: unknown ): boolean {
	return error instanceof Error && error.message === 'verification_cancelled';
}

/**
 * A failed proof is distinct from quota, attachment and provider failures.
 * @param error The original rejected request.
 */
export function isVerificationFailure( error: unknown ): boolean {
	return (
		! isVerificationCancellation( error ) &&
		error instanceof Error &&
		( error.message.startsWith( 'verification_' ) ||
			( 'code' in error &&
				typeof error.code === 'string' &&
				error.code.startsWith( 'linker_verification_' ) ) )
	);
}

/**
 * Reviewed customer explanation; API diagnostics never become visible copy.
 * @param error
 */
export function resourceRefusalReason( error: unknown ): string | null {
	// Withdrawal is not a failure: the shell restores the draft silently.
	if ( isVerificationCancellation( error ) ) {
		return null;
	}
	if ( isVerificationFailure( error ) ) {
		return __(
			'Verification could not be completed. No request has been sent in this attempt. Please try again.',
			'linker-tools'
		);
	}
	if (
		error instanceof Error &&
		'code' in error &&
		typeof error.code === 'string' &&
		error.code.startsWith( 'linker_genie_attachment_' )
	) {
		return null;
	}

	if ( error instanceof Error && 'code' in error ) {
		if ( error.code === 'linker_genie_publication_changed' ) {
			return __(
				'The product information changed while Genie was answering. Your message is still here.',
				'linker-tools'
			);
		}
		if ( error.code === 'linker_genie_publication_unavailable' ) {
			return __(
				'Genie is temporarily unavailable. Your message is still here. You can send an inquiry to our team.',
				'linker-tools'
			);
		}
	}
	if (
		error instanceof Error &&
		( ( 'status' in error && error.status === 429 ) ||
			( 'code' in error &&
				typeof error.code === 'string' &&
				/^(linker_admission_|linker_resource_|linker_genie_quota)/.test(
					error.code
				) ) )
	) {
		return __(
			'Genie is temporarily unavailable. Your message is still here. You can send an inquiry to our team.',
			'linker-tools'
		);
	}
	return null;
}
