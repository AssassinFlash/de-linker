/**
 * The local instance the suite runs against (docs/local-stack.md).
 *
 * One instance per ticket: `just up t16e`, then `just pull load …`, then
 * `just serve t16e`. The suite finds it through the machine-wide registry
 * `~/de-linker-local/instances.toml` (its ports), the checkout it was cut
 * from (the repo root, for `just`), and the instance directory (mail, logs).
 */

/**
 * External dependencies
 */
import { execFileSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

/** The repository root: tests/e2e/lib -> three levels up. */
export const REPO_ROOT = resolve(
	dirname(fileURLToPath(import.meta.url)),
	'..',
	'..',
	'..'
);

/** Where the instances live (tools/local's default; `LINKER_LOCAL_HOME` overrides). */
export function localHome(): string {
	return process.env.LINKER_LOCAL_HOME ?? join(homedir(), 'de-linker-local');
}

export interface Instance {
	/** The instance name (`just up <name>`). */
	name: string;
	/** WordPress, as the browser sees it. */
	url: string;
	/** The Solution Configurator engine. */
	engineUrl: string;
	/** Genie's agent loop. */
	genieUrl: string;
	/** The instance's data directory (mail/, logs/, wordpress/). */
	dir: string;
}

interface Row {
	port: number;
	engine_port: number;
	genie_port: number;
}

/**
 * The name the run was started with. `just e2e <name>` exports it.
 */
export function instanceName(): string {
	const name = process.env.LINKER_E2E_INSTANCE;
	if (!name) {
		throw new Error(
			'LINKER_E2E_INSTANCE is not set: run the suite with `just e2e <name>` ' +
				'(the instance `just up <name>` built).'
		);
	}
	return name;
}

/**
 * The registered ports of one instance; throws when the name is unknown, so a
 * typo fails loudly instead of testing whatever answers on a default port.
 */
export function instance(name: string = instanceName()): Instance {
	const registry = join(localHome(), 'instances.toml');
	if (!existsSync(registry)) {
		throw new Error(
			`${registry} does not exist: no local instance has been created on this machine.`
		);
	}
	const row = parseRegistry(readFileSync(registry, 'utf8'))[name];
	if (!row) {
		throw new Error(
			`${name} is not in ${registry}: create it with \`just up ${name}\`.`
		);
	}
	const host = 'http://127.0.0.1';
	return {
		name,
		url: `${host}:${row.port}`,
		engineUrl: `${host}:${row.engine_port}`,
		genieUrl: `${host}:${row.genie_port}`,
		dir: join(localHome(), name),
	};
}

/**
 * `[name]` tables with `key = number` rows, as `linker-local` writes them.
 */
export function parseRegistry(text: string): Record<string, Row> {
	const rows: Record<string, Row> = {};
	let current = '';
	for (const line of text.split('\n')) {
		const table = /^\[([^\]]+)\]\s*$/.exec(line);
		if (table) {
			current = table[1] ?? '';
			rows[current] = { port: 0, engine_port: 0, genie_port: 0 };
			continue;
		}
		const value = /^(\w+)\s*=\s*(\d+)\s*$/.exec(line);
		const row = rows[current];
		if (!row || !value) {
			continue;
		}
		const key = value[1] as keyof Row;
		if (key === 'port' || key === 'engine_port' || key === 'genie_port') {
			row[key] = Number(value[2]);
		}
	}
	return rows;
}

/** The directory `linker-local` writes captured mail into. */
export function mailDir(name: string = instanceName()): string {
	return join(localHome(), name, 'mail');
}

/** The directory the instance keeps its logs in. */
export function logDir(name: string = instanceName()): string {
	return join(localHome(), name, 'logs');
}

/**
 * A one-time login link for `user` (`just login <name> --user <login>`).
 *
 * The link is minted per call and burns on use: every helper that needs a
 * session asks for its own.
 */
export function loginLink(
	name: string = instanceName(),
	user = 'local-admin'
): string {
	return runJust(['login', name, `--user=${user}`])
		.trim()
		.split('\n')
		.pop()!
		.trim();
}

/** WP-CLI against the instance (`just wp <name> …`). */
export function wp(args: string[], name: string = instanceName()): string {
	return runJust(['wp', name, ...args]);
}

