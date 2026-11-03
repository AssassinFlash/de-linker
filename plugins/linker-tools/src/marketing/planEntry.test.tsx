// @vitest-environment jsdom
/** Installer desktop Plan stages the typed requirement before it navigates. */
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { readConfig } from '../genie/config';
import { bindMarketingEntries } from './entries';
import {
	PROJECT_BRIEF_KEY,
	readProjectBrief,
} from '../genie/shared/projectBriefDraft';

const SCOPE = 'c'.repeat( 64 );
let stop: ( () => void ) | null = null;
let navigations: string[] = [];
let stageReply: ( body: Record< string, unknown > ) => unknown = () => ( {} );

function planPage( value = '' ): void {
	document.body.innerHTML = `
		<div id="installer-journal">
			<div class="lk-hero-console">
				<div class="lk-console-input-row">
					<input id="lki-hero-query" type="text" />
					<a class="lk-btn-query" href="/solution-configurator/">Plan a Project Solution</a>
				</div>
			</div>
		</div>`;
	( document.querySelector( '#lki-hero-query' ) as HTMLInputElement ).value =
		value;
}

beforeEach( () => {
	sessionStorage.clear();
	navigations = [];
	stageReply = ( body ) => ( {
		schema_version: 1,
		brief_id: 'f'.repeat( 32 ),
		revision: 'e'.repeat( 64 ),
		text: body.text,
		source_path: body.source_path,
		scope: SCOPE,
	} );
	vi.stubGlobal(
		'fetch',
		vi.fn( async ( url: string, init?: RequestInit ) => {
			if ( String( url ).includes( 'entry-context' ) ) {
				return {
					ok: true,
					json: async () => ( { scope: SCOPE } ),
				};
			}
			const body = JSON.parse( String( init?.body ?? '{}' ) ) as Record<
				string,
				unknown
			>;
			return { ok: true, json: async () => stageReply( body ) };
		} )
	);
} );

afterEach( () => {
	stop?.();
	stop = null;
	document.body.innerHTML = '';
	vi.unstubAllGlobals();
} );

function bind(): HTMLInputElement {
	planPage();
	const mount = document.createElement( 'div' );
	const config = readConfig( mount );
	stop = bindMarketingEntries( document, config, ( url ) =>
		navigations.push( url )
	);
	return document.querySelector< HTMLInputElement >( '#lki-hero-query' )!;
}

test( 'Plan stages the exact typed requirement and never puts it in the URL', async () => {
	const field = bind();
	field.value =
		'SAJ H2-10K on a west roof, -40 °C winters, 6000 W load, no backup.';
	const link =
		document.querySelector< HTMLAnchorElement >( '.lk-btn-query' )!;
	await Promise.resolve();
	link.click();
	await vi.waitFor( () => expect( navigations ).toHaveLength( 1 ) );
	const [ destination ] = navigations;
	expect( destination ).toMatch(
		/\/solution-configurator\/\?brief=[a-f0-9]{32}$/
	);
	expect( destination ).not.toContain( 'SAJ' );
	expect( destination ).not.toContain( encodeURIComponent( 'SAJ' ) );
	// The staged record the configurator will read back is the same text.
	const stored = readProjectBrief( SCOPE );
	expect( stored?.text ).toBe(
		'SAJ H2-10K on a west roof, -40 °C winters, 6000 W load, no backup.'
	);
	expect( stored?.id ).toBe( 'f'.repeat( 32 ) );
} );

test( 'a staging failure keeps the source text and does not navigate', async () => {
	const field = bind();
	stageReply = () => {
		throw new Error( 'stage failed' );
	};
	vi.stubGlobal(
		'fetch',
		vi.fn( async ( url: string ) => {
			if ( String( url ).includes( 'entry-context' ) ) {
				return { ok: true, json: async () => ( { scope: SCOPE } ) };
			}
			return { ok: false, json: async () => ( {} ) };
		} )
	);
	field.value = 'A requirement that cannot be staged yet';
	await Promise.resolve();
	document.querySelector< HTMLAnchorElement >( '.lk-btn-query' )!.click();
	await vi.waitFor( () =>
		expect( document.body.textContent ).toContain(
			'The project note could not be carried over. Your text is still here.'
		)
	);
	expect( navigations ).toHaveLength( 0 );
	expect( field.value ).toBe( 'A requirement that cannot be staged yet' );
} );

