/**
 * The roof step on the Bavarian aerial image around PLZ 80538 (München); a
 * click asks the engine, here answered with its recorded LoD2 result for
 * Triftstraße 5.
 */

/**
 * External dependencies
 */
import type { Meta, StoryObj } from '@storybook/react-vite';

/**
 * Internal dependencies
 */
import { fakeEngine } from '../../../tests/configurator/fakes';
import '../configurator.css';
import { RoofStep } from './RoofStep';

const meta = {
	title: 'Configurator/Roof step',
	render: ( _args, context ) => {
		const locale = context.globals.locale === 'de' ? 'de' : 'en';
		const { engine } = fakeEngine( { locale } );
		return (
			<div className="linker-configurator" lang={ locale }>
				<RoofStep
					plz="80538"
					locale={ locale }
					engine={ engine }
					onApply={ () => undefined }
					onClose={ () => undefined }
				/>
			</div>
		);
	},
} satisfies Meta;

export default meta;

export const Munich: StoryObj = {};
