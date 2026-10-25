/** Customer outcomes shared by the current-selection actions. */
import { __ } from '@wordpress/i18n';

export function selectionChangedText(): string {
	return __(
		'This solution needs a new calculation before the next step.',
		'linker-tools'
	);
}

export function publicationUnavailableText(): string {
	return __(
		'The current product data could not be checked. Your entries are still here.',
		'linker-tools'
	);
}

export function additionUnconfirmedText(): string {
	return __(
		'The addition could not be confirmed. The solution draft may already contain these products.',
		'linker-tools'
	);
}

export function additionStatusText(): string {
	return __( 'Addition not confirmed.', 'linker-tools' );
}

export function newCalculationStatusText(): string {
	return __( 'New calculation required.', 'linker-tools' );
}
