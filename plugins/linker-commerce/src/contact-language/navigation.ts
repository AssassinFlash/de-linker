const STORAGE_KEY = 'linker.contact.language.v1';
const TEXT_FIELDS = [
	'message',
	'name',
	'email',
	'company',
	'intent',
] as const;
type TextField = ( typeof TEXT_FIELDS )[ number ];
type TextControl = HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement;
type Fields = Record< TextField, string >;
type Draft = {
	version: 1;
	owner: string;
	context: string;
	target: string;
	until: number;
	fields: Fields;
	consent: boolean;
	include: boolean | null;
};

/**
 * Compare public navigation without moving private form values into its URL.
 *
 * @param value Native public language URL.
 */
function address( value: string ): string {
	const url = new URL( value, window.location.href );
	if (
		url.origin !== window.location.origin ||
		url.username ||
		url.password
	) {
		throw new Error( 'contact_language_origin' );
	}
	url.hash = '';
	url.searchParams.sort();
	return url.href;
}

/** A single explicit language click, never an autosave or a submission. */
export function connectContactLanguage(): () => void {
	let stored: unknown;
	try {
		const raw = window.sessionStorage.getItem( STORAGE_KEY );
		// Consume before inspecting or restoring, including receipt/failed-POST pages.
		window.sessionStorage.removeItem( STORAGE_KEY );
		stored = JSON.parse( raw || 'null' );
	} catch {
		stored = null;
	}
	const form = document.querySelector< HTMLFormElement >(
		'form[data-linker-contact-draft-owner]'
	);
	if ( ! form ) {
		return () => {};
	}
	const owner = form.dataset.linkerContactDraftOwner || '';
	const context = form.dataset.linkerContactDraftContext || '';
	const lifetime = Number( form.dataset.linkerContactDraftLifetime );
	const control = ( field: TextField ): TextControl | null => {
		const input = form.elements.namedItem( field );
		return input instanceof HTMLInputElement ||
			input instanceof HTMLTextAreaElement ||
			input instanceof HTMLSelectElement
			? input
			: null;
	};
	const include = form.querySelector< HTMLInputElement >(
		'input[type="checkbox"][name="linker_contact_selection"]'
	);
	const consent = form.querySelector< HTMLInputElement >(
		'input[type="checkbox"][name="consent"]'
	);
	const acceptable = ( fields: unknown ): fields is Fields => {
		if (
			! fields ||
			typeof fields !== 'object' ||
			Array.isArray( fields )
		) {
			return false;
		}
		const record = fields as Record< string, unknown >;
		return (
			Object.keys( record ).length === TEXT_FIELDS.length &&
			TEXT_FIELDS.every( ( key ) => {
				const input = control( key );
				const value = record[ key ];
				if ( ! input || typeof value !== 'string' ) {
					return false;
				}
				return input instanceof HTMLSelectElement
					? Array.from( input.options ).some(
							( option ) => option.value === value
						)
					: input.maxLength >= 0 && value.length <= input.maxLength;
			} )
		);
	};
	try {
		const draft = stored as Partial< Draft > | null;
		if (
			draft &&
			draft.version === 1 &&
			owner &&
			draft.owner === owner &&
			context &&
			draft.context === context &&
			Number.isFinite( lifetime ) &&
			lifetime > 0 &&
			typeof draft.until === 'number' &&
			draft.until > Date.now() &&
			draft.until <= Date.now() + lifetime &&
			typeof draft.target === 'string' &&
			address( window.location.href ) === draft.target &&
			form.dataset.linkerContactRecovered !== '1' &&
			typeof draft.consent === 'boolean' &&
			( draft.include === null || typeof draft.include === 'boolean' ) &&
			acceptable( draft.fields )
		) {
			// A late bundle must not replace an edit already made on this page.
			if ( ! form.contains( form.ownerDocument.activeElement ) ) {
				for ( const key of TEXT_FIELDS ) {
					const input = control( key )!;
					const untouched =
						input instanceof HTMLSelectElement
							? Boolean(
									input.selectedOptions[ 0 ]?.defaultSelected
								)
							: input.value === input.defaultValue;
					if ( untouched ) {
						input.value = draft.fields[ key ];
					}
				}
				if ( consent && consent.checked === consent.defaultChecked ) {
					consent.checked = draft.consent;
				}
				if (
					include &&
					draft.include !== null &&
					include.checked === include.defaultChecked
				) {
					include.checked = draft.include;
				}
			}
		}
	} catch {
		// Invalid, expired or unrelated state was already removed. The native form wins.
	}
	const click = ( event: MouseEvent ) => {
		if (
			! form.isConnected ||
			event.defaultPrevented ||
			event.button !== 0 ||
			event.altKey ||
			event.ctrlKey ||
			event.metaKey ||
			event.shiftKey ||
			! ( event.target instanceof Element )
		) {
			return;
		}
		const link = event.target.closest< HTMLAnchorElement >(
			'a[data-linker-language-choice]'
		);
		if (
			! link ||
			link.target ||
			link.hasAttribute( 'download' ) ||
			! [ 'en', 'de' ].includes( link.dataset.linkerLanguageChoice || '' )
		) {
			return;
		}
		if ( link.getAttribute( 'aria-current' ) === 'true' ) {
			event.preventDefault();
			return;
		}
		let target: string;
		try {
			target = address( link.href );
		} catch {
			return;
		}
		const dirty =
			TEXT_FIELDS.some( ( key ) => {
				const input = control( key );
				return input instanceof HTMLSelectElement
					? ! input.selectedOptions[ 0 ]?.defaultSelected
					: Boolean( input?.value );
			} ) ||
			( consent && consent.checked !== consent.defaultChecked ) ||
			( include && include.checked !== include.defaultChecked );
		if ( ! dirty ) {
			return;
		}
		const fields = Object.fromEntries(
			TEXT_FIELDS.map( ( key ) => [ key, control( key )?.value ] )
		);
		try {
			if (
				! owner ||
				! context ||
				! Number.isFinite( lifetime ) ||
				lifetime <= 0 ||
				! acceptable( fields )
			) {
				throw new Error( 'contact_language_fields' );
			}
			const draft: Draft = {
				version: 1,
				owner,
				context,
				target,
				until: Date.now() + lifetime,
				fields,
				consent: Boolean( consent?.checked ),
				include: include?.checked ?? null,
			};
			const serialized = JSON.stringify( draft );
			window.sessionStorage.setItem( STORAGE_KEY, serialized );
			if ( window.sessionStorage.getItem( STORAGE_KEY ) !== serialized ) {
				throw new Error( 'contact_language_storage' );
			}
		} catch {
			event.preventDefault();
			try {
				window.sessionStorage.removeItem( STORAGE_KEY );
			} catch {
				// The original page remains open even when storage is unavailable.
			}
			const error = form.querySelector< HTMLElement >(
				'[data-linker-contact-draft-error]'
			);
			const fallback = error?.querySelector< HTMLAnchorElement >(
				'[data-linker-contact-draft-new-tab]'
			);
			if ( error && fallback ) {
				fallback.href = link.href;
				error.hidden = false;
				fallback.focus();
			}
		}
	};
	document.addEventListener( 'click', click );
	const clear = () => {
		try {
			window.sessionStorage.removeItem( STORAGE_KEY );
		} catch {
			// Native validation and submission keep their existing owners.
		}
	};
	form.addEventListener( 'submit', clear );
	return () => {
		document.removeEventListener( 'click', click );
		form.removeEventListener( 'submit', clear );
	};
}
