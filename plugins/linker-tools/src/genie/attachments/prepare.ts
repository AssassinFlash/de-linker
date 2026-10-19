/**
 * A picked file, ready for the turn (#236, docs/specs/13-genie.md "附件与铭牌").
 *
 * A photo is decoded by the browser (a HEIC photo too, where the browser can
 * open it: Safari on iPhone and Mac), turned upright and drawn again as a JPEG
 * of about 1.69 megapixels: the size deepseek-flash scales every image to
 * (docs/research/2026-10-17-deepseek-flash-vision/ §3.3), a few hundred
 * kilobytes on the wire, and without the camera's metadata — a canvas carries
 * no EXIF, so the GPS position never leaves the phone. A PDF goes as it is;
 * the service reads it. Anything else is refused here, before it is sent; the
 * proxy (Attachments.php) and the service check again.
 *
 * Both the dock and the home page's hero use this (the hero entry, #232).
 */

/** The limits of the proxy (includes/Genie/Attachments.php), mirrored; prepare.test.ts locks them. */
export const MAX_FILES = 3;
export const MAX_IMAGE_BYTES = 6291456;
export const MAX_PDF_BYTES = 16777216;
/** A parts list (#251): one mebibyte of CSV, or a workbook at the image ceiling. */
export const MAX_CSV_BYTES = 1048576;
export const MAX_XLSX_BYTES = 6291456;
export const MAX_TURN_BYTES = 20971520;
export const NAME_LENGTH = 255;
/** The Excel wire type the proxy and the service take (an .xlsx is a zip of XML). */
export const XLSX =
	'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
/** deepseek-flash's own scaling target, about 1300 × 1300 pixels (research §3.3). */
export const TARGET_PIXELS = 1300 * 1300;
/** A notch above libjpeg's default 75: a nameplate's small print stays sharp. */
export const JPEG_QUALITY = 0.85;

/**
 * The accepted types by the bytes each starts with, and WebP's second mark at
 * byte 8: the proxy's Attachments::MAGIC and the service's attachments.MAGIC
 * hold the same table (services/genie/tests/test_attachments.py locks the
 * three). A photo is drawn again as a JPEG here, so only a PDF is checked by
 * its bytes before it is sent.
 */
export const MAGIC: Readonly< Record< string, readonly number[] > > = {
	'image/jpeg': [ 0xff, 0xd8, 0xff ],
	'image/png': [ 0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a ],
	'image/webp': [ 0x52, 0x49, 0x46, 0x46 ],
	'application/pdf': [ 0x25, 0x50, 0x44, 0x46, 0x2d ],
	// A parts list (#251): CSV is text with no first bytes; Excel is a zip of XML.
	'text/csv': [],
	'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': [
		0x50, 0x4b, 0x03, 0x04,
	],
};
export const WEBP_MARK = { offset: 8, bytes: [ 0x57, 0x45, 0x42, 0x50 ] };

/**
 * Whether the bytes start as their type's file does (MAGIC).
 *
 * @param bytes The file.
 * @param type  Its declared type.
 */
export function startsAs( bytes: Uint8Array, type: string ): boolean {
	const magic = MAGIC[ type ];
	if ( ! magic || ! magic.every( ( byte, at ) => bytes[ at ] === byte ) ) {
		return false;
	}
	return (
		type !== 'image/webp' ||
		WEBP_MARK.bytes.every(
			( byte, at ) => bytes[ WEBP_MARK.offset + at ] === byte
		)
	);
}

/** What the file input offers: photos (HEIC included), PDFs and parts lists. */
export const ACCEPT =
	'image/jpeg,image/png,image/webp,image/heic,image/heif,.heic,.heif,application/pdf,.csv,text/csv,.xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';

/** One file as the turn carries it (the service's `Upload`). */
export interface Upload {
	name: string;
	type:
		| 'image/jpeg'
		| 'application/pdf'
		| 'text/csv'
		| 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
	data: string;
}

/** Why a file is not sent: words of the shell (AttachmentNotice). */
export type Refusal = 'type' | 'size' | 'unreadable' | 'heic';

export type Prepared =
	| { ok: true; upload: Upload; bytes: number }
	| { ok: false; reason: Refusal };

type Kind = 'photo' | 'heic' | 'pdf' | 'csv' | 'xlsx' | 'other';

/**
 * What a picked file is, by its type or, when the browser names none (HEIC
 * on some systems), by its extension. A spreadsheet exported by an older
 * Windows setup may arrive as `application/vnd.ms-excel`, so the extension
 * decides between CSV and Excel there.
 *
 * @param file The picked file.
 */
export function kindOf( file: Pick< File, 'name' | 'type' > ): Kind {
	const type = file.type.toLowerCase();
	const extension = /\.([a-z0-9]+)$/i.exec( file.name )?.[ 1 ]?.toLowerCase();
	if ( type === 'application/pdf' || ( ! type && extension === 'pdf' ) ) {
		return 'pdf';
	}
	if (
		type === 'image/heic' ||
		type === 'image/heif' ||
		extension === 'heic' ||
		extension === 'heif'
	) {
		return 'heic';
	}
	if ( [ 'image/jpeg', 'image/png', 'image/webp' ].includes( type ) ) {
		return 'photo';
	}
	if ( type === 'text/csv' || extension === 'csv' ) {
		return 'csv';
	}
	if ( extension === 'xlsx' || type === XLSX ) {
		return 'xlsx';
	}
	return 'other';
}

