import { describe, expect, it, vi } from 'vitest';
import { readContact, sendContact } from './contact';
import { readInquiry, sendInquiry } from './inquiry';

describe.each( [ '', 'wp-account-nonce' ] )(
	'native transfer identity %s',
	( nonce ) => {
		it( 'keeps REST cookie authentication exclusive to signed-in reads and submissions', async () => {
			const fetcher = vi.fn< typeof fetch >(
				async () => new Response( '{}', { status: 200 } )
			);
			await readContact( '/contact', nonce, fetcher );
			await readInquiry( '/inquiry', nonce, 'en', fetcher );
			await sendContact(
				'/contact',
				nonce,
				{
					source: '7:2',
					reason: 'asked',
					website: '',
					locale: 'en',
					page: { type: 'home' },
				},
				fetcher
			);
			await sendInquiry(
				'/inquiry',
				nonce,
				{
					source: '7:2',
					message: 'Contact me',
					attachSummary: false,
					lines: 'draft',
					website: '',
					locale: 'en',
				},
				fetcher
			);
			for ( const [ , init ] of fetcher.mock.calls ) {
				expect( new Headers( init?.headers ).get( 'X-WP-Nonce' ) ).toBe(
					nonce || null
				);
			}
		} );
	}
);
