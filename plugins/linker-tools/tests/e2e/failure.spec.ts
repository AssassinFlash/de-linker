/**
 * A failed Genie turn in Chromium (ticket #411). The proxy is this page's
 * route: a cut stream and a 502, then one retry that does answer.
 */

/**
 * External dependencies
 */
import { expect, test, type Page, type Route } from '@playwright/test';

const CUT =
	'event: meta\n' +
	'data: {"grounded":true,"fallback":false,"attempts":1,"failures":[],"language":"en"}\n\n' +
	'event: block\n' +
	'data: {"type":"text","text":"10 kW from a cut stream","refs":[]}\n\n';

const DONE =
	'event: meta\n' +
	'data: {"turn_id":8,"grounded":true,"fallback":false,"attempts":1,"failures":[],"language":"en"}\n\n' +
	'event: block\n' +
	'data: {"type":"text","text":"A hybrid inverter covers that.","refs":[]}\n\n' +
	'event: done\n' +
	'data: {"ok":true}\n\n';

const STORY = '/iframe.html?id=genie-app--english&viewMode=story';

type Mode = 'cut' | 'down' | 'ok';

/**
 * Stands in for the proxy. `cut` stores the question and an unfinished
 * stream. `down` stores nothing. `ok` stores a finished answer.
 *
 * @param page The Playwright page.
 */
function installProxy( page: Page ): {
	mode: { current: Mode };
	posts: { n: number };
} {
	const mode: { current: Mode } = { current: 'cut' };
	const posts = { n: 0 };
	const thread: {
		messages: { role: string; content: string }[];
		stream: string;
	} = { messages: [], stream: '' };

	void page.route(
		'**/wp-json/linker-ai/v1/genie/**',
		async ( route: Route ) => {
			const request = route.request();
			const path = new URL( request.url() ).pathname;
			if (
				'GET' === request.method() &&
				path.endsWith( '/conversations' )
			) {
				await route.fulfill( {
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify( {
						current_id: 7,
						conversations: [],
					} ),
				} );
				return;
			}
			if (
				'GET' === request.method() &&
				path.endsWith( '/conversation' )
			) {
				await route.fulfill( {
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify( {
						conversation_id: 7,
						messages: thread.messages,
						stream: thread.stream,
						contacts: [],
						inquiries: [],
					} ),
				} );
				return;
			}
			if ( 'POST' === request.method() && path.endsWith( '/turn' ) ) {
				posts.n += 1;
				if ( 'down' === mode.current ) {
					await route.fulfill( {
						status: 502,
						contentType: 'application/json',
						body: JSON.stringify( {
							code: 'linker_genie_upstream',
							message: 'Bad gateway',
						} ),
					} );
					return;
				}
				const body = request.postDataJSON() as {
					messages?: { role: string; content: string }[];
				};
				const stream = 'cut' === mode.current ? CUT : DONE;
				thread.messages = ( body.messages ?? [] ).map(
					( message ) => ( {
						role: message.role,
						content: message.content,
					} )
				);
				thread.stream = stream;
				await route.fulfill( {
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify( { conversation_id: 7, stream } ),
				} );
				return;
			}
			await route.fulfill( {
				status: 404,
				contentType: 'application/json',
				body: '{}',
			} );
		}
	);
	return { mode, posts };
}

test( 'a cut stream survives a reload and retries once', async ( { page } ) => {
	const proxy = installProxy( page );
	proxy.mode.current = 'cut';
	await page.goto( STORY );
	await page.getByRole( 'button', { name: 'Open' } ).click();
	await page
		.getByLabel( 'Ask Genie' )
		.fill( 'How much backup does a home with 10 kW need?' );
	await page.getByRole( 'button', { name: 'Send' } ).click();

	const alert = page.getByRole( 'alert' );
	await expect( alert ).toHaveText(
		'Genie did not answer. Please try again.'
	);
	await expect(
		page.getByText( 'How much backup does a home with 10 kW need?' )
	).toBeVisible();
	await expect( page.getByText( '10 kW from a cut stream' ) ).toHaveCount(
		0
	);
	await expect( page.getByLabel( 'Ask Genie' ) ).toHaveValue( '' );

	await page.reload();
	await expect( alert ).toHaveText(
		'Genie did not answer. Please try again.'
	);
	await expect(
		page.getByText( 'How much backup does a home with 10 kW need?' )
	).toBeVisible();
	await expect( page.getByText( '10 kW from a cut stream' ) ).toHaveCount(
		0
	);

	proxy.mode.current = 'ok';
	await page.getByRole( 'button', { name: 'Try again' } ).click();
	await expect(
		page.getByText( 'A hybrid inverter covers that.' )
	).toBeVisible();
	expect( proxy.posts.n ).toBe( 2 );
} );

test( 'a 502 puts the question back and a reload still offers retry', async ( {
	page,
} ) => {
	const proxy = installProxy( page );
	proxy.mode.current = 'down';
	await page.goto( STORY );
	await page.getByRole( 'button', { name: 'Open' } ).click();
	const question = 'Which hybrid inverter fits this house?';
	await page.getByLabel( 'Ask Genie' ).fill( question );
	await page.getByRole( 'button', { name: 'Send' } ).click();

	const alert = page.getByRole( 'alert' );
	await expect( alert ).toHaveText(
		'Genie did not answer. Please try again.'
	);
	await expect( page.getByLabel( 'Ask Genie' ) ).toHaveValue( question );
	await expect(
		page
			.locator( '.linker-genie-app__message' )
			.filter( { hasText: question } )
	).toHaveCount( 0 );

	await page.reload();
	await expect( alert ).toHaveText(
		'Genie did not answer. Please try again.'
	);
	await expect( page.getByLabel( 'Ask Genie' ) ).toHaveValue( question );

	proxy.mode.current = 'ok';
	await page.getByRole( 'button', { name: 'Try again' } ).click();
	await expect(
		page.getByText( 'A hybrid inverter covers that.' )
	).toBeVisible();
	expect( proxy.posts.n ).toBe( 2 );
} );
