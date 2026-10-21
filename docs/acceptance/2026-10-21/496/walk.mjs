/**
 * Local snapshot walk for #496 (Ask Genie on the design report).
 *
 * The design report's "Ask Genie" saves the solution first and opens Genie on
 * it; Genie reads the solution through linker/read-solution and cites its
 * figures. This walk covers approved and guest, EN and DE, 1440 and 390, the
 * pending price-gate state, another customer's id, and the save-once reuse.
 *
 * Instance: w496 on http://127.0.0.1:9267 (snapshot 20261021-1023). No inquiry,
 * no registration, no mail. The owner is user 43, the other customer user 44.
 *
 * Run (each phase needs fresh one-time links, they are one-use):
 *   W496_OWNER_LOGIN=$(just login w496 --user=w496owner | tail -1) \
 *   W496_OTHER_LOGIN=$(just login w496 --user=w496other | tail -1) \
 *   PHASE=main node walk.mjs
 *   PHASE=pending|restricted node walk.mjs   (owner state set first)
 */
import { createRequire } from 'node:module';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(
	'/Users/chesterjohn/Documents/de-linker/tests/e2e/package.json'
);
const { chromium } = require('playwright');

const here = dirname(fileURLToPath(import.meta.url));
const shotsDir = join(here, 'shots');
mkdirSync(shotsDir, { recursive: true });

const ORIGIN = 'http://127.0.0.1:9267';
// No password lives in the repository. The two accounts log in with the local
// stack's one-time link (`just login w496 --user=…`), passed for this run only;
// the link is one-use, so each PHASE gets fresh ones.
const LOGIN_URLS = {
	owner: process.env.W496_OWNER_LOGIN || '',
	other: process.env.W496_OTHER_LOGIN || '',
};
const MONEY = /(?:€|EUR)\s*\d|\d[\d.,]*\s*(?:€|EUR)/;
const INPUTS = { plz: '80538', annual: '5000', pv: '10' };

const CASES = {
	en: {
		path: '/solution-configurator/',
		locale: 'en-GB',
		plz: /Postcode of the site/,
		annual: /Annual household consumption/,
		pv: /PV array/,
		calculate: 'Calculate system',
		save: 'Save solution',
		ask: 'Ask Genie',
		question: 'Show me the products of my solution as cards.',
		loginPrice: 'Log in for prices',
	},
	de: {
		path: '/de/loesungskonfigurator/',
		locale: 'de-DE',
		plz: /Postleitzahl des Standorts/,
		annual: /Jahresverbrauch des Haushalts/,
		pv: /PV-Leistung/,
		calculate: 'System berechnen',
		save: 'Lösung speichern',
		ask: 'Genie fragen',
		question: 'Zeigen Sie mir die Produkte meiner Lösung als Karten.',
		loginPrice: 'Preise nach Anmeldung',
	},
};

const record = {
	ticket: 496,
	instance: 'w496',
	origin: ORIGIN,
	snapshot: '20261021-1023',
	accountStates: ['guest', 'pending', 'approved'],
	owner: 43,
	other: 44,
	mailSent: false,
	inquirySent: false,
	registered: false,
	startedAt: new Date().toISOString(),
	cases: [],
	ability: {},
	reuse: {},
	otherCustomer: {},
	priceGate: {},
};

function saveRecord() {
	writeFileSync( join( here, 'record.json' ), JSON.stringify( record, null, 2 ) );
}

function numbers( text ) {
	return ( text || '' ).match( /\d[\d.,]*/g ) || [];
}

const loginStates = new Map();

/**
 * The storage state of a logged-in account, from its one-time login link.
 * Captured once per run; every case context reuses it.
 */
async function loginState( browser, which ) {
	if ( loginStates.has( which ) ) {
		return loginStates.get( which );
	}
	const url = LOGIN_URLS[ which ];
	if ( ! url ) {
		throw new Error(
			`set W496_${ which.toUpperCase() }_LOGIN to a one-time link: just login w496 --user=w496${ which }`
		);
	}
	const context = await browser.newContext();
	const page = await context.newPage();
	await page.goto( url, { waitUntil: 'domcontentloaded' } );
	// A customer who logs in is sent on to the account page (the site's own
	// gate), not to wp-admin; leaving the login page is the signed-in mark.
	await page.waitForFunction(
		() => ! location.pathname.includes( 'wp-login' ),
		null,
		{ timeout: 30000 }
	);
	const state = await context.storageState();
	await context.close();
	loginStates.set( which, state );
	return state;
}

