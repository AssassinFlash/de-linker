import { expect, test } from 'vitest';
import { TurnError } from '../api/turn';
import { resourceRefusalReason } from './resourceFailure';
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
