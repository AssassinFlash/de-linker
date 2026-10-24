const STORAGE_KEY = 'linker.contact.language.v1';
const FORM_SELECTOR = 'form[data-linker-contact-draft-owner]';
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
	const edited = new WeakSet< Element >();
	let consumed = false;
	const currentForm = () =>
		document.querySelector< HTMLFormElement >( FORM_SELECTOR );
	const control = (
		form: HTMLFormElement,
		field: TextField
	): TextControl | null => {
		const input = form.elements.namedItem( field );
		return input instanceof HTMLInputElement ||
			input instanceof HTMLTextAreaElement ||
			input instanceof HTMLSelectElement
			? input
			: null;
	};
	const checkbox = ( form: HTMLFormElement, name: string ) =>
		form.querySelector< HTMLInputElement >(
			`input[type="checkbox"][name="${ name }"]`
		);
	const complete = ( form: HTMLFormElement ) =>
		Boolean( checkbox( form, 'consent' ) ) &&
		TEXT_FIELDS.every( ( key ) => {
			const input = control( form, key );
			return (
				input &&
				( ! ( input instanceof HTMLSelectElement ) ||
					input.options.length > 0 )
			);
		} );
	const atDefault = ( input: TextControl ) => {
		if ( input instanceof HTMLSelectElement ) {
			const initial = Array.from( input.options ).find(
				( option ) => option.defaultSelected
			);
			return input.value === ( initial || input.options[ 0 ] )?.value;
		}
		return input.value === input.defaultValue;
	};
	const untouched = ( input: TextControl ) =>
		! edited.has( input ) && atDefault( input );
	const acceptable = (
		form: HTMLFormElement,
		fields: unknown
	): fields is Fields => {
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
				const input = control( form, key );
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
	const clear = () => {
		try {
			window.sessionStorage.removeItem( STORAGE_KEY );
		} catch {
			// Native validation and submission keep their existing owners.
		}
	};
	const consume = ( form: HTMLFormElement | null ) => {
		if ( consumed ) {
			return;
		}
		consumed = true;
		observer.disconnect();
		try {
			const raw = window.sessionStorage.getItem( STORAGE_KEY );
			// Once the native form is complete, consume before inspecting any state.
			window.sessionStorage.removeItem( STORAGE_KEY );
			const draft = JSON.parse(
				raw || 'null'
			) as Partial< Draft > | null;
			if ( ! form ) {
				return;
			}
			const owner = form.dataset.linkerContactDraftOwner || '';
			const context = form.dataset.linkerContactDraftContext || '';
			const lifetime = Number( form.dataset.linkerContactDraftLifetime );
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
				( draft.include === null ||
					typeof draft.include === 'boolean' ) &&
				acceptable( form, draft.fields )
			) {
				for ( const key of TEXT_FIELDS ) {
					const input = control( form, key )!;
					if ( untouched( input ) ) {
						input.value = draft.fields[ key ];
					}
				}
				const consent = checkbox( form, 'consent' )!;
				const include = checkbox( form, 'linker_contact_selection' );
				if (
					! edited.has( consent ) &&
					consent.checked === consent.defaultChecked
				) {
					consent.checked = draft.consent;
				}
				if (
					include &&
					draft.include !== null &&
					! edited.has( include ) &&
					include.checked === include.defaultChecked
				) {
					include.checked = draft.include;
				}
			}
		} catch {
			// Invalid, expired or unrelated state was already removed. The native form wins.
		}
	};
	const restore = () => {
		const form = currentForm();
		if ( document.querySelector( '.linker-contact-receipt' ) ) {
			consume( null );
		} else if ( form && complete( form ) ) {
			consume( form );
		}
	};
	const observer = new MutationObserver( restore );
	const edit = ( event: Event ) => {
		const input = event.target;
		if (
			( input instanceof HTMLInputElement ||
				input instanceof HTMLTextAreaElement ||
				input instanceof HTMLSelectElement ) &&
			input.form?.matches( FORM_SELECTOR ) &&
			( TEXT_FIELDS.includes( input.name as TextField ) ||
				[ 'consent', 'linker_contact_selection' ].includes(
					input.name
				) )
		) {
			edited.add( input );
		}
	};
	const fallback = ( form: HTMLFormElement, link: HTMLAnchorElement ) => {
		const error = form.querySelector< HTMLElement >(
			'[data-linker-contact-draft-error]'
		);
		const action = error?.querySelector< HTMLAnchorElement >(
			'[data-linker-contact-draft-new-tab]'
		);
		if ( error && action ) {
			action.href = link.href;
			error.hidden = false;
			action.focus();
		}
	};
	const click = ( event: MouseEvent ) => {
		if (
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
		const form = currentForm();
		if ( ! form ) {
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
		// A click may run before the parser's queued MutationObserver callback.
		restore();
		const include = checkbox( form, 'linker_contact_selection' );
		const consent = checkbox( form, 'consent' );
		const removed = Boolean(
			form.querySelector( '.linker-contact-selection--excluded' )
		);
		const dirty =
			removed ||
			TEXT_FIELDS.some( ( key ) => {
				const input = control( form, key );
				return (
					input &&
					( input instanceof HTMLSelectElement
						? ! atDefault( input )
						: Boolean( input.value ) || ! atDefault( input ) )
				);
			} ) ||
			( consent && consent.checked !== consent.defaultChecked ) ||
			( include && include.checked !== include.defaultChecked );
		if ( ! dirty ) {
			return;
		}
		if ( ! complete( form ) ) {
			// Keep a partial parser edit here; never serialize missing controls.
			event.preventDefault();
			fallback( form, link );
			return;
		}
		const owner = form.dataset.linkerContactDraftOwner || '';
		const context = form.dataset.linkerContactDraftContext || '';
		const lifetime = Number( form.dataset.linkerContactDraftLifetime );
		const fields = Object.fromEntries(
			TEXT_FIELDS.map( ( key ) => [ key, control( form, key )!.value ] )
		);
		try {
			if (
				! owner ||
				! context ||
				! Number.isFinite( lifetime ) ||
				lifetime <= 0 ||
				! acceptable( form, fields )
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
				consent: consent!.checked,
				include: include?.checked ?? ( removed ? false : null ),
			};
			const serialized = JSON.stringify( draft );
			window.sessionStorage.setItem( STORAGE_KEY, serialized );
			if ( window.sessionStorage.getItem( STORAGE_KEY ) !== serialized ) {
				throw new Error( 'contact_language_storage' );
			}
		} catch {
			event.preventDefault();
			clear();
			fallback( form, link );
		}
	};
	const submit = ( event: Event ) => {
		if (
			event.target instanceof HTMLFormElement &&
			event.target.matches( FORM_SELECTOR )
		) {
			consumed = true;
			observer.disconnect();
			clear();
		}
	};
	const ready = () => {
		if (
			! currentForm() ||
			document.querySelector( '.linker-contact-receipt' )
		) {
			consume( null );
		}
	};
	document.addEventListener( 'input', edit, true );
	document.addEventListener( 'change', edit, true );
	document.addEventListener( 'compositionstart', edit, true );
	document.addEventListener( 'click', click );
	document.addEventListener( 'submit', submit, true );
	document.addEventListener( 'DOMContentLoaded', ready, { once: true } );
	observer.observe( document, { childList: true, subtree: true } );
	restore();
	if ( document.readyState !== 'loading' ) {
		ready();
	}
	return () => {
		observer.disconnect();
		document.removeEventListener( 'input', edit, true );
		document.removeEventListener( 'change', edit, true );
		document.removeEventListener( 'compositionstart', edit, true );
		document.removeEventListener( 'click', click );
		document.removeEventListener( 'submit', submit, true );
		document.removeEventListener( 'DOMContentLoaded', ready );
	};
}
