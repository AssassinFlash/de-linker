/**
 * WordPress dependencies
 */
import domReady from '@wordpress/dom-ready';

/**
 * Internal dependencies
 */
import { App } from './App';
import { mountApp } from './mount';

domReady( () => mountApp( 'shared', App ) );
