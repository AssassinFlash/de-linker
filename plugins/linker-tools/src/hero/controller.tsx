/**
 * The home hero's controls, wired to the conversation in place (ticket #232,
 * variant B). The hero is the LiveCanvas page's own markup; this controller
 * binds its textarea, send button, capsules, nameplate, attachment and voice
 * buttons, folds the eyebrow/title/subtitle/capsules/footnote away, and
 * mounts the conversation above the textarea — which stays the follow-up
 * field.
 *
 * Closing restores the page's hero; out of sight, a button beside the dock
 * hands the same conversation to the dock. Nothing here navigates: the send
 * button and capsules keep their live href as the no-JavaScript fallback.
 */

/**
 * WordPress dependencies
 */
import { createRoot } from '@wordpress/element';
import { __ } from '@wordpress/i18n';

/**
 * Internal dependencies
 */
import type { GenieConfig } from '../genie/config';
import { ACCEPT } from '../genie/attachments/prepare';
import {
	startDictation,
	type DictationSession,
} from '../genie/shared/dictation';
import { readFailure, pageFailureStore } from '../genie/shared/failure';
import { HeroConversation, type HeroBridge } from './Hero';
import { HeroSession } from './session';
import {
	heroExpanded,
	heroReducer,
	initialHeroState,
	pillVisible,
	type HeroEvent,
	type HeroState,
} from './state';

/** The class that folds the hero's own words away and grows the dialog. */
export const OPEN_CLASS = 'linker-genie-hero--open';

/** The class of the way back beside the dock button. */
export const PILL_CLASS = 'linker-genie-hero-pill';

/** The id every hero trigger points at with aria-controls. */
export const SURFACE_ID = 'linker-genie-hero-surface';

export interface HeroControllerOptions {
	config: GenieConfig;
	/** The window (tests pass their own). */
	win?: Window;
	/** The conversation for one unfolding; a test passes a session double. */
	session?: HeroSession;
	/** How a fresh unfolding reads the shared thread. */
	createSession?: () => HeroSession;
}

/**
 * Starts the hero's behaviour.
 *
 * @param hero    The page's `.hero-cinematic`.
 * @param options The mount's config and test seams.
 * @return A teardown that removes every listener and the injected DOM.
 */
