/** Bind only the real marketing editors; ordinary Genie links remain navigation. */
import { __ } from '@wordpress/i18n';
import type { GenieConfig } from '../genie/config';
import {
	entryScope,
	newEntryId,
	readEntryRecovery,
	rememberEntry,
	type EntryDraft,
	type EntryMode,
} from '../genie/shared/entryDraft';
import {
	MAX_PROJECT_BRIEF_LENGTH,
	UNSTAGED_BRIEF_ID,
	clearProjectBrief,
	readProjectBrief,
	stageProjectBrief,
	writeProjectBrief,
	type ProjectBriefV1,
} from '../genie/shared/projectBriefDraft';

function defaultNavigate( url: string ): void {
	try {
		window.location.assign( url );
	} catch {
		// Non-navigating test environments observe the custom event and href.
	}
}

export function bindMarketingEntries(
	root: Document,
	config: GenieConfig,
	navigate: ( url: string ) => void = defaultNavigate
): () => void {
	const editors = [
		...root.querySelectorAll< HTMLTextAreaElement >(
			'#system-search .lk-dialog-prompt, #installer-mobile-query'
		),
	];
	const cleanup = editors.map( ( field ) => {
		if ( field.dataset.genieEntryBound ) {
			return () => undefined;
		}
		field.dataset.genieEntryBound = '1';
		if (
			! field.getAttribute( 'aria-label' ) &&
			! field.getAttribute( 'aria-labelledby' ) &&
			( ! field.id ||
				! root.querySelector(
					`label[for="${ field.id.replace( /"/g, '\\"' ) }"]`
				) )
		) {
			const placeholder = field.placeholder
				.replace( /(?:\.\.\.|…)+$/u, '' )
				.trim();
			if ( placeholder ) {
				field.setAttribute( 'aria-label', placeholder );
			}
		}
		const section =
			field.closest< HTMLElement >(
				'#system-search, .installer-mobile-assistant'
			) ?? field.parentElement;
		if ( ! section ) {
			return () => undefined;
		}
		// Installer markup's field/send share the nearest mobile panel. Never bind desktop Plan here.
		const owner =
			field.id === 'installer-mobile-query'
				? ( field.closest< HTMLElement >(
						'.installer-assistant, .installer-mobile, [class*="mobile"]'
					) ?? section )
				: section;
		const send = owner.querySelector< HTMLElement >(
			'.lk-send-btn, .installer-assistant-send'
		);
		const modes = [
			...owner.querySelectorAll< HTMLButtonElement >(
				'[data-linker-assistant-open]'
			),
		];
		modes.forEach( ( button ) => {
			button.disabled = false;
		} );
		let pending: EntryDraft | null = null;
		let preparing = false;
		let scope = '';
		let live = true;
		const status = root.createElement( 'p' );
		status.className = 'screen-reader-text';
		status.setAttribute( 'role', 'status' );
		owner.append( status );
		const verify = async () => {
			const next = await entryScope( config );
			if ( scope && scope !== next ) {
				pending = null;
			}
			scope = next;
			return next;
		};
		// Recovery is editing only: refresh/back never calls the model.
		void verify()
			.then( ( current ) => {
				if ( ! live || field.value ) {
					return;
				}
				const stored = readEntryRecovery( current )
					.entries.filter(
						( item ) => item.sourcePath === location.pathname
					)
					.at( -1 );
				if ( stored ) {
					field.value = stored.text;
				}
			} )
			.catch( () => undefined );
		const deliver = async (
			mode: EntryMode,
			opener: HTMLElement = field
		) => {
			if ( preparing || ( mode === 'compose' && ! field.value.trim() ) ) {
				return;
			}
			preparing = true;
			let handed = false;
			send?.setAttribute( 'aria-busy', 'true' );
			try {
				const snapshot = field.value;
				const current = await verify();
				if ( ! live ) {
					return;
				}
				if (
					! pending ||
					pending.text !== snapshot ||
					pending.mode !== mode ||
					pending.scope !== current
				) {
					pending = {
						id: newEntryId(),
						text: snapshot,
						sourcePath: location.pathname,
						mode,
						scope: current,
					};
				}
				if ( ! rememberEntry( pending ) ) {
					throw new Error( 'entry-recovery' );
				}
				window.dispatchEvent(
					new CustomEvent( 'linker-genie-ask', {
						detail: { entry: pending, opener },
					} )
				);
				handed = true;
			} catch {
				status.className = 'linker-genie-app__error';
				status.textContent = __(
					'Genie could not load.',
					'linker-tools'
				);
			} finally {
				preparing = false;
				if ( ! handed ) {
					send?.removeAttribute( 'aria-busy' );
				}
			}
		};
		const click = ( event: Event ) => {
			event.preventDefault();
			void deliver( 'compose', event.currentTarget as HTMLElement );
		};
		const key = ( event: KeyboardEvent ) => {
			if (
				event.key === 'Enter' &&
				! event.shiftKey &&
				! event.isComposing &&
				event.keyCode !== 229
			) {
				event.preventDefault();
				void deliver( 'compose' );
			}
		};
		const mode = ( event: Event ) => {
			const target = event.currentTarget as HTMLElement;
			event.preventDefault();
			const value = target.dataset.linkerAssistantOpen;
			let intent: EntryMode = 'attach';
			if ( value === 'voice' || value === 'nameplate' ) {
				intent = value;
			}
			void deliver( intent, target );
		};
		const ack = ( event: Event ) => {
			const detail = (
				event as CustomEvent< { id: string; phase: string } >
			 ).detail;
			if (
				pending &&
				detail?.id === pending.id &&
				detail.phase === 'accepted'
			) {
				if ( field.value === pending.text ) {
					field.value = '';
				}
				status.textContent = '';
				send?.removeAttribute( 'aria-busy' );
				pending = null;
			}
			if (
				pending &&
				detail?.id === pending.id &&
				detail.phase === 'failed'
			) {
				send?.removeAttribute( 'aria-busy' );
				status.className = 'linker-genie-app__error';
				status.textContent = __(
					'Genie could not load.',
					'linker-tools'
				);
			}
		};
		send?.addEventListener( 'click', click );
		field.addEventListener( 'keydown', key );
		modes.forEach( ( button ) => button.addEventListener( 'click', mode ) );
		window.addEventListener( 'linker-genie-entry-state', ack );
		return () => {
			live = false;
			delete field.dataset.genieEntryBound;
			send?.removeEventListener( 'click', click );
			field.removeEventListener( 'keydown', key );
			modes.forEach( ( button ) =>
				button.removeEventListener( 'click', mode )
			);
			window.removeEventListener( 'linker-genie-entry-state', ack );
			status.remove();
		};
	} );

	const planInputs = [
		...root.querySelectorAll< HTMLInputElement | HTMLTextAreaElement >(
			'#lki-hero-query'
		),
	];
	const planCleanup = planInputs.map( ( field ) => {
		if ( field.dataset.geniePlanBound ) {
			return () => undefined;
		}
		field.dataset.geniePlanBound = '1';
		const owner =
			field.closest< HTMLElement >(
				'.lk-console-input-row, .lk-hero-console, #installer-journal'
			) ?? field.parentElement;
		if ( ! owner ) {
			return () => undefined;
		}
		const planLink =
			owner.querySelector< HTMLAnchorElement >( '.lk-btn-query' ) ??
			root.querySelector< HTMLAnchorElement >( '.lk-btn-query' );
		const baseHref =
			planLink?.getAttribute( 'href' ) || '/solution-configurator/';
		let staged: ProjectBriefV1 | null = null;
		let preparing = false;
		let scope = '';
		let live = true;
		const status = root.createElement( 'p' );
		status.className = 'screen-reader-text';
		status.setAttribute( 'role', 'status' );
		owner.append( status );
		const verify = async ( fresh = false ) => {
			const next = await entryScope( config, fresh );
			if ( scope && scope !== next ) {
				staged = null;
			}
			scope = next;
			return next;
		};
		void verify()
			.then( ( current ) => {
				if ( ! live || field.value ) {
					return;
				}
				const stored = readProjectBrief( current );
				if ( stored ) {
					field.value = stored.text;
					staged = stored;
				}
			} )
			.catch( () => undefined );
		const onInput = () => {
			status.textContent = '';
			status.className = 'screen-reader-text';
			if ( ! scope ) {
				return;
			}
			const value = field.value;
			if ( ! value.trim() ) {
				clearProjectBrief( scope );
				staged = null;
				return;
			}
			if ( Array.from( value ).length <= MAX_PROJECT_BRIEF_LENGTH ) {
				const draft: ProjectBriefV1 = {
					v: 1,
					id: staged?.id ?? UNSTAGED_BRIEF_ID,
					text: value,
					sourcePath: location.pathname || '/for-installer/',
					contextScope: scope,
					revision: staged?.revision ?? '0'.repeat( 64 ),
					confirmed: staged?.confirmed ?? {},
				};
				writeProjectBrief( draft );
			}
		};
		const deliverPlan = async () => {
			if ( preparing || ! field.value.trim() ) {
				return;
			}
			const snapshot = field.value;
			if ( Array.from( snapshot ).length > MAX_PROJECT_BRIEF_LENGTH ) {
				status.className = 'linker-genie-app__error';
				status.textContent = __(
					'The project note could not be carried over. Your text is still here.',
					'linker-tools'
				);
				return;
			}
			preparing = true;
			let handed = false;
			planLink?.setAttribute( 'aria-busy', 'true' );
			try {
				const current = await verify();
				if ( ! live ) {
					return;
				}
				const record = await stageProjectBrief( config, {
					text: snapshot,
					sourcePath: location.pathname || '/for-installer/',
					briefId:
						staged &&
						staged.contextScope === current &&
						staged.id !== UNSTAGED_BRIEF_ID
							? staged.id
							: null,
					expectedRevision:
						staged &&
						staged.contextScope === current &&
						staged.id !== UNSTAGED_BRIEF_ID
							? staged.revision
							: null,
					confirmed: staged?.confirmed ?? {},
				} );
				if ( ! live ) {
					return;
				}
				staged = record;
				scope = record.contextScope;
				status.textContent = '';
				status.className = 'screen-reader-text';
				const destination = new URL( baseHref, location.origin );
				destination.searchParams.set( 'brief', record.id );
				handed = true;
				window.dispatchEvent(
					new CustomEvent( 'linker-project-brief-ready', {
						detail: { brief: record, url: destination.href },
					} )
				);
				navigate( destination.href );
			} catch {
				status.className = 'linker-genie-app__error';
				status.textContent = __(
					'The project note could not be carried over. Your text is still here.',
					'linker-tools'
				);
			} finally {
				preparing = false;
				if ( ! handed ) {
					planLink?.removeAttribute( 'aria-busy' );
				}
			}
		};
		const onPlanClick = ( event: Event ) => {
			if ( ! field.value.trim() ) {
				if ( preparing ) {
					event.preventDefault();
				}
				return;
			}
			event.preventDefault();
			void deliverPlan();
		};
		const onPlanKey = ( event: Event ) => {
			const key = event as KeyboardEvent;
			// Another field's Enter is not this entry's gesture.
			if ( key.target !== field || key.key !== 'Enter' ) {
				return;
			}
			// A composing Enter belongs to the IME; Shift+Enter stays editing.
			if ( key.shiftKey || key.isComposing || key.keyCode === 229 ) {
				return;
			}
			if ( ! field.value.trim() ) {
				return;
			}
			// The LC page registers its own Enter handler on this input before
			// this binder runs, and same-node listeners fire in registration
			// order. A window capture listener runs before the target's list, so
			// the page's plain link click cannot pre-empt the staged delivery.
			event.preventDefault();
			event.stopImmediatePropagation();
			void deliverPlan();
		};
		field.addEventListener( 'input', onInput );
		window.addEventListener( 'keydown', onPlanKey, { capture: true } );
		planLink?.addEventListener( 'click', onPlanClick );
		return () => {
			live = false;
			delete field.dataset.geniePlanBound;
			field.removeEventListener( 'input', onInput );
			window.removeEventListener( 'keydown', onPlanKey, {
				capture: true,
			} );
			planLink?.removeEventListener( 'click', onPlanClick );
			status.remove();
		};
	} );

	return () => {
		cleanup.forEach( ( stop ) => stop() );
		planCleanup.forEach( ( stop ) => stop() );
	};
}
