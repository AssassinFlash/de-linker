// @vitest-environment jsdom

/**
 * The turn wording both surfaces share (ticket #232 review round 1, item 4).
 */

/**
 * External dependencies
 */
import { expect, test } from 'vitest';

/**
 * Internal dependencies
 */
import { TurnError } from '../api/turn';
import type { Upload } from '../attachments/prepare';
import {
	attachmentRefusalReason,
	buildQuestion,
	typeModelPrompt,
} from './conversation';

const PDF: Upload = {
	name: 'datasheet.pdf',
	type: 'application/pdf',
	data: 'AA==',
};

test( 'a typed question is the message', () => {
	expect( buildQuestion( '  saj  ', [] ) ).toBe( 'saj' );
} );

test( 'each file names itself on its own line, after the question', () => {
	expect( buildQuestion( 'saj', [ PDF ] ) ).toBe(
		'saj\nAttached: datasheet.pdf'
	);
} );

test( 'files alone are a question', () => {
	expect( buildQuestion( '', [ PDF ] ) ).toBe( 'Attached: datasheet.pdf' );
} );

test( 'nothing typed and no files is no question', () => {
	expect( buildQuestion( '   ', [] ) ).toBe( '' );
} );

test( 'the proxy attachment refusal keeps its reason code', () => {
	expect(
		attachmentRefusalReason(
			new TurnError( 413, 'linker_genie_attachment_type' )
		)
	).toBe( 'type' );
	expect(
		attachmentRefusalReason(
			new TurnError( 429, 'linker_genie_attachment_throttled' )
		)
	).toBe( 'throttled' );
} );

test( 'a failure that is not an attachment refusal has no reason', () => {
	expect( attachmentRefusalReason( new Error( 'turn 502' ) ) ).toBe( '' );
	expect(
		attachmentRefusalReason( new TurnError( 502, 'linker_genie_upstream' ) )
	).toBe( '' );
} );

test( 'the manual-model exit opens with the same words on both surfaces', () => {
	expect( typeModelPrompt() ).toBe( 'My device is the ' );
} );
