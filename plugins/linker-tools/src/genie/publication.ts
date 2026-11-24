/** Customer outcomes shared by the current-selection actions. */
import { __ } from '@wordpress/i18n';

export function additionUnconfirmedText(): string {
	return __(
		'The addition could not be confirmed. The solution draft may already contain these products.',
		'linker-tools'
	);
}

export function additionStatusText(): string {
	return __( 'Addition not confirmed.', 'linker-tools' );
}
