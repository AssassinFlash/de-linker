/**
 * One Genie conversation, read by both surfaces (ticket #232): the proxy
 * keeps the thread on the conversation post and names it with the browser's
 * cookie, so the hero and the dock share it. The hero reads on mount for
 * its view, and re-reads before every send so the question is asked
 * against the dock's latest turn. The server also keeps a stale snapshot
 * from dropping that turn: the new user message is appended (#373).
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
	type SentContact,
	type SentInquiryCard,
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
	/** The cards the dock (or an earlier hero turn) already sent (#243/#250). */
	contacts?: SentContact[];
	inquiries?: SentInquiryCard[];
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
	private contactsValue: SentContact[] = [];
	private inquiriesValue: SentInquiryCard[] = [];
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
	 * Reads the conversation the browser already has, once per mount.
	 *
	 * @return The stored thread.
	 */
	async load(): Promise< HeroStoredThread > {
		if ( ! this.loading ) {
			await this.refresh();
		} else {
			await this.loading;
		}
		return this.snapshot();
	}

	/**
	 * Re-reads the shared thread before a send.
	 */
	private async refresh(): Promise< void > {
		this.loading = this.read(
			this.config.threadUrl,
			this.config.nonce
		).then( ( stored ) => {
			this.messagesValue = stored.messages;
			this.turnValue = stored.turn;
			this.contactsValue = stored.contacts ?? [];
			this.inquiriesValue = stored.inquiries ?? [];
		} );
		await this.loading;
	}

	private snapshot(): HeroStoredThread {
		return {
			messages: this.messagesValue,
			turn: this.turnValue,
			contacts: this.contactsValue,
			inquiries: this.inquiriesValue,
		};
	}

	/**
	 * Sends one question on top of the conversation as it stands on the
	 * server now. The thread is appended only after the proxy answered: a
	 * refused turn (a file the proxy rejects, a service error) leaves the
	 * conversation as it was, which is what the field then shows again.
	 *
	 * @param text    The question, file names already named in it.
	 * @param uploads The turn's files, apart from the messages (#236).
	 */
	async ask(
		text: string,
		uploads: Upload[] = []
	): Promise< {
		messages: TurnMessage[];
		answer: Turn;
		contacts?: SentContact[];
		inquiries?: SentInquiryCard[];
	} > {
		// Every send, not only the first: the dock may have written a turn
		// while this view was folded (or both surfaces are open).
		await this.refresh();
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
		return {
			...this.snapshot(),
			answer,
		};
	}
}
