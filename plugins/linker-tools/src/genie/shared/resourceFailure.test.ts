import { expect, test } from 'vitest';
import { TurnError } from '../api/turn';
import {
	isVerificationCancellation,
	resourceRefusalReason,
} from './resourceFailure';
import { settleTurnFailure } from './failure';

test( 'current-source revocation is distinct from an authority outage and retains the question', () => {
	const changed = new TurnError( 409, 'linker_genie_publication_changed' );
	const unavailable = new TurnError(
		503,
		'linker_genie_publication_unavailable'
	);
	expect( resourceRefusalReason( changed ) ).toBe(
		'The product information changed while Genie was answering. Your message is still here.'
	);
	expect( resourceRefusalReason( unavailable ) ).toBe(
		'Genie is temporarily unavailable. Your message is still here. You can send an inquiry to our team.'
	);
	const settled = settleTurnFailure( changed, [], {
		text: 'My product question',
		question: 'My product question',
		uploads: [],
		omitted: [],
	} );
	expect( settled ).toMatchObject( {
		action: 'resource',
		field: 'My product question',
	} );
} );

test( 'verification failure names the check and preserves the draft without blaming a model outage', () => {
	const reason =
		'Verification could not be completed. No request has been sent in this attempt. Please try again.';
	for ( const error of [
		new Error( 'verification_widget_110100' ),
		new Error( 'verification_timeout' ),
		new TurnError( 400, 'linker_verification_expired' ),
	] ) {
		expect( resourceRefusalReason( error ) ).toBe( reason );
		expect(
			settleTurnFailure( error, [], {
				text: 'My project question',
				question: 'My project question',
				uploads: [],
				omitted: [],
			} )
		).toMatchObject( {
			action: 'resource',
			reason,
			field: 'My project question',
		} );
	}
} );

test( 'a withdrawal is neutral, and only a real verification failure is explained', () => {
	// Closing the surface, a conversation switch or a lost owner aborts this
	// attempt before anything is sent. Reopening then owes the customer their
	// question, not a report of a failure that never happened.
	expect(
		isVerificationCancellation( new Error( 'verification_cancelled' ) )
	).toBe( true );
	expect(
		resourceRefusalReason( new Error( 'verification_cancelled' ) )
	).toBeNull();
	expect(
		isVerificationCancellation( new Error( 'verification_timeout' ) )
	).toBe( false );
	expect(
		resourceRefusalReason( new Error( 'verification_timeout' ) )
	).not.toBeNull();
} );
