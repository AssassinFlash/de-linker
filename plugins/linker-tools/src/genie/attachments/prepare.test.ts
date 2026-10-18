/**
 * A picked file, ready for the turn (#236): a photo redrawn small and without
 * its metadata, a PDF as it is, anything else refused before it is sent.
 */

/**
 * External dependencies
 */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { afterEach, describe, expect, it, vi } from 'vitest';

/**
 * Internal dependencies
 */
import {
	JPEG_QUALITY,
	MAX_FILES,
	MAX_IMAGE_BYTES,
	MAX_PDF_BYTES,
	MAX_TURN_BYTES,
	NAME_LENGTH,
	TARGET_PIXELS,
	kindOf,
	prepare,
	scaledSize,
	toBase64,
	uploadName,
} from './prepare';

afterEach( () => {
	vi.unstubAllGlobals();
} );

describe( 'the limits', () => {
	it( 'are the proxy’s own', () => {
		const php = readFileSync(
			resolve( __dirname, '../../../includes/Genie/Attachments.php' ),
			'utf8'
		);
		const constant = ( name: string ) =>
			Number(
				new RegExp( `const ${ name }\\s*=\\s*(\\d+);` ).exec(
					php
				)?.[ 1 ]
			);
		expect( constant( 'MAX_FILES' ) ).toBe( MAX_FILES );
		expect( constant( 'MAX_IMAGE_BYTES' ) ).toBe( MAX_IMAGE_BYTES );
		expect( constant( 'MAX_PDF_BYTES' ) ).toBe( MAX_PDF_BYTES );
		expect( constant( 'MAX_TURN_BYTES' ) ).toBe( MAX_TURN_BYTES );
		expect( constant( 'NAME_LENGTH' ) ).toBe( NAME_LENGTH );
	} );
} );

describe( 'kindOf', () => {
	it.each( [
		[ 'plate.jpg', 'image/jpeg', 'photo' ],
		[ 'plate.webp', 'image/webp', 'photo' ],
		[ 'IMG_0001.HEIC', '', 'heic' ],
		[ 'IMG_0001.heic', 'image/heic', 'heic' ],
		[ 'datasheet.pdf', 'application/pdf', 'pdf' ],
		[ 'datasheet.pdf', '', 'pdf' ],
		[ 'list.xlsx', 'application/vnd.ms-excel', 'other' ],
		[ 'icon.svg', 'image/svg+xml', 'other' ],
		[ 'setup.exe', 'application/octet-stream', 'other' ],
	] )( '%s (%s) is %s', ( name, type, kind ) => {
		expect( kindOf( { name, type } ) ).toBe( kind );
	} );
} );

describe( 'scaledSize', () => {
	it( 'shrinks a 12-megapixel photo to about 1.69 megapixels, same shape', () => {
		const { width, height } = scaledSize( 4032, 3024 );
		expect( width * height ).toBeLessThanOrEqual( TARGET_PIXELS );
		expect( width * height ).toBeGreaterThan( TARGET_PIXELS * 0.99 );
		expect( width / height ).toBeCloseTo( 4 / 3, 2 );
	} );

	it( 'leaves a small photo as it is', () => {
		expect( scaledSize( 800, 600 ) ).toEqual( { width: 800, height: 600 } );
	} );
} );

describe( 'uploadName', () => {
	it( 'names a redrawn photo .jpg and keeps a PDF’s name', () => {
		expect( uploadName( 'IMG_0001.HEIC', true ) ).toBe( 'IMG_0001.jpg' );
		expect( uploadName( 'plate.png', true ) ).toBe( 'plate.jpg' );
		expect( uploadName( 'ds.pdf', false ) ).toBe( 'ds.pdf' );
		expect( uploadName( 'a\u0000b.pdf', false ) ).toBe( 'ab.pdf' );
		expect( uploadName( 'x'.repeat( 400 ), false ) ).toHaveLength(
			NAME_LENGTH
		);
	} );
} );

