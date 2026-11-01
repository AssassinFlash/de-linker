export type ProtectionState =
	'checking' | 'interactive' | 'retrying' | 'ready' | 'failed' | 'expired';

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
	appearance: 'always';
	size: 'flexible' | 'compact';
	retry: 'auto';
	'retry-interval': number;
	'refresh-timeout': 'manual';
	callback: ( token: string ) => void;
	'error-callback': ( code?: string ) => void;
	'before-interactive-callback': () => void;
	'unsupported-callback': () => void;
	'expired-callback': () => void;
	'timeout-callback': () => void;
}

export interface TurnstileApi {
	render: ( container: HTMLElement, options: TurnstileOptions ) => string;
	reset: ( id: string ) => void;
	remove: ( id: string ) => void;
}

export interface PublicProtection {
	ready?: ( action: string, container: HTMLElement ) => string;
	warm: ( action: string, container: HTMLElement ) => Promise< string >;
	proof: ( action: string, container: HTMLElement ) => Promise< string >;
	complete?: ( action: string, proof: string ) => boolean;
	cancel?: ( action: string, container: HTMLElement ) => boolean;
	reset: ( action: string ) => void;
}

declare global {
	interface Window {
		linkerPublicProtectionConfig?: ProtectionConfig;
		linkerPublicProtection?: PublicProtection;
		turnstile?: TurnstileApi;
	}
}
