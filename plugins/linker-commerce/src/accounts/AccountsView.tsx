/**
 * WordPress dependencies
 */
import { useCallback, useEffect, useState } from '@wordpress/element';
import { __ } from '@wordpress/i18n';

/**
 * Internal dependencies
 */
import { AccountCard } from './AccountCard';
import { AccountsApi } from './api';
import type { Account, Counts, Decision } from './types';

interface Props {
	api: AccountsApi;
	focusId: number;
	status?: 'pending' | 'restricted';
	changes: Record< number, Account >;
	onCounts: ( counts: Counts ) => void;
	onSave: ( id: number, status: Decision, reason: string ) => Promise< void >;
}

// Each native surface owns its read/error state; saved decisions are shared.
export function AccountsView( {
	api,
	focusId,
	status = 'pending',
	changes,
	onCounts,
	onSave,
}: Props ) {
	const [ items, setItems ] = useState< Account[] >( [] );
	const [ loading, setLoading ] = useState( true );
	const [ error, setError ] = useState( '' );
	const load = useCallback( async () => {
		setLoading( true );
		setError( '' );
		try {
			const result = await api.list( focusId, status );
			setItems( result.accounts );
			onCounts( result.counts );
		} catch ( failure ) {
			setError(
				failure instanceof Error
					? failure.message
					: __(
							'The request failed. Please try again.',
							'linker-commerce'
						)
			);
		} finally {
			setLoading( false );
		}
	}, [ api, focusId, status, onCounts ] );
	useEffect( () => {
		void load();
	}, [ load ] );
	useEffect( () => {
		if ( focusId && ! loading && ! error ) {
			document
				.getElementById( 'linker-accounts-focus' )
				?.scrollIntoView( { block: 'start' } );
		}
	}, [ focusId, loading, error ] );
	if ( loading ) {
		return (
			<p role="status">
				{ __( 'Loading accounts…', 'linker-commerce' ) }
			</p>
		);
	}
	if ( error ) {
		return (
			<div className="notice notice-error inline" role="alert">
				<p>{ error }</p>
				<button
					type="button"
					className="button"
					onClick={ () => void load() }
				>
					{ __( 'Try again', 'linker-commerce' ) }
				</button>
			</div>
		);
	}
	// A restriction saved on the focused card appears in the follow-up section
	// immediately, without making the employee reload the historical table.
	const listed =
		status === 'restricted' && ! focusId
			? [
					...items,
					...Object.values( changes ).filter(
						( item ) =>
							item.status === 'restricted' &&
							! items.some(
								( existing ) => existing.id === item.id
							)
					),
				].filter(
					( item ) =>
						( changes[ item.id ] || item ).status === 'restricted'
				)
			: items;
	return (
		<div className="linker-account-cards">
			{ listed.map( ( item ) => (
				<AccountCard
					key={ item.id }
					account={ changes[ item.id ] || item }
					focused={ focusId > 0 }
					onSave={ onSave }
				/>
			) ) }
			{ ! listed.length && (
				<p>
					{ status === 'restricted'
						? __(
								'No restricted accounts are awaiting customer information.',
								'linker-commerce'
							)
						: __(
								'No accounts are waiting for review. New registrations will appear here and in the top bar.',
								'linker-commerce'
							) }
				</p>
			) }
		</div>
	);
}