async function resetThread( page, lang ) {
	// Genie keeps a signed-in customer's conversation with the account, so a
	// new browser context restores the last case's thread. Every case starts
	// from its own empty conversation.
	await page.goto( ORIGIN + CASES[ lang ].path, {
		waitUntil: 'domcontentloaded',
	} );
	await page.evaluate( async () => {
		const app = document.querySelector( '[data-linker-app="genie"]' );
		const nonce = app.dataset.restNonce;
		const list = await fetch( '/wp-json/linker-ai/v1/genie/conversations', {
			credentials: 'same-origin',
			headers: { 'X-WP-Nonce': nonce },
		} )
			.then( ( response ) => response.json() )
			.catch( () => null );
		for ( const conversation of list?.conversations || [] ) {
			await fetch(
				`/wp-json/linker-ai/v1/genie/conversations/${ conversation.id }`,
				{
					method: 'DELETE',
					credentials: 'same-origin',
					headers: { 'X-WP-Nonce': nonce },
				}
			);
		}
	} );
}

async function dismissConsent( page ) {
	// The snapshot's consent banner covers the lower half of the page. Reject
	// the optional purposes (no analytics requests) so the screenshots show
	// the report and the dock, not the banner.
	for ( const label of [ /Reject all/i, /Alle ablehnen/i, /Ablehnen/i ] ) {
		const button = page.getByRole( 'button', { name: label } ).first();
		if ( await button.count() ) {
			await button.click( { timeout: 2000 } ).catch( () => undefined );
			await page.waitForTimeout( 400 );
			return;
		}
	}
}

async function generateReport( page, lang ) {
	const c = CASES[ lang ];
	await dismissConsent( page );
	await page.getByLabel( c.plz ).fill( INPUTS.plz );
	await page.getByLabel( c.annual ).fill( INPUTS.annual );
	await page.getByLabel( c.pv ).fill( INPUTS.pv );
	await page.getByRole( 'button', { name: c.calculate } ).click();
	await page.locator( '#linker-report-section' ).waitFor( {
		state: 'visible',
		timeout: 90000,
	} );
	const report = page.locator( '#linker-report-section' );
	await report.scrollIntoViewIfNeeded();
	const text = ( await report.innerText() ).replace( /\s+/g, ' ' );
	return { text, numbers: numbers( text ) };
}

async function ask( page, lang ) {
	const c = CASES[ lang ];
	const report = page.locator( '#linker-report-section' );
	const button = report.getByRole( 'button', { name: c.ask } );
	await button.scrollIntoViewIfNeeded();
	await button.click();
}

async function waitAnswerCount( page, moreThan ) {
	await page.waitForFunction(
		( n ) => document.querySelectorAll( '.linker-genie-message-body' ).length > n,
		moreThan,
		{ timeout: 120000 }
	);
	// The text reveals itself; the cards below it follow the same answer.
	await page.waitForTimeout( 2000 );
}

async function cardPrices( page ) {
	const cards = page.locator( '.linker-genie-app__cards .linker-card' );
	const seen = new Set();
	const ids = [];
	const prices = [];
	const count = await cards.count();
	for ( let index = 0; index < count; index++ ) {
		const card = cards.nth( index );
		const id = ( await card.getAttribute( 'id' ) ) || `card-${ index }`;
		if ( seen.has( id ) ) {
			continue;
		}
		seen.add( id );
		ids.push( id );
		const price = card.locator( '.linker-card__price' );
		prices.push(
			( await price.count() ) > 0
				? ( await price.first().innerText() ).trim()
				: ''
		);
	}
	return { cards: ids.length, prices };
}

async function answerCount( page ) {
	return page.locator( '.linker-genie-message-body' ).count();
}

async function lastAnswer( page ) {
	const bodies = page.locator( '.linker-genie-message-body' );
	const count = await bodies.count();
	return ( await bodies.nth( count - 1 ).innerText() ).replace( /\s+/g, ' ' );
}

async function shot( page, name ) {
	await page.screenshot( { path: join( shotsDir, `${ name }.png` ) } );
}

