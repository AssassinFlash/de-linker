export type FormAction =
	'contact' | 'inquiry' | 'registration' | 'genie_contact' | 'genie_inquiry';

export interface WidgetConfig {
	siteKey: string;
	language: 'en' | 'de';
}

export interface TurnstileOptions {
	sitekey: string;
	action: FormAction;
	language: 'en' | 'de';
	size: 'flexible' | 'compact';
	theme: 'light';
	retry: 'auto';
	'refresh-expired': 'auto';
	callback: ( token: string ) => void;
	'error-callback': ( code: string ) => boolean;
	'expired-callback': () => void;
}

export interface TurnstileApi {
	render: ( container: HTMLElement, options: TurnstileOptions ) => string;
	reset: ( id: string ) => void;
	remove: ( id: string ) => void;
}

export interface Widgets {
	mount: (
		container: HTMLElement,
		action: FormAction,
		onToken?: ( token: string ) => void
	) => () => void;
	refresh: ( container: HTMLElement ) => void;
}

declare global {
	interface Window {
		linkerTurnstileConfig?: WidgetConfig;
		linkerTurnstile?: Widgets;
		turnstile?: TurnstileApi;
	}
}
