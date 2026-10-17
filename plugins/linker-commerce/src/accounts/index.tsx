/**
 * WordPress dependencies
 */
import { createRoot } from '@wordpress/element';

/**
 * Internal dependencies
 */
import { AccountsApp } from './AccountsApp';
import { AccountsApi } from './api';
import './style.css';

const root = document.getElementById( 'linker-accounts-app' );
if ( root?.dataset.api && root.dataset.nonce ) {
	createRoot( root ).render(
		<AccountsApp
			api={ new AccountsApi( root.dataset.api, root.dataset.nonce ) }
			focusId={ Number( root.dataset.focus || 0 ) }
		/>
	);
}