export function startHero(
	hero: HTMLElement,
	options: HeroControllerOptions
): () => void {
	const win = options.win ?? window;
	const doc = win.document;
	const prompt = hero.querySelector< HTMLTextAreaElement >( '.hero-prompt' );
	const dialog = hero.querySelector< HTMLElement >( '.hero-dialog' );
	const sendButton = hero.querySelector< HTMLElement >( '.hero-send' );
	if ( ! prompt || ! dialog || ! sendButton ) {
		return () => undefined;
	}

	const originalPlaceholder = prompt.placeholder;
	const makeSession =
		options.createSession ??
		( () =>
			options.session ??
			new HeroSession( {
				restUrl: options.config.restUrl,
				turnUrl: options.config.turnUrl,
				threadUrl: options.config.threadUrl,
				nonce: options.config.restNonce,
				locale: options.config.locale,
				page: options.config.page,
			} ) );

	let state: HeroState = initialHeroState;
	let expandedNow = false;
	let root: ReturnType< typeof createRoot > | null = null;
	let bridge: HeroBridge | null = null;
	let pending: { text: string; files?: ArrayLike< File > } | null = null;
	let pill: HTMLButtonElement | null = null;
	let recognition: DictationSession | null = null;
	// The control that opened the conversation: focus returns to it on close.
	let lastTrigger: HTMLElement | null = null;
	// The six controls, for aria-expanded / aria-controls (populated below).
	const triggers: HTMLElement[] = [];

	// The conversation's container exists from the start, hidden, so every
	// trigger's aria-controls resolves even while the hero is resting. It
	// carries no content until the conversation unfolds.
	const host = doc.createElement( 'div' );
	host.className = 'linker-genie-hero__host';
	host.id = SURFACE_ID;
	host.hidden = true;
	dialog!.insertBefore( host, dialog!.firstChild );

	const picker = doc.createElement( 'input' );
	picker.type = 'file';
	picker.hidden = true;
	picker.accept = ACCEPT;
	doc.body.append( picker );

	function update( event: HeroEvent ): void {
		state = heroReducer( state, event );
		render();
	}

	function render(): void {
		const expanded = heroExpanded( state );
		if ( expanded !== expandedNow ) {
			expandedNow = expanded;
			hero.classList.toggle( OPEN_CLASS, expanded );
			triggers.forEach( ( trigger ) =>
				trigger.setAttribute( 'aria-expanded', String( expanded ) )
			);
			if ( expanded ) {
				prompt!.placeholder = __( 'Ask a follow-up…', 'linker-tools' );
				mount();
			} else {
				prompt!.placeholder = originalPlaceholder;
				prompt!.value = '';
				unmount();
			}
		}
		syncPill();
	}

	function mount(): void {
		if ( root ) {
			return;
		}
		host.hidden = false;
		root = createRoot( host );
		const session = makeSession();
		root.render(
			<HeroConversation
				config={ options.config }
				session={ session }
				onReady={ onReady }
				onContinue={ continueToPanel }
				onClose={ close }
				onConversation={ ( has ) =>
					update( { type: 'conversation', has } )
				}
				readPrompt={ () => prompt!.value }
				setPrompt={ ( text ) => {
					prompt!.value = text;
				} }
				focusPrompt={ () => prompt!.focus() }
				requestPicker={ openPicker }
			/>
		);
	}

	function unmount(): void {
		// A dictation the closed hero started must not keep the microphone.
		recognition?.stop();
		recognition = null;
		bridge = null;
		if ( root ) {
			root.unmount();
			root = null;
		}
		host.hidden = true;
		host.replaceChildren();
	}

	function onReady( next: HeroBridge ): void {
		bridge = next;
		if ( pending ) {
			const { text, files } = pending;
			pending = null;
			next.ask( text, files );
		}
	}

	/**
	 * Opens the conversation and asks one question (or sends picked files).
	 *
	 * @param text    The question; empty when the files are the question.
	 * @param files   Files from the page's picker.
	 * @param trigger The page's control that started it; focus returns there.
	 */
	function runAsk(
		text: string,
		files?: ArrayLike< File >,
		trigger?: HTMLElement
	): void {
		if ( ! text.trim() && ! ( files && files.length > 0 ) ) {
			return;
		}
		if ( trigger ) {
			lastTrigger = trigger;
		}
		update( { type: 'ask' } );
		if ( bridge ) {
			bridge.ask( text, files );
			return;
		}
		pending = { text, files };
	}

	/** Folds the conversation back to the resting hero. */
	function close(): void {
		const trigger = lastTrigger;
		lastTrigger = null;
		update( { type: 'close' } );
		// The hero is back: the control that opened it takes the focus again
		// (review round 1, item 3).
		trigger?.focus?.();
	}

	/**
	 * Hands the conversation to the standing dock, then restores the hero.
	 * The loader forwards `refresh` and `fromHome` to the app, which re-reads
	 * the thread and marks it as asked from the homepage.
	 */
	function continueToPanel(): void {
		win.dispatchEvent(
			new CustomEvent( 'linker-genie-ask', {
				detail: { refresh: true, fromHome: true },
			} )
		);
		close();
	}

	function openPicker(): void {
		// One accepted set for both buttons: prepare.ts refuses what Genie
		// cannot read, and the nameplate button may still receive a PDF.
		picker.accept = ACCEPT;
		// A pick of the same file again must fire again.
		picker.value = '';
		picker.click();
	}

	function dictate(): void {
		if ( recognition ) {
			recognition.stop();
			recognition = null;
			return;
		}
		const session = startDictation(
			win,
			options.config.locale,
			( heard ) => {
				prompt!.value = prompt!.value
					? `${ prompt!.value } ${ heard }`
					: heard;
			},
			() => {
				recognition = null;
			}
		);
		if ( ! session ) {
			// No dictation, or a refused microphone: the field is the way in.
			prompt!.focus();
			return;
		}
		recognition = session;
	}

	function syncPill(): void {
		const show = pillVisible( state );
		if ( show && ! pill ) {
			pill = doc.createElement( 'button' );
			pill.type = 'button';
			pill.className = PILL_CLASS;
			const mark = doc.createElement( 'span' );
			mark.setAttribute( 'aria-hidden', 'true' );
			mark.textContent = '✦';
			pill.append(
				mark,
				doc.createTextNode(
					' ' +
						__(
							'Your Genie conversation · continue',
							'linker-tools'
						)
				)
			);
			pill.addEventListener( 'click', continueToPanel );
			doc.body.append( pill );
		}
		if ( pill ) {
			pill.hidden = ! show;
		}
	}

	function onKeyDown( event: KeyboardEvent ): void {
		if ( event.key === 'Enter' && ! event.shiftKey ) {
			event.preventDefault();
			runAsk( prompt!.value, undefined, prompt! );
		}
	}

	function onSendClick( event: MouseEvent ): void {
		// The live anchor is the no-JavaScript fallback; with the script the
		// conversation opens in place instead of leaving the page.
		event.preventDefault();
		runAsk( prompt!.value, undefined, sendButton! );
	}

	function capsuleClick( capsule: Element ): ( event: Event ) => void {
		return ( event: Event ) => {
			event.preventDefault();
			runAsk(
				( capsule.textContent ?? '' ).trim(),
				undefined,
				capsule as HTMLElement
			);
		};
	}

	const photoButton = hero.querySelector< HTMLElement >(
		'[data-linker-assistant-open="nameplate"]'
	);
	const attachButton = hero.querySelector< HTMLElement >(
		'[data-linker-assistant-open="attach"]'
	);
	const voiceButton = hero.querySelector< HTMLElement >(
		'[data-linker-assistant-open="voice"]'
	);

	function onPhotoClick( event: Event ): void {
		event.preventDefault();
		lastTrigger = photoButton;
		if ( ! heroExpanded( state ) ) {
			update( { type: 'ask' } );
		}
		openPicker();
	}

	function onAttachClick( event: Event ): void {
		event.preventDefault();
		lastTrigger = attachButton;
		if ( ! heroExpanded( state ) ) {
			update( { type: 'ask' } );
		}
		openPicker();
	}

	function onVoiceClick( event: Event ): void {
		event.preventDefault();
		lastTrigger = voiceButton;
		if ( ! heroExpanded( state ) ) {
			update( { type: 'ask' } );
		}
		dictate();
	}

	function onPickerChange(): void {
		const files = picker.files;
		if ( files && files.length > 0 ) {
			runAsk( '', files );
		}
		picker.value = '';
	}

	function isOutOfSight(): boolean {
		const rect = hero.getBoundingClientRect();
		// jsdom has no layout: height 0 is not "scrolled past the hero".
		return rect.height > 0 && rect.bottom <= 0;
	}

	function onScroll(): void {
		update( { type: 'scroll', out: isOutOfSight() } );
	}

	function onDockState( event: Event ): void {
		const detail = ( event as CustomEvent< { open?: unknown } > ).detail;
		update( { type: 'dock', open: !! detail?.open } );
	}

	const capsules = Array.from(
		hero.querySelectorAll< HTMLElement >( '.hero-capsule' )
	).map( ( capsule ) => ( {
		capsule,
		listener: capsuleClick( capsule ),
	} ) );

	// The six triggers announce the surface they control (review round 1,
	// item 3): the textarea with Enter, the send button, every capsule, the
	// nameplate, attachment and voice buttons.
	[
		prompt,
		sendButton,
		...capsules.map( ( { capsule } ) => capsule ),
		photoButton,
		attachButton,
		voiceButton,
	].forEach( ( trigger ) => {
		if ( ! trigger ) {
			return;
		}
		triggers.push( trigger );
		trigger.setAttribute( 'aria-expanded', 'false' );
		trigger.setAttribute( 'aria-controls', SURFACE_ID );
	} );

	prompt.addEventListener( 'keydown', onKeyDown );
	sendButton.addEventListener( 'click', onSendClick );
	photoButton?.addEventListener( 'click', onPhotoClick );
	attachButton?.addEventListener( 'click', onAttachClick );
	voiceButton?.addEventListener( 'click', onVoiceClick );
	picker.addEventListener( 'change', onPickerChange );
	win.addEventListener( 'scroll', onScroll, { passive: true } );
	win.addEventListener( 'resize', onScroll );
	win.addEventListener( 'linker-genie-state', onDockState );
	capsules.forEach( ( { capsule, listener } ) =>
		capsule.addEventListener( 'click', listener )
	);
	// The suite's readiness signal: the controls are bound (no visual change).
	hero.setAttribute( 'data-linker-genie-hero', 'ready' );
	onScroll();
	// A failed turn from before this load unfolds the conversation, so the
	// error is on the page without another click (ticket #411).
	if ( readFailure( pageFailureStore() ) ) {
		update( { type: 'ask' } );
	}

	return () => {
		prompt.removeEventListener( 'keydown', onKeyDown );
		sendButton.removeEventListener( 'click', onSendClick );
		photoButton?.removeEventListener( 'click', onPhotoClick );
		attachButton?.removeEventListener( 'click', onAttachClick );
		voiceButton?.removeEventListener( 'click', onVoiceClick );
		picker.removeEventListener( 'change', onPickerChange );
		win.removeEventListener( 'scroll', onScroll );
		win.removeEventListener( 'resize', onScroll );
		win.removeEventListener( 'linker-genie-state', onDockState );
		capsules.forEach( ( { capsule, listener } ) =>
			capsule.removeEventListener( 'click', listener )
		);
		unmount();
		host.remove();
		pill?.remove();
		picker.remove();
		recognition?.stop();
		hero.removeAttribute( 'data-linker-genie-hero' );
		hero.classList.remove( OPEN_CLASS );
		prompt.placeholder = originalPlaceholder;
	};
}
