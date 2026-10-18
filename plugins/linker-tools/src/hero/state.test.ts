// @vitest-environment jsdom

/**
 * The home hero's conversation state (ticket #232): untouched, unfolded in
 * the hero, or folded back to the resting hero with a way back.
 */

/**
 * External dependencies
 */
import { expect, test } from 'vitest';

/**
 * Internal dependencies
 */
import {
	heroExpanded,
	heroReducer,
	initialHeroState,
	pillVisible,
	type HeroEvent,
	type HeroState,
} from './state';

function run( events: HeroEvent[], from: HeroState = initialHeroState ) {
	return events.reduce( heroReducer, from );
}

test( 'the hero starts untouched: not unfolded, no way back', () => {
	expect( heroExpanded( initialHeroState ) ).toBe( false );
	expect( pillVisible( initialHeroState ) ).toBe( false );
} );

test( 'an ask unfolds the conversation in place', () => {
	const state = run( [ { type: 'ask' } ] );
	expect( state.phase ).toBe( 'open' );
	expect( heroExpanded( state ) ).toBe( true );
} );

test( 'closing the conversation restores the hero and keeps the conversation', () => {
	const state = run( [
		{ type: 'ask' },
		{ type: 'conversation', has: true },
		{ type: 'close' },
	] );
	expect( state.phase ).toBe( 'closed' );
	expect( state.hasConversation ).toBe( true );
	expect( heroExpanded( state ) ).toBe( false );
} );

test( 'a conversation that exists counts even before the hero asks', () => {
	const state = run( [ { type: 'conversation', has: true } ] );
	expect( state.hasConversation ).toBe( true );
} );

test( 'the way back appears only once the hero is out of sight', () => {
	const inSight = run( [
		{ type: 'conversation', has: true },
		{ type: 'close' },
		{ type: 'scroll', out: false },
	] );
	expect( pillVisible( inSight ) ).toBe( false );

	const outOfSight = heroReducer( inSight, { type: 'scroll', out: true } );
	expect( pillVisible( outOfSight ) ).toBe( true );
} );

test( 'no conversation, no way back', () => {
	const state = run( [
		{ type: 'scroll', out: true },
		{ type: 'conversation', has: false },
	] );
	expect( pillVisible( state ) ).toBe( false );
} );

test( 'the way back stays beside the dock while the hero is out of sight, and steps aside for the dock', () => {
	const folded = run( [
		{ type: 'conversation', has: true },
		{ type: 'scroll', out: true },
		{ type: 'close' },
	] );
	expect( pillVisible( folded ) ).toBe( true );

	// Scrolling away from an unfolded conversation still leaves the way back
	// (the prototype's B rule); clicking it folds the hero first.
	expect( pillVisible( heroReducer( folded, { type: 'ask' } ) ) ).toBe(
		true
	);

	const docked = heroReducer( folded, { type: 'dock', open: true } );
	expect( pillVisible( docked ) ).toBe( false );
	expect(
		pillVisible( heroReducer( docked, { type: 'dock', open: false } ) )
	).toBe( true );
} );

test( 'continuing in the side panel folds the hero and leaves the conversation', () => {
	const state = run( [
		{ type: 'ask' },
		{ type: 'conversation', has: true },
		{ type: 'continue' },
		{ type: 'scroll', out: true },
	] );
	expect( state.phase ).toBe( 'closed' );
	expect( heroExpanded( state ) ).toBe( false );
	expect( pillVisible( state ) ).toBe( true );
} );