async function caseAccount( browser, lang, viewport, account ) {
	const c = CASES[ lang ];
	const storageState =
		account === 'guest' ? undefined : await loginState( browser, 'owner' );
	const context = await browser.newContext( {
		viewport,
		locale: c.locale,
		...( storageState ? { storageState } : {} ),
	} );
	const page = await context.newPage();
	const solutions = [];
	const turns = [];
	page.on( 'response', async ( response ) => {
		const request = response.request();
		if (
			request.method() === 'POST' &&
			response.url().includes( '/linker/v1/solutions' )
		) {
			solutions.push( {
				status: response.status(),
				body: await response.json().catch( () => null ),
			} );
		}
		if (
			request.method() === 'POST' &&
			response.url().includes( '/genie/turn' )
		) {
			turns.push( {
				status: response.status(),
				page: ( request.postDataJSON() || {} ).page || null,
			} );
		}
	} );

	await resetThread( page, lang );
	const report = await generateReport( page, lang );
	const signedIn = await page
		.locator( '[data-linker-app="genie"]' )
		.getAttribute( 'data-signed-in' );
	if ( account !== 'guest' && signedIn !== '1' ) {
		throw new Error( `${ account } is not signed in` );
	}
	const caseRecord = {
		lang,
		viewport: viewport.name,
		account,
		signedIn,
		reportExcerpt: report.text.slice( 0, 600 ),
		reportNumbers: report.numbers.slice( 0, 20 ),
	};
	if ( account === 'guest' ) {
		await ask( page, lang );
		await page
			.locator( '.linker-report__ask-note' )
			.waitFor( { state: 'visible', timeout: 60000 } );
		caseRecord.note = (
			await page.locator( '.linker-report__ask-note' ).innerText()
		).replace( /\s+/g, ' ' );
		caseRecord.solutions = solutions;
		caseRecord.turns = turns;
		caseRecord.answer = null;
		await shot( page, `${ account }-${ lang }-${ viewport.name }-report` );
		record.cases.push( caseRecord );
		await context.close();
		return;
	}

	// The approved state: Ask saves once, opens Genie, and the answer cites
	// the report's own figures.
	const before = await answerCount( page );
	await ask( page, lang );
	await waitAnswerCount( page, before );
	const answer = await lastAnswer( page );
	caseRecord.answer = answer;
	caseRecord.solutions = solutions;
	caseRecord.turns = turns;
	caseRecord.solutionId = solutions[ 0 ]?.body?.id ?? 0;
	caseRecord.cited = report.numbers.filter( ( n ) => answer.includes( n ) );
	await shot( page, `${ account }-${ lang }-${ viewport.name }-answer` );

	// The products as cards: their price line follows this account.
	const answered = await answerCount( page );
	await page.fill( '#linker-genie-input', c.question );
	await page.press( '#linker-genie-input', 'Enter' );
	await waitAnswerCount( page, answered );
	const found = await cardPrices( page );
	caseRecord.cardPrices = found.prices;
	caseRecord.cards = found.cards;
	caseRecord.cardAnswer = ( await lastAnswer( page ) ).slice( 0, 800 );
	await shot( page, `${ account }-${ lang }-${ viewport.name }-cards` );
	record.cases.push( caseRecord );
	await context.close();
}

async function reuseCase( browser ) {
	const context = await browser.newContext( {
		viewport: { width: 1440, height: 1000 },
		locale: CASES.en.locale,
		storageState: await loginState( browser, 'owner' ),
	} );
	const page = await context.newPage();
	const solutions = [];
	const turns = [];
	page.on( 'response', async ( response ) => {
		const request = response.request();
		if (
			request.method() === 'POST' &&
			response.url().includes( '/linker/v1/solutions' )
		) {
			solutions.push( response.status() );
		}
		if (
			request.method() === 'POST' &&
			response.url().includes( '/genie/turn' )
		) {
			turns.push( ( request.postDataJSON() || {} ).page || null );
		}
	} );
	await resetThread( page, 'en' );
	await generateReport( page, 'en' );
	const report = page.locator( '#linker-report-section' );
	await page.getByRole( 'button', { name: 'Save solution' } ).click();
	await page
		.locator( '.linker-actions__status', { hasText: 'Saved to your account.' } )
		.waitFor( { state: 'visible', timeout: 60000 } );
	await report.getByRole( 'button', { name: 'Ask Genie' } ).click();
	await page.waitForFunction(
		() => document.querySelectorAll( '.linker-genie-message-body' ).length > 0,
		null,
		{ timeout: 120000 }
	);
	await page.waitForTimeout( 3000 );
	record.reuse = {
		savePosts: solutions.length,
		statuses: solutions,
		turns,
	};
	await context.close();
}

