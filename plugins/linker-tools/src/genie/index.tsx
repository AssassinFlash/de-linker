/**
 * WordPress dependencies
 */
import domReady from '@wordpress/dom-ready';

/**
 * Internal dependencies
 */
import { mountApp } from '../shared/mount';
import { App } from './App';

domReady( () => mountApp( 'genie', App ) );