test( 'an empty Plan field leaves the ordinary configurator navigation alone', async () => {
	const field = bind();
	field.value = '   ';
	const link =
		document.querySelector< HTMLAnchorElement >( '.lk-btn-query' )!;
	let preventedByBinder: boolean | null = null;
	// Runs after the binder's own listener (target) during the bubble phase, so
	// it observes the decision without performing a jsdom navigation.
	document.addEventListener(
		'click',
		( event ) => {
			preventedByBinder = event.defaultPrevented;
			event.preventDefault();
		},
		{ once: true }
	);
	link.dispatchEvent(
		new MouseEvent( 'click', { bubbles: true, cancelable: true } )
	);
	expect( preventedByBinder ).toBe( false );
	await Promise.resolve();
	expect( navigations ).toHaveLength( 0 );
	expect( sessionStorage.getItem( PROJECT_BRIEF_KEY ) ).toBeNull();
} );

test( 'the page own Enter handler cannot pre-empt the staged delivery', async () => {
	// The LC page registers an Enter handler on the input before the binder runs
	// and clicks the plain link. Two guarantees are asserted: the binder decides
	// first (its listener is registered on the window's capture phase, so it runs
	// ahead of every listener on the input), and even if a page handler does fire,
	// the link's own click is intercepted instead of navigating with lost text.
	planPage();
	const field =
		document.querySelector< HTMLInputElement >( '#lki-hero-query' )!;
	const link =
		document.querySelector< HTMLAnchorElement >( '.lk-btn-query' )!;
	let pageClicks = 0;
	field.addEventListener( 'keydown', ( event ) => {
		if ( ( event as KeyboardEvent ).key === 'Enter' ) {
			event.preventDefault();
			pageClicks += 1;
			link.click();
		}
	} );
	const mount = document.createElement( 'div' );
	stop = bindMarketingEntries( document, readConfig( mount ), ( url ) =>
		navigations.push( url )
	);
	field.value = 'SAJ H2-10K with a 6000 W load';
	await Promise.resolve();
	field.dispatchEvent(
		new KeyboardEvent( 'keydown', {
			key: 'Enter',
			bubbles: true,
			cancelable: true,
		} )
	);
	await vi.waitFor( () => expect( navigations ).toHaveLength( 1 ) );
	// The page's handler never fired, so its plain link click never happened.
	expect( pageClicks ).toBe( 0 );
	expect( navigations[ 0 ] ).toContain( '?brief=' );
	expect( readProjectBrief( SCOPE )?.text ).toBe(
		'SAJ H2-10K with a 6000 W load'
	);
} );

test( 'Enter plans once; Shift and composing Enter stay in the field', async () => {
	const field = bind();
	field.value = 'One line requirement';
	await Promise.resolve();
	const shift = new KeyboardEvent( 'keydown', {
		key: 'Enter',
		shiftKey: true,
		bubbles: true,
		cancelable: true,
	} );
	expect( field.dispatchEvent( shift ) ).toBe( true );
	expect( navigations ).toHaveLength( 0 );

	const composing = new KeyboardEvent( 'keydown', {
		key: 'Enter',
		isComposing: true,
		bubbles: true,
		cancelable: true,
	} );
	expect( field.dispatchEvent( composing ) ).toBe( true );
	expect( navigations ).toHaveLength( 0 );

	field.dispatchEvent(
		new KeyboardEvent( 'keydown', {
			key: 'Enter',
			bubbles: true,
			cancelable: true,
		} )
	);
	await vi.waitFor( () => expect( navigations ).toHaveLength( 1 ) );
} );
