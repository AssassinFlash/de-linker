/**
 * The Genie panel in its open state, EN and DE.
 */

/**
 * External dependencies
 */
import type { Meta, StoryObj } from '@storybook/react-vite';

/**
 * Internal dependencies
 */
import { App } from './App';
import type { GenieConfig } from './config';

const BASE: GenieConfig = {
	locale: 'en',
	pageType: 'category',
	turnUrl: '/wp-json/linker-ai/v1/genie/turn',
	threadUrl: '/wp-json/linker-ai/v1/genie/conversation',
	voteUrl: '/wp-json/linker-ai/v1/genie/turn',
	restUrl: '/wp-json/',
	restNonce: 'storybook',
	disclosure:
		"Hi, I'm Genie, Linker's AI assistant. You're chatting with an AI system.",
	accountUrl: '/my-account/',
	prompts: [
		'Ask Genie',
		'I need a three-phase hybrid inverter for a home with 10 kWp PV.',
	],
};

const meta = {
	title: 'Genie/App',
	component: App,
	args: { config: BASE },
	decorators: [
		( Story ) => (
			<div style={ { maxWidth: '36rem', margin: '2rem auto' } }>
				<Story />
			</div>
		),
	],
} satisfies Meta< typeof App >;

export default meta;
type Story = StoryObj< typeof meta >;

export const English: Story = {};

export const German: Story = {
	args: {
		config: {
			...BASE,
			locale: 'de',
			disclosure:
				'Hallo, ich bin Genie, der KI-Assistent von Linker. Sie chatten mit einem KI-System.',
			prompts: [
				'Genie fragen',
				'Ich brauche einen dreiphasigen Hybridwechselrichter für ein Wohngebäude mit 10 kWp PV.',
			],
		},
	},
};