describe( 'prepare', () => {
	it( 'sends a PDF as it is', async () => {
		const file = new File( [ '%PDF-1.7 datasheet' ], 'ds.pdf', {
			type: 'application/pdf',
		} );
		const result = await prepare( file );
		expect( result ).toEqual( {
			ok: true,
			upload: {
				name: 'ds.pdf',
				type: 'application/pdf',
				data: btoa( '%PDF-1.7 datasheet' ),
			},
			bytes: 18,
		} );
	} );

	it( 'refuses a file named PDF that is not one', async () => {
		const file = new File( [ 'MZ program' ], 'ds.pdf', {
			type: 'application/pdf',
		} );
		expect( await prepare( file ) ).toEqual( {
			ok: false,
			reason: 'type',
		} );
	} );

	it( 'refuses a PDF over the limit before reading it', async () => {
		const file = new File( [ '%PDF-' ], 'manual.pdf', {
			type: 'application/pdf',
		} );
		Object.defineProperty( file, 'size', { value: MAX_PDF_BYTES + 1 } );
		expect( await prepare( file ) ).toEqual( {
			ok: false,
			reason: 'size',
		} );
	} );

	it( 'refuses what is neither a photo nor a PDF', async () => {
		const file = new File( [ 'x' ], 'list.xlsx', {
			type: 'application/vnd.ms-excel',
		} );
		expect( await prepare( file ) ).toEqual( {
			ok: false,
			reason: 'type',
		} );
	} );

	it( 'says when the browser cannot open a HEIC photo', async () => {
		vi.stubGlobal(
			'createImageBitmap',
			vi.fn( async () => {
				throw new DOMException( 'unsupported', 'InvalidStateError' );
			} )
		);
		const file = new File( [ 'heic' ], 'IMG_0001.HEIC', { type: '' } );
		expect( await prepare( file ) ).toEqual( {
			ok: false,
			reason: 'heic',
		} );
	} );

	it( 'redraws a photo upright as a small JPEG, through a canvas', async () => {
		const close = vi.fn();
		const open = vi.fn( async () => ( {
			width: 4000,
			height: 3000,
			close,
		} ) );
		vi.stubGlobal( 'createImageBitmap', open );
		const drawImage = vi.fn();
		vi.spyOn( HTMLCanvasElement.prototype, 'getContext' ).mockReturnValue( {
			drawImage,
		} as unknown as CanvasRenderingContext2D );
		const toBlob = vi
			.spyOn( HTMLCanvasElement.prototype, 'toBlob' )
			.mockImplementation( function ( callback ) {
				callback(
					new Blob( [ new Uint8Array( [ 0xff, 0xd8, 0xff ] ) ] )
				);
			} );
		const file = new File( [ 'jpeg' ], 'IMG_0001.HEIC', {
			type: 'image/heic',
		} );

		const result = await prepare( file );

		expect( open ).toHaveBeenCalledWith( file, {
			imageOrientation: 'from-image',
		} );
		const [ , , , width, height ] = drawImage.mock.calls[ 0 ];
		expect( width * height ).toBeLessThanOrEqual( TARGET_PIXELS );
		expect( toBlob ).toHaveBeenCalledWith(
			expect.any( Function ),
			'image/jpeg',
			JPEG_QUALITY
		);
		expect( close ).toHaveBeenCalled();
		expect( result ).toEqual( {
			ok: true,
			upload: { name: 'IMG_0001.jpg', type: 'image/jpeg', data: '/9j/' },
			bytes: 3,
		} );
	} );
} );

describe( 'toBase64', () => {
	it( 'encodes a file larger than one call can take', () => {
		const bytes = new Uint8Array( 200_000 ).fill( 65 );
		expect( atob( toBase64( bytes ) ) ).toBe( 'A'.repeat( 200_000 ) );
	} );
} );
