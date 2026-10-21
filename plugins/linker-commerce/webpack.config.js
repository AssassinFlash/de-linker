const config = require( '@wordpress/scripts/config/webpack.config' );
module.exports = {
	...config,
	entry: {
		accounts: './src/accounts/index.tsx',
		protection: './src/protection/index.ts',
	},
};
