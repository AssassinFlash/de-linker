import { render, screen } from '@testing-library/react';
import { resetLocaleData, setLocaleData } from '@wordpress/i18n';
import { afterEach, expect, test } from 'vitest';
import germanGenie from '../../../languages/linker-tools-de_DE_formal-c2be3a742ec1f5e619cd2beb8d234138.json';
import type { PlanningSourcesAvailableBlock } from '../api/turn';
import { PlanningSourcesCard } from './PlanningSourcesCard';
import { TurnProgress } from './TurnProgress';

afterEach( () => resetLocaleData( {}, 'linker-tools' ) );

test.each( [ 'en', 'de' ] )(
	'%s shows turn progress and identifies historical sources using the shipped catalogs',
	( locale ) => {
		if ( locale === 'de' ) {
			setLocaleData( germanGenie.locale_data.messages, 'linker-tools' );
		}
		const source: PlanningSourcesAvailableBlock = {
			type: 'planning_sources',
			schema_version: 1,
			status: 'available',
			binding: {
				planning_project_id: 'project',
				planning_revision: 5,
				planning_run_ids: [ 'older-run' ],
				runs: [
					{
						id: 'older-run',
						revision: 4,
						manifest_sha256: 'a'.repeat( 64 ),
						result_sha256: 'b'.repeat( 64 ),
					},
				],
			},
			results: [ { revision: 4, groups: [] } ],
			url: '/solution-configurator/?project=project&run=older-run#lp-calculations',
		};
		const notice =
			locale === 'de'
				? 'Diese Quellenkarte gehört zu einer früheren Antwort und bezieht sich nicht auf die aktuelle Anfrage.'
				: 'This source card belongs to an earlier response, not the current request.';
		const view = render(
			<ol>
				<TurnProgress skeleton />
			</ol>
		);
		expect(
			view.container.querySelector( '.linker-genie-wait__lines' )
		).toBeVisible();
		view.rerender(
			<PlanningSourcesCard
				block={ source }
				currentPage={ {
					type: 'tool',
					planning_project_id: 'project',
					planning_revision: 5,
					planning_run_ids: [ 'older-run' ],
				} }
			/>
		);
		// Selecting an older saved run in the current revision is a valid current context.
		expect( screen.queryByText( notice ) ).toBeNull();
		view.rerender(
			<PlanningSourcesCard
				block={ source }
				currentPage={ {
					type: 'tool',
					planning_project_id: 'project',
					planning_revision: 5,
					planning_run_ids: [ 'new-run' ],
				} }
			/>
		);
		expect( screen.getByText( notice ) ).toBeVisible();
		expect(
			screen.getByText(
				locale === 'de' ? 'Gespeicherter Stand 4' : 'Saved revision 4'
			)
		).toBeVisible();
	}
);
