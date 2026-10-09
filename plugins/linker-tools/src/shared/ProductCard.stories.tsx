/**
 * The product card in each feedback state; the card keeps its height.
 */

/**
 * External dependencies
 */
import type { Meta, StoryObj } from '@storybook/react-vite';

/**
 * Internal dependencies
 */
import { ProductCard, type CardState } from './ProductCard';

const TEXT: Record< CardState, string > = {
	idle: '',
	pending: 'Adding…',
	added: 'In your solution draft',
	unverified: 'Sent, but the draft does not show it yet. Please check.',
	retry: 'Not added. Try again.',
};

const meta = {
	title: 'Shared/ProductCard',
	component: ProductCard,
	args: {
		id: 'card',
		role: 'Hybrid inverter',
		title: 'GoodWe ESA GW10K-ETA-G20 (10 kW three-phase power module)',
		model: 'Model GW10K-ETA-G20',
		quantity: '1 pc',
		badges: [ { tone: 'ok', text: 'In stock' } ],
		image: {
			src: 'https://de-linker.com/wp-content/uploads/2026/09/GW_ESA_product_front.png',
			alt: '',
		},
	},
	decorators: [
		( Story ) => (
			<div
				className="linker-configurator"
				style={ { maxWidth: '32rem' } }
			>
				<Story />
			</div>
		),
	],
} satisfies Meta< typeof ProductCard >;

export default meta;
type Story = StoryObj< typeof meta >;

export const Idle: Story = {};
export const Pending: Story = {
	args: { status: { state: 'pending', text: TEXT.pending } },
};
export const Added: Story = {
	args: { status: { state: 'added', text: TEXT.added } },
};
export const Unverified: Story = {
	args: { status: { state: 'unverified', text: TEXT.unverified } },
};
export const Retry: Story = {
	args: { status: { state: 'retry', text: TEXT.retry } },
};
