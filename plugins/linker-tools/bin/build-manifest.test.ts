// @vitest-environment node

/**
 * External dependencies
 */
import { execFileSync, spawnSync } from 'node:child_process';
import {
	appendFileSync,
	copyFileSync,
	mkdirSync,
	mkdtempSync,
	rmSync,
	unlinkSync,
	writeFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { afterEach, beforeEach, expect, test } from 'vitest';

const script = fileURLToPath(
	new URL( './build-manifest.mjs', import.meta.url )
);

// A package laid out like plugins/linker-tools, in its own git repository.
const fixture: Record< string, string > = {
	'.gitignore': '.DS_Store\n',
	'package.json': '{}\n',
	'package-lock.json': '{}\n',
	'webpack.config.js': 'module.exports = {};\n',
	'src/app/index.tsx': 'export {};\n',
	'src/app/index.test.tsx': 'export {};\n',
	'src/app/App.stories.tsx': 'export {};\n',
	'build/app.js': 'console.log( 1 );\n',
	'build/app.asset.php': '<?php return array();\n',
};

let pkg: string;

function file( path: string ): string {
	return join( pkg, path );
}

function run( command: 'write' | 'check' ) {
	return spawnSync(
		process.execPath,
		[ file( 'bin/build-manifest.mjs' ), command ],
		{ encoding: 'utf8' }
	);
}

beforeEach( () => {
	pkg = mkdtempSync( join( tmpdir(), 'build-manifest-' ) );
	for ( const [ path, content ] of Object.entries( fixture ) ) {
		mkdirSync( dirname( file( path ) ), { recursive: true } );
		writeFileSync( file( path ), content );
	}
	mkdirSync( file( 'bin' ) );
	copyFileSync( script, file( 'bin/build-manifest.mjs' ) );
	execFileSync( 'git', [ 'init', '--quiet' ], { cwd: pkg } );
	const written = run( 'write' );
	if ( written.status !== 0 ) {
		throw new Error( written.stderr );
	}
} );

afterEach( () => {
	rmSync( pkg, { recursive: true, force: true } );
} );

test( 'passes while nothing changed since the last write', () => {
	expect( run( 'check' ) ).toMatchObject( {
		status: 0,
		stdout: 'build/ matches its sources.\n',
	} );
} );

test.each( [ 'src/app/index.tsx', 'package-lock.json', 'build/app.js' ] )(
	'fails and names %s when it changed',
	( path ) => {
		appendFileSync( file( path ), '\n' );

		const result = run( 'check' );

		expect( result.status ).toBe( 1 );
		expect( result.stderr ).toContain( `changed: ${ path }\n` );
	}
);

test( 'fails and names a source file added without a rebuild', () => {
	writeFileSync( file( 'src/app/extra.ts' ), 'export {};\n' );

	const result = run( 'check' );

	expect( result.status ).toBe( 1 );
	expect( result.stderr ).toContain( 'added: src/app/extra.ts\n' );
} );

test( 'fails and names a source file deleted without a rebuild', () => {
	unlinkSync( file( 'src/app/index.tsx' ) );

	const result = run( 'check' );

	expect( result.status ).toBe( 1 );
	expect( result.stderr ).toContain( 'removed: src/app/index.tsx\n' );
} );

test( 'ignores tests, stories and files git ignores', () => {
	appendFileSync( file( 'src/app/index.test.tsx' ), '\n' );
	appendFileSync( file( 'src/app/App.stories.tsx' ), '\n' );
	writeFileSync( file( 'src/.DS_Store' ), '' );
	writeFileSync( file( 'build/.DS_Store' ), '' );

	expect( run( 'check' ).status ).toBe( 0 );
} );

test( 'fails without a manifest', () => {
	unlinkSync( file( 'build/manifest.json' ) );

	const result = run( 'check' );

	expect( result.status ).toBe( 1 );
	expect( result.stderr ).toContain( 'build/manifest.json is unreadable' );
} );
