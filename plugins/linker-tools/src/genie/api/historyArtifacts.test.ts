/** Restored artifacts use current authority; transcript words stay historical. */
import { afterEach, expect, test, vi } from 'vitest';
import { resetLocaleData, setLocaleData } from '@wordpress/i18n';
import { restoreArtifacts } from './historyArtifacts';
import { readThread } from './turn';

afterEach( () => resetLocaleData( undefined, 'linker-tools' ) );

const PDF = 'https://de-linker.test/uploads/aio3_datasheet_en.pdf#page=1';
const blocks = [
	{ type: 'text', text: 'Hier ist Ihr Datenblatt.', refs: [] },
	{
		type: 'cards',
		product_ids: [ 3573 ],
		prices: [ { product_id: 3573, text: '1.680,00 €' } ],
	},
	{
		type: 'document',
		ref: 'p3573.document.0',
		label: 'SAJ eSolar AIO3 Datenblatt (EN), Seite 1',
		url: PDF,
	},
];
const stream = [
	[ 'meta', { language: 'de' } ],
	...blocks.map( ( block ) => [ 'block', block ] ),
	[ 'done', { ok: true } ],
]
	.map(
		( [ event, data ] ) =>
			`event: ${ event }\ndata: ${ JSON.stringify( data ) }\n\n`
	)
	.join( '' );
const product = {
	product_id: 3573,
	model: 'eSolar AIO3',
	documents: [
		{
			url: PDF.split( '#' )[ 0 ],
			title: 'SAJ eSolar AIO3 Datasheet (EN)',
			type: 'datasheet',
			lang: 'en',
		},
	],
	commerce: {
		price_visible: false,
		price_line: 'Net price after partner sign-in',
		price_reason: 'login',
	},
};

function fetchWith( current: unknown = product, ok = true ) {
	return vi.fn( async ( url: RequestInfo | URL ) => ( {
		ok: String( url ) === '/thread' || ok,
		json: async () =>
			String( url ) === '/thread'
				? {
						messages: [
							{ role: 'user', content: 'Bitte das Datenblatt.' },
						],
						stream,
					}
				: current,
	} ) ) as unknown as typeof fetch;
}

const context = { restUrl: '/wp-json/', locale: 'en' as const };

test( 'a restored approved price becomes the current visitor line, without changing German transcript or PDF facts', async () => {
	const fetcher = fetchWith();
	const restored = await readThread(
		'/thread',
		'current-nonce',
		fetcher,
		context
	);
	expect( restored.messages.map( ( message ) => message.content ) ).toEqual( [
		'Bitte das Datenblatt.',
		'Hier ist Ihr Datenblatt.',
	] );
	expect( restored.turn?.meta?.language ).toBe( 'de' );
	expect( restored.turn?.blocks[ 1 ] ).toMatchObject( {
		prices: [
			{
				product_id: 3573,
				text: 'Net price after partner sign-in',
				reason: 'login',
			},
		],
	} );
	expect( restored.turn?.blocks[ 2 ] ).toMatchObject( {
		label: 'eSolar AIO3 · Datasheet (EN) · p.\u00a01',
		url: PDF,
		sourceTitle: 'SAJ eSolar AIO3 Datasheet (EN)',
	} );
	expect( fetcher ).toHaveBeenCalledWith(
		expect.stringContaining( 'input[lang]=en' ),
		expect.objectContaining( {
			credentials: 'same-origin',
			cache: 'no-store',
			headers: { 'X-WP-Nonce': 'current-nonce' },
		} )
	);
} );

test.each( [
	[ 'pending', 'Account under review. Prices after approval.' ],
	[ 'restricted', 'Not available for your account' ],
	[ 'project', 'Quoted per project' ],
] )(
	'restoration respects the current %s authority',
	async ( reason, line ) => {
		const fetcher = fetchWith( {
			result: {
				...product,
				commerce: {
					price_visible: false,
					price_line: line,
					price_reason: reason,
				},
			},
		} );
		const restored = await readThread( '/thread', 'n', fetcher, context );
		expect( restored.turn?.blocks[ 1 ] ).toMatchObject( {
			prices: [ { text: line, reason } ],
		} );
		expect( JSON.stringify( restored.turn ) ).not.toContain( '1.680' );
	}
);

test( 'current approved authority supplies the current amount', async () => {
	const fetcher = fetchWith( {
		...product,
		commerce: { price_visible: true, price_line: '€1,700.00' },
	} );
	const restored = await readThread( '/thread', 'n', fetcher, context );
	expect( restored.turn?.blocks[ 1 ] ).toMatchObject( {
		prices: [ { text: '€1,700.00' } ],
	} );
} );

test.each( [
	[ null, false ],
	[
		{
			product_id: 3573,
			commerce: { price_visible: false, price_line: '€1,680' },
		},
		true,
	],
] )(
	'unavailable or incomplete authority never falls back to a historical amount',
	async ( current, ok ) => {
		const restored = await readThread(
			'/thread',
			'n',
			fetchWith( current, ok ),
			context
		);
		expect( restored.turn?.blocks[ 1 ] ).toMatchObject( { prices: [] } );
		expect( restored.messages[ 1 ].content ).toBe(
			'Hier ist Ihr Datenblatt.'
		);
		expect( restored.turn?.blocks[ 2 ] ).toMatchObject( {
			url: PDF,
			sourceTitle: 'SAJ eSolar AIO3 Datenblatt (EN)',
		} );
		expect( JSON.stringify( restored.turn ) ).not.toContain( '1.680' );
	}
);

