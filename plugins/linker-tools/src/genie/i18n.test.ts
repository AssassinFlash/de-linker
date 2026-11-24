// @vitest-environment node

/**
 * External dependencies
 */
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { expect, test } from 'vitest';

/**
 * Internal dependencies
 */
import germanGenie from '../../languages/linker-tools-de_DE_formal-c2be3a742ec1f5e619cd2beb8d234138.json';

// A string literal in single or double quotes; prettier picks double quotes
// only for a text that contains an apostrophe.
const STRING = String.raw`(?:'((?:[^'\\]|\\.)*)'|"((?:[^"\\]|\\.)*)")`;
const SINGLE = new RegExp(
	String.raw`\b__\(\s*${ STRING }\s*,\s*'linker-tools'`,
	'g'
);
const PLURAL = new RegExp(
	String.raw`\b_n\(\s*${ STRING }\s*,\s*${ STRING }\s*,`,
	'g'
);
const CONTEXT = new RegExp(
	String.raw`\b_x\(\s*${ STRING }\s*,\s*${ STRING }\s*,\s*'linker-tools'`,
	'g'
);

function literal( match: RegExpMatchArray ): string {
	return ( match[ 1 ] ?? match[ 2 ] ).replace( /\\(['"])/g, '$1' );
}

function sources( dir: string ): string[] {
	if ( statSync( dir ).isFile() ) {
		return [ dir ];
	}
	return readdirSync( dir ).flatMap( ( name ) => {
		const path = join( dir, name );
		if ( statSync( path ).isDirectory() ) {
			return sources( path );
		}
		return /\.tsx?$/.test( name ) && ! /\.(test|stories)\./.test( name )
			? [ path ]
			: [];
	} );
}

function used( dirs: string[] ): Map< string, number > {
	const out = new Map< string, number >();
	for ( const file of dirs.flatMap( sources ) ) {
		const text = readFileSync( file, 'utf8' );
		for ( const match of text.matchAll( SINGLE ) ) {
			out.set( literal( match ), 1 );
		}
		for ( const match of text.matchAll( PLURAL ) ) {
			out.set( literal( match ), 2 );
		}
		for ( const match of text.matchAll( CONTEXT ) ) {
			out.set(
				`${ match[ 3 ] ?? match[ 4 ] }\u0004${ literal( match ) }`,
				1
			);
		}
	}
	return out;
}

const genieMessages = germanGenie.locale_data.messages as Record<
	string,
	unknown
>;

test( 'every genie text has a German translation', () => {
	const missing = [
		...used( [ 'src/genie', 'src/shared', 'src/protection' ] ).keys(),
	].filter( ( id ) => ! ( id in genieMessages ) );
	expect( missing ).toEqual( [] );
} );

test( 'the genie translation file holds only texts the code uses', () => {
	const ids = used( [ 'src/genie', 'src/shared', 'src/protection' ] );
	const unused = Object.keys( genieMessages ).filter(
		( id ) => id && ! ids.has( id )
	);
	expect( unused ).toEqual( [] );
} );

test( 'genie German keeps the naming and the formal address', () => {
	const text = JSON.stringify( genieMessages );
	expect( text ).not.toMatch( /\b(du|dein|deine|dich|dir)\b/i );
	expect( genieMessages[ "Genie – Linker's AI assistant" ] ).toEqual( [
		'Genie – der KI-Assistent von Linker',
	] );
} );
