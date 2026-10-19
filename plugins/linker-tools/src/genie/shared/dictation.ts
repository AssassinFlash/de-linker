/**
 * The browser's own speech recognition (ticket #232 review round 1, item 4):
 * the dock's microphone and the home hero's voice button share one start,
 * stop and failure rule. No vendor service: where the browser has none, the
 * caller gets null and keeps its field.
 */

/**
 * Internal dependencies
 */
import type { Locale } from '../../configurator/types';

/** The browser's speech recognition, structurally (lib.dom's interface). */
export interface Dictation {
	lang: string;
	onresult:
		| ( ( event: {
				results: ArrayLike< ArrayLike< { transcript: string } > >;
		  } ) => void )
		| null;
	onend: ( () => void ) | null;
	onerror: ( () => void ) | null;
	start: () => void;
	stop: () => void;
}

export type DictationCtor = new () => Dictation;

/** A running dictation; stop it on unmount or when the visitor asks again. */
export interface DictationSession {
	stop: () => void;
}

declare global {
	interface Window {
		SpeechRecognition?: DictationCtor;
		webkitSpeechRecognition?: DictationCtor;
	}
}

/**
 * Starts dictation in the browser's own engine.
 *
 * @param win          The window (a test passes its own).
 * @param locale       The page language: de-DE or en-US.
 * @param onTranscript Called with each heard phrase.
 * @param onEnd        Called when the engine ends or errors, and when start()
 *                     refuses the microphone.
 * @return The running session, or null when the browser has no dictation.
 */
export function startDictation(
	win: Window,
	locale: Locale,
	onTranscript: ( text: string ) => void,
	onEnd: () => void
): DictationSession | null {
	const Ctor = win.SpeechRecognition ?? win.webkitSpeechRecognition;
	if ( ! Ctor ) {
		return null;
	}
	const session = new Ctor();
	session.lang = 'de' === locale ? 'de-DE' : 'en-US';
	session.onresult = ( event ) => {
		const heard = event.results[ 0 ]?.[ 0 ]?.transcript ?? '';
		if ( heard ) {
			onTranscript( heard );
		}
	};
	session.onend = onEnd;
	session.onerror = onEnd;
	try {
		session.start();
	} catch {
		// A browser that refuses the microphone ends the attempt; the caller
		// keeps its own field.
		session.onend = null;
		session.onerror = null;
		onEnd();
		return null;
	}
	return { stop: () => session.stop() };
}
