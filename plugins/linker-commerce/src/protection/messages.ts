import { __ } from '@wordpress/i18n';

/**
 * States in which this attempt is still obtaining a proof. A terminal state
 * (`failed`, `expired`, `ready`) has its own sentence, so it is not here.
 */
export type PendingState = 'checking' | 'interactive' | 'retrying';

const PENDING: readonly string[] = [ 'checking', 'interactive', 'retrying' ];

/**
 * Narrow a lifecycle value from the widget or the DOM to a pending state.
 *
 * @param value Any lifecycle value, including one written by an older bundle.
 */
export function pendingState( value: string | undefined ): PendingState {
	return value !== undefined && PENDING.includes( value )
		? ( value as PendingState )
		: 'checking';
}

/**
 * Every one of these states precedes the native business/resource submission.
 *
 * @param state Current verification lifecycle state.
 */
export function verificationPendingText( state: PendingState ): string {
	if ( state === 'interactive' ) {
		return __(
			'No request has been sent in this attempt. Please complete the verification.',
			'linker-commerce'
		);
	}
	if ( state === 'retrying' ) {
		return __(
			'Verification is being retried. No request has been sent in this attempt.',
			'linker-commerce'
		);
	}
	return __(
		'Checking verification. No request has been sent in this attempt.',
		'linker-commerce'
	);
}

/**
 * The one sentence for a verification attempt that ended without a request:
 * the browser stopped before the native submit, so nothing was sent.
 * The server's own verification refusals say the same thing, in the same words.
 */
export function verificationFailedText(): string {
	return __(
		'Verification could not be completed. No request has been sent in this attempt. Please try again or email sales@de-linker.com.',
		'linker-commerce'
	);
}
