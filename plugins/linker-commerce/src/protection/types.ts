export type ProtectionState = 'checking' | 'ready' | 'failed' | 'expired';

export interface ProtectionConfig {
	api: string;
	nonce: string;
	mode: string;
	businessVerification?: 'required' | 'optional';
	language: 'en' | 'de';
}

export interface TurnstileOptions {
	sitekey: string;
	action: string;
	language: 'en' | 'de';
	appearance: 'interaction-only';
	callback: ( token: string ) => void;
	'error-callback': () => void;
	'expired-callback': () => void;
	'timeout-callback': () => void;
}

export interface TurnstileApi {
	render: ( container: HTMLElement, options: TurnstileOptions ) => string;
	remove: ( id: string ) => void;
}

export interface PublicProtection {
	ready?: ( action: string, container: HTMLElement ) => string;
	warm: ( action: string, container: HTMLElement ) => Promise< string >;
	proof: ( action: string, container: HTMLElement ) => Promise< string >;
	reset: ( action: string ) => void;
}

declare global {
	interface Window {
		linkerPublicProtectionConfig?: ProtectionConfig;
		linkerPublicProtection?: PublicProtection;
		turnstile?: TurnstileApi;
	}
}
