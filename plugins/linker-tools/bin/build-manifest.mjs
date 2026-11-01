/**
 * Records which sources the committed build/ was made from, and checks it.
 *
 *     node bin/build-manifest.mjs write   last step of `npm run build`
 *     node bin/build-manifest.mjs check   fail if a source or a built file
 *                                         changed since the last write
 *
 * Sources are the files under src/ except tests and stories, plus the files
 * that steer the build. The manifest keeps one SHA-256 per file, so a failed
 * check names what changed.
 */
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

// A sibling plugin can use the same committed-build gate with an explicit root.
const root = process.argv[ 3 ]
	? resolve( process.argv[ 3 ] )
	: fileURLToPath( new URL( '..', import.meta.url ) );
const isTools =
	JSON.parse( readFileSync( join( root, 'package.json' ), 'utf8' ) ).name ===
	'linker-tools';
const manifestPath = 'build/manifest.json';
const buildInputs = [
	'package.json',
	'package-lock.json',
	'webpack.config.js',
	...( isTools ? [ 'project-input-contracts.json', 'bin/build.cjs' ] : [] ),
];
const notBuilt = /\.(test|stories)\.[jt]sx?$/;

// Files under `dir` that git tracks or would track. Ignored files, such as the
// .DS_Store that Finder drops, never reach the repository, so they don't count.
function listFiles( dir ) {
	return execFileSync(
		'git',
		[ 'ls-files', '-z', '--cached', '--others', '--exclude-standard', dir ],
		{ cwd: root, encoding: 'utf8' }
	)
		.split( '\0' )
		.filter( ( file ) => file !== '' && existsSync( join( root, file ) ) );
}

function hashFiles( files ) {
	return Object.fromEntries(
		[ ...files ].sort().map( ( file ) => [
			file,
			createHash( 'sha256' )
				.update( readFileSync( join( root, file ) ) )
				.digest( 'hex' ),
		] )
	);
}

function snapshot() {
	if ( isTools ) {
		const contracts = JSON.parse(
			readFileSync( join( root, 'project-input-contracts.json' ), 'utf8' )
		);
		const plannerDirectory = join( root, 'build/planner' );
		const planner = JSON.parse(
			readFileSync(
				join( plannerDirectory, 'source-manifest.json' ),
				'utf8'
			)
		);
		const vite = JSON.parse(
			readFileSync(
				join( plannerDirectory, 'vite-manifest.json' ),
				'utf8'
			)
		);
		const entry = vite?.[ 'src/main.tsx' ]?.file;
		if (
			typeof entry !== 'string' ||
			! /^assets\/[a-zA-Z0-9_.-]+\.js$/.test( entry ) ||
			! existsSync( join( plannerDirectory, entry ) )
		) {
			throw new Error( 'Planner build entry is missing or invalid' );
		}
		if (
			JSON.stringify( planner.project_input_contracts ) !==
			JSON.stringify( contracts.project_input_contracts )
		) {
			throw new Error( 'Planner build and Tools input contracts differ' );
		}
	}
	return {
		sources: hashFiles( [
			...buildInputs,
			...listFiles( 'src' ).filter( ( file ) => ! notBuilt.test( file ) ),
		] ),
		build: hashFiles(
			listFiles( 'build' ).filter( ( file ) => file !== manifestPath )
		),
	};
}

function differences( recorded = {}, current ) {
	const files = new Set( [
		...Object.keys( recorded ),
		...Object.keys( current ),
	] );
	return [ ...files ]
		.sort()
		.filter( ( file ) => recorded[ file ] !== current[ file ] )
		.map( ( file ) => {
			if ( ! ( file in current ) ) {
				return `removed: ${ file }`;
			}
			return file in recorded ? `changed: ${ file }` : `added: ${ file }`;
		} );
}

function check() {
	let recorded;
	try {
		recorded = JSON.parse(
			readFileSync( join( root, manifestPath ), 'utf8' )
		);
	} catch ( error ) {
		return [ `${ manifestPath } is unreadable: ${ error.message }` ];
	}
	const current = snapshot();
	return [
		...differences( recorded.sources, current.sources ),
		...differences( recorded.build, current.build ),
	];
}

const command = process.argv[ 2 ];

if ( command === 'write' ) {
	writeFileSync(
		join( root, manifestPath ),
		JSON.stringify( snapshot(), null, '\t' ) + '\n'
	);
} else if ( command === 'check' ) {
	const problems = check();
	if ( problems.length > 0 ) {
		process.stderr.write(
			'build/ does not match its sources; run `just build` and commit build/.\n' +
				problems.map( ( problem ) => `  ${ problem }\n` ).join( '' )
		);
		process.exit( 1 );
	}
	process.stdout.write( 'build/ matches its sources.\n' );
} else {
	process.stderr.write( 'Usage: node bin/build-manifest.mjs write|check\n' );
	process.exit( 2 );
}
