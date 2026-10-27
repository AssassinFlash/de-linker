/** Restored artifacts use current authority; transcript words stay historical. */
import { afterEach, expect, test, vi } from 'vitest';
import { resetLocaleData, setLocaleData } from '@wordpress/i18n';
import { restoreArtifacts } from './historyArtifacts';
import { parseStream, readThread } from './turn';
import { ARTIFACT_TIMEOUT_MS } from './product';

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
		document_id: 'doc',
		document_revision: 'revision-1',
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

const permission = {
	schema_version: 1,
	products: [
		{ product_id: 3573, published_locale_ids: [ 3573 ] },
		{ product_id: 1, published_locale_ids: [ 1 ] },
		{ product_id: 2, published_locale_ids: [ 2 ] },
	],
	documents: [
		{
			document_id: 'doc',
			document_revision: 'revision-1',
			url: PDF.split( '#' )[ 0 ],
		},
	],
};

function fetchWith( current: unknown = product, ok = true ) {
	return vi.fn( async ( url: RequestInfo | URL ) => ( {
		ok: String( url ) === '/thread' || ok,
		json: async () => {
			if ( String( url ) === '/thread' ) {
				return {
					messages: [
						{ role: 'user', content: 'Bitte das Datenblatt.' },
					],
					stream,
				};
			}
			if ( String( url ).endsWith( '/publication/manifest' ) ) {
				return permission;
			}
			return current;
		},
	} ) ) as unknown as typeof fetch;
}

const context = { restUrl: '/wp-json/', locale: 'en' as const };

test( 'current native product and publication reads may finish after five seconds', async () => {
	vi.useFakeTimers();
	const immediate = fetchWith();
	const fetcher = vi.fn( async ( ...args: Parameters< typeof fetch > ) => {
		await new Promise( ( resolve ) => setTimeout( resolve, 10_000 ) );
		return immediate( ...args );
	} );
	const restored = restoreArtifacts(
		parseStream( stream ),
		context,
		'current-nonce',
		fetcher
	);
	try {
		await vi.advanceTimersByTimeAsync( 10_000 );
		await expect( restored ).resolves.toMatchObject( {
			blocks: [
				{},
				{
					product_ids: [ 3573 ],
					prices: [ { text: 'Net price after partner sign-in' } ],
				},
				{ url: PDF, sourceTitle: 'SAJ eSolar AIO3 Datasheet (EN)' },
			],
		} );
		expect( vi.getTimerCount() ).toBe( 0 );
	} finally {
		vi.useRealTimers();
	}
} );

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
			url: ok ? PDF : null,
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
					document_id: 'doc',
					document_revision: 'revision-1',
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

test.each( [
	[ 'en' as const, 'pp.' ],
	[ 'de' as const, 'S.' ],
] )(
	'chunk-only citations use the verified native title in %s without product lookups',
	async ( locale, pageWord ) => {
		const title = 'GoodWe Wechselrichtersystem Garantie (DE)';
		const documentWord = locale === 'de' ? 'Dokument' : 'Document';
		setLocaleData( { Document: [ documentWord ] }, 'linker-tools' );
		const url =
			'https://de-linker.test/uploads/GW_Limited-Warranty_Inverter-System_Europe_DE.pdf?download=1#page=2';
		const original = {
			type: 'document' as const,
			ref: 'c99',
			document_id: 'warranty',
			document_revision: 'revision-2',
			label: 'Historical source title · pp. 2, 5',
			url,
		};
		const fetcher = vi.fn( async () => ( {
			ok: true,
			json: async () => ( {
				...permission,
				documents: [
					{
						document_id: 'warranty',
						document_revision: 'revision-2',
						title,
						url: url.split( '#' )[ 0 ],
					},
					{
						document_id: 'missing-title',
						document_revision: 'revision-2',
						title: '   ',
						url: url.split( '#' )[ 0 ],
					},
				],
			} ),
		} ) ) as unknown as typeof fetch;
		const restored = await restoreArtifacts(
			{
				meta: null,
				blocks: [
					original,
					{ ...original, ref: 'c100', document_id: 'missing-title' },
					{ ...original, ref: 'c101', document_revision: 'stale' },
				],
			},
			{ ...context, locale },
			'n',
			fetcher
		);
		expect( restored.blocks[ 0 ] ).toMatchObject( {
			label: `${ title } · ${ pageWord }\u00a02, 5`,
			sourceTitle: title,
			url,
		} );
		expect( restored.blocks[ 1 ] ).toMatchObject( {
			label: `${ documentWord } · GW_Limited-Warranty_Inverter-System_Europe_DE.pdf · ${ pageWord }\u00a02, 5`,
			sourceTitle: 'Historical source title',
			url,
		} );
		expect( restored.blocks[ 2 ] ).toMatchObject( {
			label: original.label,
			url: null,
		} );
		expect( original.label ).toBe( 'Historical source title · pp. 2, 5' );
		expect( fetcher ).toHaveBeenCalledTimes( 1 );
		expect( fetcher ).toHaveBeenCalledWith(
			'/wp-json/linker/v1/publication/manifest',
			expect.any( Object )
		);
	}
);

test( 'unproven historical content identity keeps the transcript but removes its active URL', async () => {
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
		label: original.label,
		url: null,
	} );
	expect( original.label ).toBe(
		'An unnamed specialist certificate · pp. 2, 5'
	);
	expect( fetcher ).toHaveBeenCalledTimes( 1 );
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
				document_id: 'doc',
				document_revision: 'revision-1',
				label: 'Series manual · p. 1',
				url: PDF,
			},
		],
	};
	const fetcher = vi.fn( async ( url: RequestInfo | URL ) => ( {
		ok: true,
		json: async () =>
			String( url ).endsWith( '/publication/manifest' )
				? permission
				: {
						...product,
						product_id: String( url ).includes( 'product_id]=2' )
							? 2
							: 1,
						model: String( url ).includes( 'product_id]=2' )
							? 'Model B'
							: 'Model A',
					},
	} ) ) as unknown as typeof fetch;
	const restored = await restoreArtifacts( turn, context, 'n', fetcher );
	expect( restored.blocks[ 1 ] ).toMatchObject( {
		label: 'Model B · Datasheet (EN) · p.\u00a01',
	} );
} );

test.each( [ 'headers', 'body' ] )(
	'an auxiliary lookup that never resolves at %s is aborted within the bounded current-authority budget',
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
			await vi.advanceTimersByTimeAsync( ARTIFACT_TIMEOUT_MS - 1 );
			expect( settled ).toBe( false );
			await vi.advanceTimersByTimeAsync( 1 );
			expect( settled ).toBe( true );
			expect( signal?.aborted ).toBe( true );
			const restored = await result;
			expect( restored.turn?.blocks[ 1 ] ).toMatchObject( {
				product_ids: [],
				prices: [],
			} );
			expect( restored.turn?.blocks[ 2 ] ).toMatchObject( { url: null } );
			expect( restored.messages[ 1 ].content ).toBe(
				'Hier ist Ihr Datenblatt.'
			);
			expect( vi.getTimerCount() ).toBe( 0 );
		} finally {
			vi.useRealTimers();
		}
	}
);
