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

export function bindMarketingEntries(
	root: Document,
	config: GenieConfig
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
		const section =
			field.closest< HTMLElement >(
				'#system-search, .installer-mobile-assistant'
			) ?? field.parentElement;
		if ( ! section ) {
			return () => undefined;
		}
		// Installer markup's field/send share the nearest mobile panel. Never bind desktop Plan.
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
	return () => cleanup.forEach( ( stop ) => stop() );
}
