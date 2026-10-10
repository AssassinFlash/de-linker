/**
 * The configurator's screens and states on the engine's recorded answers.
 * Each story types the inputs behind the answer it shows (the requests are
 * listed in services/engine/tests/test_ui_fixtures.py).
 */

/**
 * External dependencies
 */
import type { Meta, StoryObj } from '@storybook/react-vite';
import { expect, userEvent, within } from 'storybook/test';

/**
 * Internal dependencies
 */
import {
	fakeEngine,
	fakeStore,
	fixtures,
} from '../../tests/configurator/fakes';
import { App, type AppProps } from './App';
import type { Locale } from './types';

type Args = {
	outcome: 'solution' | 'none' | 'unavailable' | 'never';
	commercial: 'sized' | 'indicative';
	segment: AppProps[ 'initialSegment' ];
	draft: 'added' | 'unverified' | 'retry';
};

function Harness( {
	outcome,
	commercial,
	segment,
	draft,
	locale,
}: Args & { locale: Locale } ) {
	const { engine } = fakeEngine( {
		locale,
		residential: outcome,
		commercial,
	} );
	const { store } = fakeStore( draft );
	return (
		<App
			config={ {
				engineUrl: '',
				restUrl: '/wp-json/',
				restNonce: '',
				locale,
				openRoof: false,
			} }
			engine={ engine }
			store={ store }
			initialSegment={ segment }
		/>
	);
}

const meta = {
	title: 'Configurator/App',
	args: {
		outcome: 'solution',
		commercial: 'indicative',
		segment: 'residential',
		draft: 'added',
	},
	render: ( args, context ) => (
		<Harness
			{ ...args }
			locale={ context.globals.locale === 'de' ? 'de' : 'en' }
		/>
	),
} satisfies Meta< Args >;

export default meta;
type Story = StoryObj< typeof meta >;

const GERMAN: Record< string, string > = {
	plz: 'Postleitzahl des Standorts',
	annual: 'Jahresverbrauch des Haushalts',
	kwp: 'PV-Leistung',
	single: 'Einphasig',
	backup: 'Notstromversorgung',
	submit: 'System berechnen',
};
const ENGLISH: Record< string, string > = {
	plz: 'Postcode of the site',
	annual: 'Annual household consumption',
	kwp: 'PV array',
	single: 'Single-phase',
	backup: 'Backup supply',
	submit: 'Calculate system',
};

interface Household {
	annual: string;
	kwp: string;
	singlePhase?: boolean;
	backup?: 'needed';
}

// residential-*.json and residential-none-*.json answer these households.
const PROPOSED: Household = { annual: '5000', kwp: '10' };
const NO_CANDIDATE: Household = {
	annual: '6000',
	kwp: '12',
	singlePhase: true,
	backup: 'needed',
};

async function fillAndCalculate(
	canvasElement: HTMLElement,
	locale: string,
	household: Household = PROPOSED
) {
	const canvas = within( canvasElement );
	const text = locale === 'de' ? GERMAN : ENGLISH;
	await userEvent.type(
		canvas.getByLabelText( new RegExp( text.plz ) ),
		'80538'
	);
	await userEvent.type(
		canvas.getByLabelText( new RegExp( text.annual ) ),
		household.annual
	);
	await userEvent.type(
		canvas.getByLabelText( new RegExp( text.kwp ) ),
		household.kwp
	);
	if ( household.singlePhase ) {
		await userEvent.click( canvas.getByLabelText( text.single ) );
	}
	if ( household.backup ) {
		await userEvent.selectOptions(
			canvas.getByLabelText( text.backup ),
			household.backup
		);
	}
	await userEvent.click(
		canvas.getByRole( 'button', { name: text.submit } )
	);
}

/** Screen 1: the inputs before anything is calculated. */
export const Inputs: Story = {};

/** Screen 2 and 3: the proposed system and, below it, the design report. */
export const Solution: Story = {
	play: async ( { canvasElement, globals } ) => {
		await fillAndCalculate( canvasElement, globals.locale );
		await expect(
			await within( canvasElement ).findAllByRole( 'article' )
		).not.toHaveLength( 0 );
	},
};

/** The solution after "Add all to solution draft". */
export const AddedToDraft: Story = {
	play: async ( context ) => {
		await Solution.play!( context );
		const canvas = within( context.canvasElement );
		const name =
			context.globals.locale === 'de'
				? 'Alles zum Lösungsentwurf hinzufügen'
				: 'Add all to solution draft';
		await userEvent.click( canvas.getByRole( 'button', { name } ) );
	},
};

export const DraftNotConfirmed: Story = {
	...AddedToDraft,
	args: { draft: 'unverified' },
};

export const Computing: Story = {
	args: { outcome: 'never' },
	play: async ( { canvasElement, globals } ) =>
		fillAndCalculate( canvasElement, globals.locale ),
};

export const NoCandidate: Story = {
	args: { outcome: 'none' },
	play: async ( { canvasElement, globals } ) =>
		fillAndCalculate( canvasElement, globals.locale, NO_CANDIDATE ),
};

export const Unavailable: Story = {
	args: { outcome: 'unavailable' },
	play: async ( { canvasElement, globals } ) =>
		fillAndCalculate( canvasElement, globals.locale ),
};

export const CommercialInputs: Story = { args: { segment: 'commercial' } };

// commercial-sized-*.json and commercial-indicative-*.json answer these.
async function commercialRun(
	canvasElement: HTMLElement,
	locale: string,
	path: 'sized' | 'indicative'
) {
	const canvas = within( canvasElement );
	const de = locale === 'de';
	const type = ( label: RegExp, value: string ) =>
		userEvent.type( canvas.getByLabelText( label ), value );
	await type(
		de ? /Postleitzahl des Standorts/ : /Postcode of the site/,
		'80538'
	);
	await type(
		de ? /Netzanschlussleistung/ : /Grid connection capacity/,
		'250'
	);
	await type( de ? /^Jahresverbrauch/ : /^Annual consumption/, '380000' );
	await type( de ? /Zielhöchstlast/ : /Target peak/, '150' );
	if ( path === 'sized' ) {
		await userEvent.upload(
			canvas.getByLabelText(
				de ? /15-Minuten-Lastgang/ : /15-minute load profile/
			),
			new File( [ fixtures.loadProfile ], 'load-profile-15min.csv', {
				type: 'text/csv',
			} )
		);
	} else {
		await type(
			de ? /Jahreshöchstlast laut Rechnung/ : /Annual peak from the bill/,
			'200'
		);
		await userEvent.click(
			canvas.getByLabelText(
				de ? 'Eigenverbrauch von PV-Strom' : 'Self-consumption of PV'
			)
		);
		await type(
			de
				? /PV-Anlage, bestehend oder geplant/
				: /PV array, existing or planned/,
			'120'
		);
	}
	await userEvent.click(
		canvas.getByRole( 'button', {
			name: de ? 'Speicher berechnen' : 'Calculate storage',
		} )
	);
}

export const CommercialIndicative: Story = {
	args: { segment: 'commercial', commercial: 'indicative' },
	play: async ( { canvasElement, globals } ) =>
		commercialRun( canvasElement, globals.locale, 'indicative' ),
};

export const CommercialSized: Story = {
	args: { segment: 'commercial', commercial: 'sized' },
	play: async ( { canvasElement, globals } ) =>
		commercialRun( canvasElement, globals.locale, 'sized' ),
};

export const Utility: Story = { args: { segment: 'utility' } };
