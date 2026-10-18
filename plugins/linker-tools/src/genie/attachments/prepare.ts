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
export const MAX_TURN_BYTES = 20971520;
export const NAME_LENGTH = 255;
/** deepseek-flash's own scaling target, about 1300 × 1300 pixels (research §3.3). */
export const TARGET_PIXELS = 1300 * 1300;
/** A notch above libjpeg's default 75: a nameplate's small print stays sharp. */
export const JPEG_QUALITY = 0.85;

/** What the file input offers: photos (HEIC included) and PDFs. */
export const ACCEPT =
	'image/jpeg,image/png,image/webp,image/heic,image/heif,.heic,.heif,application/pdf';

/** One file as the turn carries it (the service's `Upload`). */
export interface Upload {
	name: string;
	type: 'image/jpeg' | 'application/pdf';
	data: string;
}

/** Why a file is not sent: words of the shell (AttachmentNotice). */
export type Refusal = 'type' | 'size' | 'unreadable' | 'heic';

export type Prepared =
	| { ok: true; upload: Upload; bytes: number }
	| { ok: false; reason: Refusal };

type Kind = 'photo' | 'heic' | 'pdf' | 'other';

/**
 * What a picked file is, by its type or, when the browser names none (HEIC
 * on some systems), by its extension.
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
		if ( new TextDecoder().decode( bytes.slice( 0, 5 ) ) !== '%PDF-' ) {
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
