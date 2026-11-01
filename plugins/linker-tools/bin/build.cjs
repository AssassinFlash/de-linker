// Run the installed wp-scripts CLI. Its webpack child also needs the plugin's
// local loader paths when another worktree owns the physical node_modules.
const path = require( 'node:path' );
const metadata = require.resolve( '@wordpress/scripts/package.json' );
process.env.NODE_OPTIONS = [ process.env.NODE_OPTIONS, '--preserve-symlinks' ]
	.filter( Boolean )
	.join( ' ' );
process.argv.splice( 2, 0, 'build' );
require(
	path.resolve(
		path.dirname( metadata ),
		require( metadata ).bin[ 'wp-scripts' ]
	)
);
