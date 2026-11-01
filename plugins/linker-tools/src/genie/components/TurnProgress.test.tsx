import { fireEvent, render, screen } from '@testing-library/react';
import { resetLocaleData, setLocaleData } from '@wordpress/i18n';
import { afterEach, expect, test, vi } from 'vitest';
import germanGenie from '../../../languages/linker-tools-de_DE_formal-c2be3a742ec1f5e619cd2beb8d234138.json';
import germanHero from '../../../languages/linker-tools-de_DE_formal-6796211aef57736d0923df38ef696ad2.json';
import type { PlanningSourcesAvailableBlock } from '../api/turn';
import { PlanningSourcesCard } from './PlanningSourcesCard';
import { TurnProgress } from './TurnProgress';

afterEach( () => resetLocaleData( {}, 'linker-tools' ) );

test.each( [ 'en', 'de' ] )(
	'%s distinguishes unsent verification and historical sources using the shipped catalogs',
	( locale ) => {
		expect(
			germanHero.locale_data.messages[ 'Cancel verification' ]
		).toEqual( [ 'Prüfung abbrechen' ] );
		if ( locale === 'de' ) {
			setLocaleData( germanHero.locale_data.messages, 'linker-tools' );
			setLocaleData( germanGenie.locale_data.messages, 'linker-tools' );
		}
		const cancel = vi.fn();
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
				<TurnProgress
					verificationPending
					onCancel={ cancel }
					skeleton
				/>
			</ol>
		);
		fireEvent.click(
			screen.getByRole( 'button', {
				name:
					locale === 'de'
						? 'Prüfung abbrechen'
						: 'Cancel verification',
			} )
		);
		expect( cancel ).toHaveBeenCalledOnce();
		expect(
			view.container.querySelector( '.linker-genie-wait__lines' )
		).toBeNull();
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
