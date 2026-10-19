/**
 * The home hero's conversation state (ticket #232, variant B · unfold in
 * place): untouched, unfolded inside the hero, or folded back to the resting
 * hero with a way back once the hero is out of sight.
 *
 * The state is pure and lives outside React, because the hero's controls —
 * the page's own textarea, send button, capsules, photo, attachment and voice
 * buttons — are part of the LiveCanvas page, not of the conversation React
 * renders into it. The controller binds those controls and feeds events here.
 */

/** The three faces of the hero. */
export type HeroPhase = 'idle' | 'open' | 'closed';

export interface HeroState {
	/** Untouched, unfolded in place, or folded back with the conversation kept. */
	phase: HeroPhase;
	/** Whether the browser's current Genie conversation has any message. */
	hasConversation: boolean;
	/** The hero is entirely above the viewport. */
	scrolledOut: boolean;
	/** The standing dock is open. */
	dockOpen: boolean;
}

export type HeroEvent =
	| { type: 'ask' }
	| { type: 'close' }
	| { type: 'continue' }
	| { type: 'conversation'; has: boolean }
	| { type: 'scroll'; out: boolean }
	| { type: 'dock'; open: boolean };

export const initialHeroState: HeroState = {
	phase: 'idle',
	hasConversation: false,
	scrolledOut: false,
	dockOpen: false,
};

/**
 * Folds one event into the hero's state.
 *
 * @param state The state before the event.
 * @param event What happened.
 */
export function heroReducer( state: HeroState, event: HeroEvent ): HeroState {
	switch ( event.type ) {
		case 'ask':
			return { ...state, phase: 'open' };
		// Closing and handing over to the side panel are the same fold: the
		// hero is restored, the conversation stays on the server.
		case 'close':
		case 'continue':
			return { ...state, phase: 'closed' };
		case 'conversation':
			return { ...state, hasConversation: event.has };
		case 'scroll':
			return { ...state, scrolledOut: event.out };
		case 'dock':
			return { ...state, dockOpen: event.open };
	}
}

/**
 * Whether the page shows the conversation inside the hero.
 *
 * @param state The hero's state.
 */
export function heroExpanded( state: HeroState ): boolean {
	return state.phase === 'open';
}

/**
 * Whether the "Your Genie conversation · continue" entry stands beside the
 * dock button: there is a conversation, the hero is out of sight, and the
 * dock is closed. The conversation may still be unfolded in the hero — the
 * entry is the way back once the hero is scrolled away (the prototype's B
 * rule), and clicking it folds the hero and continues in the dock.
 *
 * @param state The hero's state.
 */
export function pillVisible( state: HeroState ): boolean {
	return state.hasConversation && state.scrolledOut && ! state.dockOpen;
}