/**
 * The size a photo is drawn at: the same shape, at most TARGET_PIXELS.
 *
 * @param width  The photo's width.
 * @param height The photo's height.
 */
export function scaledSize(
	width: number,
	height: number
): { width: number; height: number } {
	const pixels = width * height;
	if ( pixels <= TARGET_PIXELS ) {
		return { width, height };
	}
	const scale = Math.sqrt( TARGET_PIXELS / pixels );
	return {
		width: Math.max( 1, Math.floor( width * scale ) ),
		height: Math.max( 1, Math.floor( height * scale ) ),
	};
}

/**
 * A file's name as the thread shows it: a re-encoded photo ends in `.jpg`.
 *
 * @param name      The picked file's name.
 * @param reencoded Whether the file was drawn again as a JPEG.
 */
export function uploadName( name: string, reencoded: boolean ): string {
	const plain = name.replace( /[\u0000-\u001f\u007f]/g, '' ).trim() || 'file';
	const renamed = reencoded
		? plain.replace( /\.(heic|heif|png|webp|jpe?g)$/i, '' ) + '.jpg'
		: plain;
	return renamed.slice( 0, NAME_LENGTH );
}

/**
 * The picked file as the turn carries it, or why it is not sent.
 *
 * @param file The picked file.
 */
export async function prepare( file: File ): Promise< Prepared > {
	const kind = kindOf( file );
	if ( kind === 'other' ) {
		return { ok: false, reason: 'type' };
	}
	if ( kind === 'pdf' ) {
		if ( file.size > MAX_PDF_BYTES ) {
			return { ok: false, reason: 'size' };
		}
		const bytes = await bytesOf( file );
		if ( ! startsAs( bytes, 'application/pdf' ) ) {
			return { ok: false, reason: 'type' };
		}
		return {
			ok: true,
			upload: {
				name: uploadName( file.name, false ),
				type: 'application/pdf',
				data: toBase64( bytes ),
			},
			bytes: bytes.length,
		};
	}
	if ( kind === 'csv' || kind === 'xlsx' ) {
		// A parts list (#251) goes as it is: the service parses the rows, and the
		// file is never stored. CSV is text (no NUL byte); an .xlsx is a zip.
		const max = kind === 'csv' ? MAX_CSV_BYTES : MAX_XLSX_BYTES;
		if ( file.size > max ) {
			return { ok: false, reason: 'size' };
		}
		const bytes = await bytesOf( file );
		if (
			kind === 'csv' ? bytes.includes( 0 ) : ! startsAs( bytes, XLSX )
		) {
			return { ok: false, reason: 'type' };
		}
		return {
			ok: true,
			upload: {
				name: uploadName( file.name, false ),
				type: kind === 'csv' ? 'text/csv' : XLSX,
				data: toBase64( bytes ),
			},
			bytes: bytes.length,
		};
	}
	const jpeg = await reencode( file );
	if ( ! jpeg ) {
		// A HEIC photo the browser cannot open is told apart: the customer
		// can export it as a JPEG, or take the photo in "Most Compatible".
		return { ok: false, reason: kind === 'heic' ? 'heic' : 'unreadable' };
	}
	if ( jpeg.length > MAX_IMAGE_BYTES ) {
		return { ok: false, reason: 'size' };
	}
	return {
		ok: true,
		upload: {
			name: uploadName( file.name, true ),
			type: 'image/jpeg',
			data: toBase64( jpeg ),
		},
		bytes: jpeg.length,
	};
}

/**
 * The photo upright, at most TARGET_PIXELS, as JPEG bytes; null when the
 * browser cannot open it.
 *
 * @param file The picked photo.
 */
async function reencode( file: File ): Promise< Uint8Array | null > {
	let bitmap: ImageBitmap | null = null;
	try {
		// `from-image` applies the camera's orientation before the metadata
		// that carries it is dropped.
		bitmap = await createImageBitmap( file, {
			imageOrientation: 'from-image',
		} );
	} catch {
		return null;
	}
	try {
		const size = scaledSize( bitmap.width, bitmap.height );
		const canvas = document.createElement( 'canvas' );
		canvas.width = size.width;
		canvas.height = size.height;
		const context = canvas.getContext( '2d' );
		if ( ! context ) {
			return null;
		}
		context.drawImage( bitmap, 0, 0, size.width, size.height );
		const blob = await new Promise< Blob | null >( ( resolve ) =>
			canvas.toBlob( resolve, 'image/jpeg', JPEG_QUALITY )
		);
		return blob ? await bytesOf( blob ) : null;
	} finally {
		bitmap.close();
	}
}

/**
 * A file's bytes, through FileReader: the one reader every browser the site
 * serves has, and the test DOM too.
 *
 * @param blob The file.
 */
function bytesOf( blob: Blob ): Promise< Uint8Array > {
	return new Promise( ( resolve, reject ) => {
		const reader = new FileReader();
		reader.onload = () =>
			resolve( new Uint8Array( reader.result as ArrayBuffer ) );
		reader.onerror = () => reject( reader.error );
		reader.readAsArrayBuffer( blob );
	} );
}

/**
 * Bytes as base64, in slices: a whole PDF through one `String.fromCharCode`
 * call overflows the call stack.
 *
 * @param bytes The file.
 */
export function toBase64( bytes: Uint8Array ): string {
	let binary = '';
	const slice = 0x8000;
	for ( let start = 0; start < bytes.length; start += slice ) {
		binary += String.fromCharCode(
			...bytes.subarray( start, start + slice )
		);
	}
	return btoa( binary );
}
