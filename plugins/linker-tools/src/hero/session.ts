/**
 * One Genie conversation, read by both surfaces (ticket #232): the proxy
 * keeps the thread on the conversation post and names it with the browser's
 * cookie, so the hero and the dock share it as long as each reads before it
 * writes. The dock does that on mount; the hero reads when it unfolds, then
 * sends the whole thread back with its next question. Sending only the hero's
 * own messages would replace the dock's history (Proxy::turn records the
 * request's messages), so the read comes first.
 */

/**
 * Internal dependencies
 */
import type { Locale } from '../configurator/types';
import {
	assistantMessage,
	readThread,
	sendTurn,
	type PageContext,
	type Turn,
	type TurnMessage,
} from '../genie/api/turn';
import type { Upload } from '../genie/attachments/prepare';

/** What the hero's mount point gives the session (config.ts). */
export interface HeroSessionConfig {
	turnUrl: string;
	threadUrl: string;
	nonce: string;
	locale: Locale;
	page: PageContext;
}

/** The stored thread, in the shapes the rest of the app uses. */
export interface HeroStoredThread {
	messages: TurnMessage[];
	turn: Turn | null;
}

/** The one read the hero needs; a test passes the proxy's double. */
export type HeroReadThread = (
	url: string,
	nonce: string
) => Promise< HeroStoredThread >;

/** The one send the hero needs; the same proxy call the dock makes. */
export type HeroSendTurn = typeof sendTurn;

export class HeroSession {
	private messagesValue: TurnMessage[] = [];
	private turnValue: Turn | null = null;
	private loading: Promise< void > | null = null;

	/**
	 * @param config The mount's routes, nonce, language and page context.
	 * @param read   The stored-thread reader (readThread).
	 * @param send   The turn sender (sendTurn).
	 */
	constructor(
		private readonly config: HeroSessionConfig,
		private readonly read: HeroReadThread = readThread,
		private readonly send: HeroSendTurn = sendTurn
	) {}

	/** The thread as last read or answered. */
	get messages(): TurnMessage[] {
		return this.messagesValue;
	}

	/** The last answer's blocks, when there is one. */
	get turn(): Turn | null {
		return this.turnValue;
	}

	/**
	 * Reads the conversation the browser already has, once.
	 *
	 * @return The stored thread.
	 */
	async load(): Promise< HeroStoredThread > {
		if ( ! this.loading ) {
			this.loading = this.read(
				this.config.threadUrl,
				this.config.nonce
			).then( ( stored ) => {
				this.messagesValue = stored.messages;
				this.turnValue = stored.turn;
			} );
		}
		await this.loading;
		return {
			messages: this.messagesValue,
			turn: this.turnValue,
		};
	}

	/**
	 * Sends one question on top of the stored conversation.
	 *
	 * The thread is appended only after the proxy answered: a refused turn
	 * (a file the proxy rejects, a service error) leaves the conversation as
	 * it was, which is what the field then shows again.
	 *
	 * @param text    The question, file names already named in it.
	 * @param uploads The turn's files, apart from the messages (#236).
	 */
	async ask(
		text: string,
		uploads: Upload[] = []
	): Promise< { messages: TurnMessage[]; answer: Turn } > {
		await this.load();
		const next: TurnMessage[] = [
			...this.messagesValue,
			{ role: 'user', content: text },
		];
		const answer = await this.send(
			this.config.turnUrl,
			this.config.nonce,
			this.config.locale,
			next,
			this.config.page,
			uploads
		);
		this.messagesValue = next.concat( assistantMessage( answer ) );
		this.turnValue = answer;
		return { messages: this.messagesValue, answer };
	}
}
