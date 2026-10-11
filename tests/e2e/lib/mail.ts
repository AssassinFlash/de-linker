/**
 * The instance's captured mail (docs/local-stack.md §隔离): `wp_mail()`
 * writes a real message — headers and body as the host's `mail()` would have
 * received it — into `mail/<time>-<uuid>.eml`.
 *
 * The suite reads that spool the way the customer's mailbox would: subjects,
 * recipients, the Bcc the company copy carries, and the decoded text.
 */

/**
 * External dependencies
 */
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';

/**
 * Internal dependencies
 */
import { mailDir } from './instance';

export interface Message {
	file: string;
	/** When the message was written, in ms. */
	writtenAt: number;
	to: string[];
	cc: string[];
	bcc: string[];
	subject: string;
	/** The decoded `text/plain` body, or the decoded HTML when there is none. */
	body: string;
	/** The decoded `text/html` body, when the message has one. */
	html: string;
}

/** Every message in the spool, oldest first. */
export function messages(): Message[] {
	const dir = mailDir();
	let names: string[];
	try {
		names = readdirSync(dir).filter((name) => name.endsWith('.eml'));
	} catch {
		return [];
	}
	return names
		.map((name) => {
			const file = join(dir, name);
			return parse(
				name,
				readFileSync(file, 'utf8'),
				statSync(file).mtimeMs
			);
		})
		.sort((left, right) => left.writtenAt - right.writtenAt);
}

/**
 * Messages written after `since` (ms), optionally filtered by subject.
 */
export function since(sinceMs: number, subject?: string | RegExp): Message[] {
	return messages().filter((message) => {
		if (message.writtenAt <= sinceMs) {
			return false;
		}
		return subject === undefined || matches(message.subject, subject);
	});
}

function matches(value: string, wanted: string | RegExp): boolean {
	return typeof wanted === 'string' ? value === wanted : wanted.test(value);
}

/** Now, as `since()` wants it — take it before the action that sends mail. */
export function mark(): number {
	return Date.now();
}

/** Parses one `.eml`. */
export function parse(file: string, raw: string, writtenAt: number): Message {
	const split = raw.split(/\r?\n\r?\n/);
	const header = split.shift() ?? '';
	const body = split.join('\n\n');
	const fields = unfold(header);
	const contentType = (fields['content-type'] ?? '').toLowerCase();
	const transfer = (fields['content-transfer-encoding'] ?? '').toLowerCase();
	const parts = body.split(/------=_Part_|--[-\w]+boundary[-\w]*/);
	return {
		file,
		writtenAt,
		to: addresses(fields.to ?? ''),
		cc: addresses(fields.cc ?? ''),
		bcc: addresses(fields.bcc ?? ''),
		subject: decode(fields.subject ?? ''),
		body: decodeBody(body, contentType, transfer, parts, 'text/plain'),
		html: decodeBody(body, contentType, transfer, parts, 'text/html'),
	};
}

/** `key: value` with continuation lines joined; keys lowercased. */
function unfold(header: string): Record<string, string> {
	const fields: Record<string, string> = {};
	let key: string | null = null;
	for (const line of header.split(/\r?\n/)) {
		if (/^[ \t]/.test(line) && key) {
			fields[key] = `${fields[key]} ${line.trim()}`;
			continue;
		}
		const match = /^([^:]+):\s?(.*)$/.exec(line);
		if (!match) {
			continue;
		}
		key = (match[1] ?? '').toLowerCase();
		fields[key] = match[2] ?? '';
	}
	return fields;
}

/** The mail addresses in a header, angle-address form preferred. */
export function addresses(header: string): string[] {
	const found: string[] = [];
	for (const part of header.split(',')) {
		const angle = /<([^>]+)>/.exec(part);
		const address = (angle?.[1] ?? part).trim();
		if (address.includes('@')) {
			found.push(address);
		}
	}
	return found;
}

/** MIME encoded-words (`=?UTF-8?Q?…?=`) decoded. */
function decode(value: string): string {
	return value.replace(
		/=\?[^?]+\?([BbQq])\?([^?]*)\?=/g,
		(_whole, encoding: string, text: string) =>
			encoding.toUpperCase() === 'B'
				? Buffer.from(text, 'base64').toString('utf8')
				: decodeQuotedPrintable(
						text
							.replace(/_/g, ' ')
							.replace(/=\?[^?]+\?[BbQq]\?[^?]*\?=/g, '')
					)
	);
}

/**
 * The body of one MIME type: the message's own body when it is that type, or
 * the matching part of a multipart message.
 */
function decodeBody(
	body: string,
	contentType: string,
	transfer: string,
	parts: string[],
	wanted: string
): string {
	if (!contentType.startsWith('multipart/')) {
		return contentType.includes(wanted)
			? decodeTransfer(body, transfer)
			: '';
	}
	for (const part of parts) {
		const split = part.split(/\r?\n\r?\n/);
		const header = (split.shift() ?? '').toLowerCase();
		if (header.includes(wanted)) {
			const encoding = /content-transfer-encoding:\s*(\S+)/.exec(header);
			return decodeTransfer(split.join('\n\n'), encoding?.[1] ?? '7bit');
		}
	}
	return '';
}

function decodeTransfer(body: string, encoding: string): string {
	if (encoding.includes('base64')) {
		return Buffer.from(body.replace(/\s/g, ''), 'base64').toString('utf8');
	}
	if (encoding.includes('quoted-printable')) {
		return decodeQuotedPrintable(body);
	}
	return body.trim();
}

function decodeQuotedPrintable(value: string): string {
	const joined = value.replace(/=\r?\n/g, '');
	const bytes: number[] = [];
	for (let index = 0; index < joined.length; index += 1) {
		const hex = /^=([0-9A-Fa-f]{2})/.exec(joined.slice(index));
		if (hex) {
			bytes.push(parseInt(hex[1] ?? '0', 16));
			index += 2;
			continue;
		}
		bytes.push(joined.charCodeAt(index) & 0xff);
	}
	return Buffer.from(bytes).toString('utf8');
}
