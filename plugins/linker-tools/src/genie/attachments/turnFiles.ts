/** Large draft uploads are held by the browser. The session journal keeps their owner and order. */
import type { Upload } from './prepare';

interface FileRef {
	file: string;
	name: string;
}
interface Snapshot {
	text?: string;
	id: string;
	uploads: Upload[];
	expires?: number;
}
const prefix = 'linker-genie-turn-failure:v2:';
const loaded = new Map< string, Upload >();
function fileKey( scope: string, upload: Upload ): string | undefined {
	for ( const [ id, file ] of loaded ) {
		if (
			id.startsWith( scope + ':' ) &&
			file.name === upload.name &&
			file.type === upload.type &&
			file.data === upload.data
		) {
			return id;
		}
	}
	return undefined;
}
let connection: Promise< IDBDatabase > | undefined;

function database(): Promise< IDBDatabase > {
	if ( ! connection ) {
		connection = new Promise< IDBDatabase >( ( resolve, reject ) => {
			const open = indexedDB.open( 'linker-genie-attachments', 1 );
			open.onupgradeneeded = () =>
				open.result
					.createObjectStore( 'snapshots', { keyPath: 'id' } )
					.createIndex( 'expires', 'expires' );
			open.onsuccess = () => resolve( open.result );
			open.onerror = () => reject( open.error );
		} ).catch( ( error ) => {
			connection = undefined;
			throw error;
		} );
	}
	return connection;
}

async function write( snapshot: Snapshot ): Promise< boolean > {
	if ( typeof indexedDB === 'undefined' ) {
		return false;
	}
	try {
		const db = await database();
		await new Promise< void >( ( resolve, reject ) => {
			const tx = db.transaction( 'snapshots', 'readwrite' );
			const store = tx.objectStore( 'snapshots' );
			store.put( snapshot );
			const expired = store
				.index( 'expires' )
				.openCursor( IDBKeyRange.upperBound( Date.now() ) );
			expired.onsuccess = () => {
				const cursor = expired.result;
				if ( cursor ) {
					cursor.delete();
					cursor.continue();
				}
			};
			tx.oncomplete = () => resolve();
			tx.onabort = () => reject( tx.error );
		} );
		return true;
	} catch {
		// The journal still uses native session storage and explicitly names files it cannot retain.
		return false;
	}
}

async function read( id: string ): Promise< Snapshot | undefined > {
	if ( typeof indexedDB === 'undefined' ) {
		return undefined;
	}
	try {
		const db = await database();
		return await new Promise< Snapshot | undefined >(
			( resolve, reject ) => {
				const request = db
					.transaction( 'snapshots' )
					.objectStore( 'snapshots' )
					.get( id );
				request.onsuccess = () =>
					resolve(
						request.result && request.result.expires > Date.now()
							? request.result
							: undefined
					);
				request.onerror = () => reject( request.error );
			}
		);
	} catch {
		return undefined;
	}
}

export async function removeFiles( id: string ): Promise< void > {
	if ( typeof indexedDB === 'undefined' ) {
		return;
	}
	const db = await database();
	const tx = db.transaction( 'snapshots', 'readwrite' );
	tx.objectStore( 'snapshots' ).delete( id );
	await new Promise< void >( ( resolve, reject ) => {
		tx.oncomplete = () => resolve();
		tx.onabort = () => reject( tx.error );
	} );
}

export async function keepPickedFile( scope: string, upload: Upload ) {
	if ( fileKey( scope, upload ) ) {
		return;
	}
	const id = scope + ':' + crypto.randomUUID();
	// The browser claim and its conversation expire together (Genie Retention).
	if (
		await write( {
			id,
			uploads: [ upload ],
			expires: Date.now() + 90 * 24 * 60 * 60 * 1000,
		} )
	) {
		loaded.set( id, upload );
	}
}

/**
 * Compact only a journal write which otherwise exceeds the session-storage quota.
 * @param key
 * @param raw
 */
export function compactFiles( key: string, raw: string ): string {
	if ( ! key.startsWith( prefix ) ) {
		return raw;
	}
	const scope = key.slice( prefix.length );
	const bucket = JSON.parse( raw );
	for ( const entry of Object.values( bucket.records ) as {
		record: { uploads: ( Upload | FileRef )[] };
	}[] ) {
		entry.record.uploads = entry.record.uploads.map( ( file ) => {
			if ( ! ( 'data' in file ) ) {
				return file;
			}
			const id = fileKey( scope, file );
			return id?.startsWith( scope + ':' )
				? { file: id, name: file.name }
				: file;
		} );
	}
	return JSON.stringify( bucket );
}

export function expandFiles( key: string, raw: string | null ): string | null {
	if ( ! raw || ! key.startsWith( prefix ) || ! raw.includes( '"file":' ) ) {
		return raw;
	}
	const bucket = JSON.parse( raw );
	for ( const entry of Object.values( bucket.records ) as {
		record: { uploads: ( Upload | FileRef )[]; omitted: string[] };
	}[] ) {
		entry.record.uploads = entry.record.uploads.flatMap(
			( file ): Upload[] => {
				if ( ! ( 'file' in file ) ) {
					return [ file ];
				}
				const restored = file.file.startsWith(
					key.slice( prefix.length ) + ':'
				)
					? loaded.get( file.file )
					: undefined;
				if ( ! restored ) {
					entry.record.omitted.push( file.name );
					return [];
				}
				return [ restored ];
			}
		);
	}
	return JSON.stringify( bucket );
}

export async function restorePickedFiles( scope: string ) {
	let raw: string | null;
	try {
		raw = sessionStorage.getItem( prefix + scope );
	} catch {
		return;
	}
	if ( ! raw?.includes( '"file":' ) ) {
		return;
	}
	const bucket = JSON.parse( raw );
	const refs = (
		Object.values( bucket.records ) as {
			record: { uploads: ( Upload | FileRef )[] };
		}[]
	 )
		.flatMap( ( entry ) => entry.record.uploads )
		.filter(
			( file ): file is FileRef =>
				'file' in file && file.file.startsWith( scope + ':' )
		);
	await Promise.all(
		refs.map( async ( ref ) => {
			if ( loaded.has( ref.file ) ) {
				return;
			}
			const upload = ( await read( ref.file ) )?.uploads[ 0 ];
			if ( upload ) {
				loaded.set( ref.file, upload );
			}
		} )
	);
}

export function releasePickedFiles( uploads: Upload[], scope?: string ) {
	for ( const upload of uploads ) {
		const id =
			( scope ? fileKey( scope, upload ) : undefined ) ??
			Array.from( loaded ).find(
				( [ , file ] ) => file === upload
			)?.[ 0 ];
		if ( id ) {
			try {
				const journal = sessionStorage.getItem(
					prefix + id.split( ':' )[ 0 ]
				);
				if ( journal?.includes( JSON.stringify( id ) ) ) {
					continue;
				}
			} catch {
				continue;
			}
			loaded.delete( id );

			void removeFiles( id ).catch( () => undefined );
		}
	}
}

export async function keepJobFiles(
	jobId: string,
	uploads: Upload[],
	until: number,
	text: string
) {
	if ( uploads.length ) {
		await write( { id: jobId, uploads, expires: until, text } );
	}
}
export const readJobDraft = read;
