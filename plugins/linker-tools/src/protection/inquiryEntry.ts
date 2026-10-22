/** Small first-party entry: the native inquiry page does not eagerly load Genie. */
import { restoreInquiry } from './inquiryHandoff';

if ( document.readyState === 'loading' ) {
	document.addEventListener(
		'DOMContentLoaded',
		() => {
			void restoreInquiry();
		},
		{ once: true }
	);
} else {
	void restoreInquiry();
}