async function abilityCase( browser, solutionId ) {
	// An owner, a guest, and another customer ask the same ability directly.
	const request = async ( account ) => {
		const storageState =
			account === 'guest'
				? undefined
				: await loginState( browser, account === 'owner' ? 'owner' : 'other' );
		const context = await browser.newContext( {
			viewport: { width: 1440, height: 1000 },
			locale: 'en-GB',
			...( storageState ? { storageState } : {} ),
		} );
		const page = await context.newPage();
		await page.goto( ORIGIN + CASES.en.path, {
			waitUntil: 'domcontentloaded',
		} );
		const result = await page.evaluate( async ( id ) => {
			const app = document.querySelector( '[data-linker-app="genie"]' );
			const response = await fetch(
				`/wp-json/wp-abilities/v1/abilities/linker/read-solution/run?input%5Bsolution_id%5D=${ id }&input%5Blang%5D=en`,
				{
					credentials: 'same-origin',
					headers: { 'X-WP-Nonce': app.dataset.restNonce },
				}
			);
			const body = await response.text();
			return { status: response.status, body };
		}, solutionId );
		await context.close();
		return result;
	};
	record.ability = {
		owner: await request( 'owner' ),
		guest: await request( 'guest' ),
		other: await request( 'other' ),
	};
	record.otherCustomer = {
		solutionId,
		status: record.ability.other.status,
		refused: record.ability.other.status === 403,
	};
}

async function gateCase( browser, state ) {
	// The pending account still reads its own solution and sees no price.
	const context = await browser.newContext( {
		viewport: { width: 1440, height: 1000 },
		locale: 'en-GB',
		storageState: await loginState( browser, 'owner' ),
	} );
	const page = await context.newPage();
	const solutions = [];
	page.on( 'response', async ( response ) => {
		if (
			response.request().method() === 'POST' &&
			response.url().includes( '/linker/v1/solutions' )
		) {
			solutions.push( {
				status: response.status(),
				body: await response.json().catch( () => null ),
			} );
		}
	} );
	await resetThread( page, 'en' );
	const report = await generateReport( page, 'en' );
	await ask( page, 'en' );
	await page.waitForFunction(
		() => document.querySelectorAll( '.linker-genie-message-body' ).length > 0,
		null,
		{ timeout: 120000 }
	);
	// The answer reveals itself character by character; read it once whole.
	await page.waitForTimeout( 3000 );
	const answer = await lastAnswer( page );
	const answered = await answerCount( page );
	await page.fill( '#linker-genie-input', CASES.en.question );
	await page.press( '#linker-genie-input', 'Enter' );
	await waitAnswerCount( page, answered );
	const found = await cardPrices( page );
	const solutionId = solutions[ 0 ]?.body?.id ?? 0;
	const direct = await page.evaluate( async ( id ) => {
		const app = document.querySelector( '[data-linker-app="genie"]' );
		const response = await fetch(
			`/wp-json/wp-abilities/v1/abilities/linker/read-solution/run?input%5Bsolution_id%5D=${ id }&input%5Blang%5D=en`,
			{
				credentials: 'same-origin',
				headers: { 'X-WP-Nonce': app.dataset.restNonce },
			}
		);
		return { status: response.status, body: await response.text() };
	}, solutionId );
	record.priceGate[ state ] = {
		state,
		answer: answer.slice( 0, 500 ),
		cited: report.numbers.filter( ( n ) => answer.includes( n ) ),
		cardPrices: found.prices,
		cards: found.cards,
		solutionId,
		abilityStatus: direct.status,
		money: MONEY.test( direct.body ),
		body: direct.body.slice( 0, 300 ),
	};
	await shot( page, `${ state }-en-1440-answer` );
	await context.close();
}

const PHASE = process.env.PHASE || 'main';
const browser = await chromium.launch( { headless: true } );
try {
	if ( PHASE === 'pending' || PHASE === 'restricted' ) {
		Object.assign(
			record,
			JSON.parse( readFileSync( join( here, 'record.json' ), 'utf8' ) )
		);
		await gateCase( browser, PHASE );
		record.finishedAt = new Date().toISOString();
		saveRecord();
	} else {
		const viewports = [
			{ name: '1440', width: 1440, height: 1000 },
			{ name: '390', width: 390, height: 844 },
		];
		for ( const lang of [ 'en', 'de' ] ) {
			for ( const viewport of viewports ) {
				await caseAccount( browser, lang, viewport, 'guest' );
				saveRecord();
				await caseAccount( browser, lang, viewport, 'approved' );
				saveRecord();
			}
		}
		await reuseCase( browser );
		saveRecord();
		const approved = record.cases.find(
			( item ) =>
				item.account === 'approved' &&
				item.lang === 'en' &&
				item.solutionId
		);
		await abilityCase( browser, approved?.solutionId ?? 0 );
		record.priceGate.approved = {
			status: record.ability.owner.status,
			money: MONEY.test( record.ability.owner.body ),
		};
		record.priceGate.guest = {
			status: record.ability.guest.status,
			money: MONEY.test( record.ability.guest.body ),
		};
		saveRecord();
	}
} finally {
	await browser.close();
}