/**
 * Runs `just` and reports how it ended, for tools whose own exit code is part
 * of their answer (`linker-pull check-urls` exits non-zero when a snapshot
 * address does not answer 200, and its JSON summary is still the result).
 */
export function runJustRaw(args: string[]): { stdout: string; status: number } {
	try {
		const stdout = execFileSync('just', args, {
			cwd: REPO_ROOT,
			encoding: 'utf8',
			stdio: ['ignore', 'pipe', 'pipe'],
			maxBuffer: 64 * 1024 * 1024,
		});
		return { stdout, status: 0 };
	} catch (error) {
		// execFileSync's error carries the child's own output and exit code,
		// which for these tools is the answer, not a failure of the run.
		const failure = error as {
			stdout?: string;
			stderr?: string;
			status?: number;
		};
		return {
			stdout: failure.stdout || failure.stderr || String(error),
			status: failure.status ?? 1,
		};
	}
}

/**
 * Local Turnstile acceptance profile: Cloudflare's official always-pass dummy
 * pair, `enforce` so the browser chain runs the real verification, and the
 * testing hostname the dummy keys always report (siteverify metadata
 * `result_with_testing_key`). Production refuses the test key families
 * (Protection\Configuration::test_keys), so this cannot weaken live.
 *
 * These are the same values `just turnstile-test` writes for a human run. A
 * browser suite must not leave them behind: they turn every public door on the
 * instance into an enforce-mode chain, and the PHP integration suites that post
 * through those doors without a proof expect the instance as they found it.
 */
export const TURNSTILE_PROFILE: Record<string, string> = {
	LINKER_PUBLIC_PROTECTION_MODE: 'enforce',
	LINKER_TURNSTILE_SITE_KEY: '1x00000000000000000000AA',
	LINKER_TURNSTILE_SECRET_KEY: '1x0000000000000000000000000000000AA',
	LINKER_TURNSTILE_HOSTNAME: 'example.com',
	// The dummy keys always pass at Cloudflare; this constant makes the
	// server answer that verdict locally (Turnstile.php) so the suite stops
	// depending on this machine's network for every verification.
	LINKER_TURNSTILE_LOCAL_VERIFY: '1',
};

/**
 * Apply the dummy profile for one run and return the restore that puts the
 * instance's own constants back (an absent constant is deleted again). Reads
 * and writes go through WP-CLI, so the running site sees the same values the
 * suite's fixtures read back.
 */
export function applyTurnstileProfile(
	name: string = instanceName()
): () => void {
	const prior = Object.keys(TURNSTILE_PROFILE).map((constant) => {
		const current = runJustRaw([
			'wp',
			name,
			'config',
			'get',
			constant,
			'--type=constant',
		]);
		return {
			constant,
			value: current.status === 0 ? current.stdout.trim() : null,
		};
	});
	for (const [constant, value] of Object.entries(TURNSTILE_PROFILE)) {
		wp(
			['config', 'set', constant, value, '--type=constant', '--quiet'],
			name
		);
		if (
			wp(['config', 'get', constant, '--type=constant'], name).trim() !==
			value
		) {
			throw new Error(
				`turnstile profile: ${constant} did not read back as applied`
			);
		}
	}
	return () => {
		for (const { constant, value } of prior) {
			if (value === null) {
				wp(
					[
						'config',
						'delete',
						constant,
						'--type=constant',
						'--quiet',
					],
					name
				);
				continue;
			}
			wp(
				[
					'config',
					'set',
					constant,
					value,
					'--type=constant',
					'--quiet',
				],
				name
			);
		}
	};
}

/** Runs `just` from the repository root; throws with the captured output. */
export function runJust(
	args: string[],
	options: { env?: NodeJS.ProcessEnv } = {}
): string {
	try {
		return execFileSync('just', args, {
			cwd: REPO_ROOT,
			encoding: 'utf8',
			stdio: ['ignore', 'pipe', 'pipe'],
			maxBuffer: 64 * 1024 * 1024,
			env: { ...process.env, ...options.env },
		});
	} catch (error) {
		const failure = error as {
			stderr?: string;
			stdout?: string;
			message: string;
		};
		throw new Error(
			`just ${args.join(' ')} failed: ${failure.stderr || failure.stdout || failure.message}`
		);
	}
}
