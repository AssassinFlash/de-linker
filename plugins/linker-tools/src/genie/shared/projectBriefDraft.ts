/** Installer desktop project-brief staging and same-tab recovery. */
import type { GenieConfig } from '../config';
import { TAB_KEY } from './nativeScope';

export const PROJECT_BRIEF_KEY = 'linker-project-brief-draft';
export const MAX_PROJECT_BRIEF_LENGTH = 4096;
export const UNSTAGED_BRIEF_ID = '0'.repeat( 32 );

export interface SizeHintFields {
	pv_kwp: number;
	annual_kwh: number;
	phase: 1 | 3;
	backup: 'none' | 'needed' | 'needed_accessory_ok';
	plz: string;
}

export interface ProjectBriefV1 {
	v: 1;
	id: string;
	text: string;
	sourcePath: string;
	contextScope: string;
	revision: string;
	confirmed: Partial< SizeHintFields >;
}

type Config = Pick< GenieConfig, 'restUrl' | 'restNonce' >;

function validPath( path: unknown ): path is string {
	return (
		typeof path === 'string' &&
		path.length > 0 &&
		path.length <= 256 &&
		path.startsWith( '/' ) &&
		! path.startsWith( '//' ) &&
		! path.includes( '\r' ) &&
		! path.includes( '\n' ) &&
		! path.includes( '?' ) &&
		! path.includes( '#' )
	);
}

function validConfirmed( value: unknown ): value is Partial< SizeHintFields > {
	if ( ! value || typeof value !== 'object' || Array.isArray( value ) ) {
		return false;
	}
	const record = value as Record< string, unknown >;
	for ( const [ key, item ] of Object.entries( record ) ) {
		if ( item === undefined ) {
			continue;
		}
		if (
			( key === 'pv_kwp' || key === 'annual_kwh' ) &&
			( typeof item !== 'number' ||
				! Number.isFinite( item ) ||
				item <= 0 )
		) {
			return false;
		} else if ( key === 'phase' && item !== 1 && item !== 3 ) {
			return false;
		} else if (
			key === 'backup' &&
			item !== 'none' &&
			item !== 'needed' &&
			item !== 'needed_accessory_ok'
		) {
			return false;
		} else if (
			key === 'plz' &&
			( typeof item !== 'string' ||
				! item.trim() ||
				Array.from( item ).length > MAX_PROJECT_BRIEF_LENGTH )
		) {
			return false;
		} else if (
			! [ 'pv_kwp', 'annual_kwh', 'phase', 'backup', 'plz' ].includes(
				key
			)
		) {
			return false;
		}
	}
	return true;
}

export function isProjectBrief( value: unknown ): value is ProjectBriefV1 {
	if ( ! value || typeof value !== 'object' ) {
		return false;
	}
	const item = value as Partial< ProjectBriefV1 >;
	return (
		item.v === 1 &&
		typeof item.id === 'string' &&
		/^[a-f0-9]{32}$/.test( item.id ) &&
		typeof item.text === 'string' &&
		item.text.trim().length > 0 &&
		Array.from( item.text ).length <= MAX_PROJECT_BRIEF_LENGTH &&
		validPath( item.sourcePath ) &&
		typeof item.contextScope === 'string' &&
		/^[a-f0-9]{64}$/.test( item.contextScope ) &&
		typeof item.revision === 'string' &&
		/^[a-f0-9]{64}$/.test( item.revision ) &&
		validConfirmed( item.confirmed )
	);
}

export function readProjectBrief( scope: string ): ProjectBriefV1 | null {
	if ( ! /^[a-f0-9]{64}$/.test( scope ) ) {
		return null;
	}
	try {
		const raw = sessionStorage.getItem( PROJECT_BRIEF_KEY );
		if ( ! raw ) {
			return null;
		}
		const parsed: unknown = JSON.parse( raw );
		if ( ! isProjectBrief( parsed ) || parsed.contextScope !== scope ) {
			sessionStorage.removeItem( PROJECT_BRIEF_KEY );
			return null;
		}
		return parsed;
	} catch {
		return null;
	}
}

