// @vitest-environment jsdom

/**
 * The browser's dictation, started the same way by the dock and the hero
 * (ticket #232 review round 1, item 4).
 */

/**
 * External dependencies
 */
import { expect, test, vi } from 'vitest';

/**
 * Internal dependencies
 */
import { startDictation, type Dictation } from './dictation';

class FakeRecognition implements Dictation {
	static instances: FakeRecognition[] = [];
	lang = '';
	onresult: Dictation[ 'onresult' ] = null;
	onend: ( () => void ) | null = null;
	onerror: ( () => void ) | null = null;
	started = false;
	stopped = false;

	constructor() {
		FakeRecognition.instances.push( this );
	}

	start(): void {
		this.started = true;
	}

	stop(): void {
		this.stopped = true;
	}
}

class ThrowingRecognition extends FakeRecognition {
	start(): void {
		throw new Error( 'microphone refused' );
	}
}

test( 'the German page dictates in German and hands over each phrase', () => {
	FakeRecognition.instances = [];
	const heard: string[] = [];
	const onEnd = vi.fn();
	const win = {
		SpeechRecognition: FakeRecognition,
	} as unknown as Window;

	const session = startDictation(
		win,
		'de',
		( text ) => heard.push( text ),
		onEnd
	);

	const recognition = FakeRecognition.instances[ 0 ];
	expect( recognition.lang ).toBe( 'de-DE' );
	expect( recognition.started ).toBe( true );
	recognition.onresult?.( {
		results: [ [ { transcript: 'Welcher Speicher passt?' } ] ],
	} );
	expect( heard ).toEqual( [ 'Welcher Speicher passt?' ] );
	session?.stop();
	expect( recognition.stopped ).toBe( true );
	expect( onEnd ).not.toHaveBeenCalled();
} );

test( 'the prefixed engine is used when the standard name is absent', () => {
	FakeRecognition.instances = [];
	const win = {
		webkitSpeechRecognition: FakeRecognition,
	} as unknown as Window;

	const session = startDictation(
		win,
		'en',
		() => undefined,
		() => undefined
	);

	expect( session ).not.toBeNull();
	expect( FakeRecognition.instances[ 0 ].lang ).toBe( 'en-US' );
} );

test( 'an end or an error ends the dictation', () => {
	FakeRecognition.instances = [];
	const onEnd = vi.fn();
	startDictation(
		{ SpeechRecognition: FakeRecognition } as unknown as Window,
		'en',
		() => undefined,
		onEnd
	);

	FakeRecognition.instances[ 0 ].onend?.();
	expect( onEnd ).toHaveBeenCalledTimes( 1 );
} );

test( 'a refused microphone returns no session and ends the attempt', () => {
	const onEnd = vi.fn();
	const session = startDictation(
		{ SpeechRecognition: ThrowingRecognition } as unknown as Window,
		'en',
		() => undefined,
		onEnd
	);

	expect( session ).toBeNull();
	expect( onEnd ).toHaveBeenCalledTimes( 1 );
} );

test( 'a browser without dictation gets no session', () => {
	expect(
		startDictation(
			{} as Window,
			'en',
			() => undefined,
			() => undefined
		)
	).toBeNull();
} );
