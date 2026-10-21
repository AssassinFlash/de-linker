import { __ } from '@wordpress/i18n';

/**
 * Reviewed customer explanation; API diagnostics never become visible copy.
 * @param error
 */
export function resourceRefusalReason( error: unknown ): string | null {
	if (
		error instanceof Error &&
		'code' in error &&
		typeof error.code === 'string' &&
		error.code.startsWith( 'linker_genie_attachment_' )
	) {
		return null;
	}

	if (
		error instanceof Error &&
		( ( 'status' in error && error.status === 429 ) ||
			( 'code' in error &&
				typeof error.code === 'string' &&
				/^(linker_admission_|linker_resource_|linker_genie_quota)/.test(
					error.code
				) ) ||
			error.message.startsWith( 'verification_' ) )
	) {
		return __(
			'Genie is temporarily unavailable. Your message is still here. You can send an inquiry to our team.',
			'linker-tools'
		);
	}
	return null;
}