test( 'document-only history matches authoritative metadata by ref and retains every page and source language', async () => {
	setLocaleData( { Datasheet: [ 'Datenblatt' ] }, 'linker-tools' );
	const restored = await restoreArtifacts(
		{
			meta: null,
			blocks: [
				{
					type: 'document',
					ref: 'p3573.document.0',
					label: 'SAJ eSolar AIO3 Datasheet (EN) · pp. 1, 3, 7',
					url: PDF,
				},
			],
		},
		{ ...context, locale: 'de' },
		'n',
		fetchWith()
	);
	expect( restored.blocks[ 0 ] ).toMatchObject( {
		label: 'eSolar AIO3 · Datenblatt (EN) · S.\u00a01, 3, 7',
		url: PDF,
		sourceTitle: 'SAJ eSolar AIO3 Datasheet (EN)',
	} );
} );

test( 'unknown metadata is not guessed or translated; current Document UI preserves the original title and URL', async () => {
	setLocaleData( { Document: [ 'Dokument' ] }, 'linker-tools' );
	const original = {
		type: 'document' as const,
		ref: 'c99',
		label: 'An unnamed specialist certificate · pp. 2, 5',
		url: 'https://de-linker.test/uploads/specialist-file_en.pdf#page=2',
	};
	const fetcher = fetchWith();
	const restored = await restoreArtifacts(
		{ meta: null, blocks: [ original ] },
		{ ...context, locale: 'de' },
		'n',
		fetcher
	);
	expect( restored.blocks[ 0 ] ).toMatchObject( {
		label: 'Dokument · specialist-file_en.pdf · S.\u00a02, 5',
		url: original.url,
		sourceTitle: 'An unnamed specialist certificate',
	} );
	expect( original.label ).toBe(
		'An unnamed specialist certificate · pp. 2, 5'
	);
	expect( fetcher ).not.toHaveBeenCalled();
} );

test.each( [ undefined, 'false', true ] )(
	'a missing or contradictory price visibility field is not authority (%s)',
	async ( visible ) => {
		const restored = await readThread(
			'/thread',
			'n',
			fetchWith( {
				...product,
				commerce: {
					price_visible: visible,
					price_line: 'Net price after partner sign-in',
					price_reason: 'login',
				},
			} ),
			context
		);
		expect( restored.turn?.blocks[ 1 ] ).toMatchObject( { prices: [] } );
	}
);

test( 'a shared series PDF is attributed to the document ref product rather than the first card', async () => {
	const turn = {
		meta: null,
		blocks: [
			{ type: 'cards' as const, product_ids: [ 1, 2 ] },
			{
				type: 'document' as const,
				ref: 'p2.document.0',
				label: 'Series manual · p. 1',
				url: PDF,
			},
		],
	};
	const fetcher = vi.fn( async ( url: RequestInfo | URL ) => ( {
		ok: true,
		json: async () => ( {
			...product,
			product_id: String( url ).includes( 'product_id]=2' ) ? 2 : 1,
			model: String( url ).includes( 'product_id]=2' )
				? 'Model B'
				: 'Model A',
		} ),
	} ) ) as unknown as typeof fetch;
	const restored = await restoreArtifacts( turn, context, 'n', fetcher );
	expect( restored.blocks[ 1 ] ).toMatchObject( {
		label: 'Model B · Datasheet (EN) · p.\u00a01',
	} );
} );

test.each( [ 'headers', 'body' ] )(
	'an auxiliary lookup that never resolves at %s is aborted at the five-second presentation budget',
	async ( stage ) => {
		vi.useFakeTimers();
		let signal: AbortSignal | undefined;
		const fetcher = vi.fn(
			async ( _url: RequestInfo | URL, options?: RequestInit ) => {
				signal = options?.signal ?? undefined;
				if ( stage === 'headers' ) {
					return new Promise< Response >( () => undefined );
				}
				return {
					ok: true,
					json: () => new Promise( () => undefined ),
				} as unknown as Response;
			}
		);
		try {
			const result = readThread(
				'/thread',
				'n',
				( ( url, options ) =>
					String( url ) === '/thread'
						? fetchWith()( url, options )
						: fetcher( url, options ) ) as typeof fetch,
				context
			);
			let settled = false;
			void result.then( () => {
				settled = true;
			} );
			await vi.advanceTimersByTimeAsync( 4_999 );
			expect( settled ).toBe( false );
			await vi.advanceTimersByTimeAsync( 1 );
			expect( settled ).toBe( true );
			expect( signal?.aborted ).toBe( true );
			const restored = await result;
			expect( restored.turn?.blocks[ 1 ] ).toMatchObject( {
				prices: [],
			} );
			expect( restored.messages[ 1 ].content ).toBe(
				'Hier ist Ihr Datenblatt.'
			);
			expect( vi.getTimerCount() ).toBe( 0 );
		} finally {
			vi.useRealTimers();
		}
	}
);
