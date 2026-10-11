/**
 * The run's precondition (docs/specs/16-review-acceptance.md §环境).
 *
 * Everything in this suite is an assertion about a real instance, so a
 * missing instance is a failure of the run, not a skip: the setup names what
 * is wrong and the suite stops before the first spec.
 */

/**
 * External dependencies
 */
import { request } from '@playwright/test';

/**
 * Internal dependencies
 */
import { instance, instanceName, localHome, REPO_ROOT } from './instance';

export const INSTANCE_READY =
	'the instance answers /wp-json/ and both services report healthy';

export default async function globalSetup(): Promise<void> {
	const name = instanceName();
	const target = instance(name);
	const context = await request.newContext({ timeout: 20_000 });

	const checks: Array<
		[string, () => Promise<{ ok(): boolean; status(): number }>]
	> = [
		['WordPress', () => context.get(`${target.url}/wp-json/`)],
		['the engine', () => context.get(`${target.engineUrl}/health`)],
		['Genie', () => context.get(`${target.genieUrl}/health`)],
	];

	const failures: string[] = [];
	for (const [label, probe] of checks) {
		try {
			const response = await probe();
			if (!response.ok()) {
				failures.push(`${label} answered ${response.status()}`);
			}
		} catch (error) {
			failures.push(`${label}: ${(error as Error).message}`);
		}
	}
	await context.dispose();

	if (failures.length > 0) {
		throw new Error(
			`instance ${name} is not ready (${REPO_ROOT}, ${localHome()}):\n  ` +
				`${failures.join('\n  ')}\n` +
				`Start it with \`just up ${name}\`, load the snapshot, then \`just serve ${name}\` ` +
				'(docs/local-stack.md, docs/specs/6-live-pull.md).'
		);
	}
}
