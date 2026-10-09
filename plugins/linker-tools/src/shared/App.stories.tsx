/**
 * External dependencies
 */
import type { Meta, StoryObj } from '@storybook/react-vite';

/**
 * Internal dependencies
 */
import { App } from './App';

const meta = {
	title: 'Shared/App',
	component: App,
} satisfies Meta< typeof App >;

export default meta;

export const Default: StoryObj< typeof meta > = {};
