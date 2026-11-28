import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { runInNewContext } from 'node:vm';
import { expect, it, vi } from 'vitest';

const source = readFileSync( resolve( 'assets/hero-loader.js' ), 'utf8' );

function home() {
	const doc = document.implementation.createHTMLDocument();
	doc.body.innerHTML =
		'<section class="hero-cinematic"><textarea class="hero-prompt"></textarea><a class="hero-send" href="/de/genie/">Senden</a><a class="hero-capsule" href="/de/genie/">Vergleichen</a></section><script type="application/json" data-linker-hero-loader>{"src":"hero.js"}</script>';
	const events = new EventTarget();
	const load = vi
		.fn< () => Promise< void > >()
		.mockResolvedValue( undefined );
	const assign = vi.fn();
	runInNewContext( source, {
		document: doc,
		window: {
			addEventListener: events.addEventListener.bind( events ),
			location: { assign },
			linkerLoadGenieEntry: load,
		},
	} );
	return {
		prompt: doc.querySelector( 'textarea' )!,
		capsule: doc.querySelector< HTMLAnchorElement >( '.hero-capsule' )!,
		send: doc.querySelector< HTMLAnchorElement >( '.hero-send' )!,
		ready: () =>
			events.dispatchEvent( new Event( 'linker-genie-hero-ready' ) ),
		assign,
		load,
	};
}

it( 'replays the first capsule click after binding the hero', () => {
	const { capsule, load, ready } = home();
	expect( load ).not.toHaveBeenCalled();
	capsule.click();
	expect( load ).toHaveBeenCalledTimes( 1 );
	const opened = vi.fn( ( event: Event ) => event.preventDefault() );
	capsule.addEventListener( 'click', opened );
	ready();
	expect( opened ).toHaveBeenCalledTimes( 1 );
} );

it( 'keeps typed text and submits the first Enter after boot', () => {
	const { prompt, load, send, ready } = home();
	prompt.dispatchEvent( new Event( 'focusin', { bubbles: true } ) );
	prompt.value = 'Which inverter fits?';
	prompt.dispatchEvent( new Event( 'input', { bubbles: true } ) );
	prompt.dispatchEvent(
		new KeyboardEvent( 'keydown', {
			bubbles: true,
			cancelable: true,
			key: 'Enter',
		} )
	);
	const onSend = vi.fn( ( event: Event ) => event.preventDefault() );
	send.addEventListener( 'click', onSend );
	ready();
	expect( load ).toHaveBeenCalledTimes( 1 );
	expect( onSend ).toHaveBeenCalledTimes( 1 );
	expect( prompt.value ).toBe( 'Which inverter fits?' );
} );

it( 'uses the localized link when the bundle fails', async () => {
	const { capsule, assign, load } = home();
	load.mockRejectedValue( new Error( 'unavailable' ) );
	capsule.click();
	await vi.waitFor( () =>
		expect( assign ).toHaveBeenCalledWith( capsule.href )
	);
} );