export function writeProjectBrief( brief: ProjectBriefV1 ): boolean {
	if ( ! isProjectBrief( brief ) ) {
		return false;
	}
	try {
		const encoded = JSON.stringify( brief );
		sessionStorage.setItem( PROJECT_BRIEF_KEY, encoded );
		return sessionStorage.getItem( PROJECT_BRIEF_KEY ) === encoded;
	} catch {
		return false;
	}
}

export function clearProjectBrief( scope: string, id?: string ): boolean {
	try {
		const raw = sessionStorage.getItem( PROJECT_BRIEF_KEY );
		if ( ! raw ) {
			return true;
		}
		const parsed: unknown = JSON.parse( raw );
		if (
			! isProjectBrief( parsed ) ||
			parsed.contextScope !== scope ||
			( id !== undefined && parsed.id !== id )
		) {
			return false;
		}
		if ( sessionStorage.getItem( PROJECT_BRIEF_KEY ) !== raw ) {
			return false;
		}
		sessionStorage.removeItem( PROJECT_BRIEF_KEY );
		return sessionStorage.getItem( PROJECT_BRIEF_KEY ) === null;
	} catch {
		return false;
	}
}

function ensureTabToken(): string {
	let tab = sessionStorage.getItem( TAB_KEY );
	if ( ! tab || ! /^[0-9a-f-]{36}$/.test( tab ) ) {
		tab = crypto.randomUUID();
		sessionStorage.setItem( TAB_KEY, tab );
		if ( sessionStorage.getItem( TAB_KEY ) !== tab ) {
			throw new Error( 'project-brief-tab' );
		}
	}
	return tab;
}

export async function stageProjectBrief(
	config: Config,
	input: {
		text: string;
		sourcePath: string;
		briefId?: string | null;
		expectedRevision?: string | null;
		confirmed?: Partial< SizeHintFields >;
	}
): Promise< ProjectBriefV1 > {
	if (
		! input.text.trim() ||
		Array.from( input.text ).length > MAX_PROJECT_BRIEF_LENGTH ||
		! validPath( input.sourcePath )
	) {
		throw new Error( 'project-brief-input' );
	}
	const tab = ensureTabToken();
	const payload: Record< string, unknown > = {
		schema_version: 1,
		tab,
		text: input.text,
		source_path: input.sourcePath,
	};
	if ( input.briefId && input.briefId !== UNSTAGED_BRIEF_ID ) {
		payload.brief_id = input.briefId;
	}
	if ( input.expectedRevision && input.briefId !== UNSTAGED_BRIEF_ID ) {
		payload.expected_revision = input.expectedRevision;
	}
	const response = await fetch(
		`${ config.restUrl }linker-ai/v1/genie/project-brief`,
		{
			method: 'POST',
			credentials: 'same-origin',
			cache: 'no-store',
			headers: {
				'Content-Type': 'application/json',
				'X-WP-Nonce': config.restNonce,
			},
			body: JSON.stringify( payload ),
		}
	);
	if ( ! response.ok ) {
		throw new Error( 'project-brief-stage' );
	}
	const result: unknown = await response.json();
	if ( ! result || typeof result !== 'object' ) {
		throw new Error( 'project-brief-readback' );
	}
	const data = result as Record< string, unknown >;
	if (
		data.schema_version !== 1 ||
		typeof data.brief_id !== 'string' ||
		! /^[a-f0-9]{32}$/.test( data.brief_id ) ||
		typeof data.revision !== 'string' ||
		! /^[a-f0-9]{64}$/.test( data.revision ) ||
		data.text !== input.text ||
		data.source_path !== input.sourcePath ||
		typeof data.scope !== 'string' ||
		! /^[a-f0-9]{64}$/.test( data.scope )
	) {
		throw new Error( 'project-brief-readback' );
	}
	const record: ProjectBriefV1 = {
		v: 1,
		id: data.brief_id,
		text: data.text,
		sourcePath: data.source_path,
		contextScope: data.scope,
		revision: data.revision,
		confirmed: input.confirmed ?? {},
	};
	if ( ! writeProjectBrief( record ) ) {
		throw new Error( 'project-brief-storage' );
	}
	return record;
}
