/**
 * WordPress dependencies
 */
import { createPortal, useEffect, useRef, useState } from '@wordpress/element';
import { __, _n, sprintf } from '@wordpress/i18n';

/**
 * Internal dependencies
 */
import { AccountsView } from './AccountsView';
import { AccountsApi } from './api';
import type { Account, Counts, Decision } from './types';

function updateChrome( counts: Counts ) {
	const label = sprintf(
		/* translators: %s: number of accounts waiting for review. */
		_n(
			'%s account to review',
			'%s accounts to review',
			counts.pending,
			'linker-commerce'
		),
		String( counts.pending )
	);
	document
		.querySelectorAll< HTMLElement >( '[data-linker-account-count]' )
		.forEach( ( node ) => {
			const state = node.dataset.linkerAccountCount;
			node.textContent = String(
				state === 'all'
					? Object.values( counts ).reduce(
							( sum, count ) => sum + count,
							0
						)
					: counts[ state as keyof Counts ]
			);
		} );
	const bar = document.getElementById( 'wp-admin-bar-linker-accounts' );
	bar?.classList.toggle( 'linker-has-pending', counts.pending > 0 );
	const text = bar?.querySelector( '.linker-review-label' );
	if ( text ) {
		text.textContent = label;
	}
	bar?.querySelector( 'a' )?.setAttribute( 'aria-label', label );
}

export function AccountsApp( {
	api,
	focusId,
}: {
	api: AccountsApi;
	focusId: number;
} ) {
	const [ changes, setChanges ] = useState< Record< number, Account > >( {} );
	const [ open, setOpen ] = useState( false );
	const [ drawerFocus, setDrawerFocus ] = useState( 0 );
	const dialog = useRef< HTMLDialogElement >( null );
	const trigger = useRef< HTMLElement | null >( null );
	const queueMount = document.getElementById( 'linker-accounts-queue' );
	const focusMount = document.getElementById( 'linker-accounts-focus' );
	const restrictedMount = document.getElementById(
		'linker-accounts-restricted'
	);
	useEffect( () => {
		const onClick = ( event: MouseEvent ) => {
			const element =
				event.target instanceof Element
					? event.target.closest< HTMLElement >(
							'#wp-admin-bar-linker-accounts > a, [data-linker-account]'
						)
					: null;
			if (
				! element ||
				event.ctrlKey ||
				event.metaKey ||
				event.shiftKey ||
				event.altKey
			) {
				return;
			}
			event.preventDefault();
			trigger.current = element;
			setDrawerFocus( Number( element.dataset.linkerAccount || 0 ) );
			setOpen( true );
		};
		document.addEventListener( 'click', onClick );
		document
			.querySelector( '#wp-admin-bar-linker-accounts > a' )
			?.setAttribute( 'aria-haspopup', 'dialog' );
		return () => document.removeEventListener( 'click', onClick );
	}, [] );
	useEffect( () => {
		if ( open && ! dialog.current?.open ) {
			dialog.current?.showModal();
		} else if ( ! open && dialog.current?.open ) {
			dialog.current.close();
		}
	}, [ open ] );
	async function save( id: number, status: Decision, reason: string ) {
		const result = await api.decide( id, status, reason );
		setChanges( ( current ) => ( { ...current, [ id ]: result.account } ) );
		updateChrome( result.counts );
		const row = document.getElementById( `linker-account-row-${ id }` );
		const label = row?.querySelector( '.linker-account-status-label' );
		const value = row?.querySelector( '.linker-account-reason-value' );
		if ( label ) {
			label.textContent = result.account.statusLabel;
		}
		if ( value ) {
			value.textContent = result.account.reason;
		}
		const filter = document.getElementById( 'linker-accounts-history' )
			?.dataset.status;
		if ( row ) {
			row.hidden = Boolean(
				filter && filter !== 'all' && filter !== status
			);
		}
	}
	const view = (
		id: number,
		status: 'pending' | 'restricted' = 'pending'
	) => (
		<AccountsView
			api={ api }
			focusId={ id }
			status={ status }
			changes={ changes }
			onCounts={ updateChrome }
			onSave={ save }
		/>
	);
	return (
		<>
			{ queueMount && createPortal( view( 0 ), queueMount ) }
			{ focusMount &&
				focusId > 0 &&
				createPortal( view( focusId ), focusMount ) }
			{ restrictedMount &&
				createPortal( view( 0, 'restricted' ), restrictedMount ) }
			<dialog
				ref={ dialog }
				id="linker-accounts-dialog"
				aria-labelledby="linker-accounts-dialog-title"
				onClose={ () => {
					setOpen( false );
					const previous = trigger.current;
					const fallback = document.querySelector< HTMLElement >(
						'#wp-admin-bar-linker-accounts > a'
					);
					( previous?.isConnected && previous.getClientRects().length
						? previous
						: fallback
					)?.focus();
				} }
			>
				<header>
					<h2 id="linker-accounts-dialog-title">
						{ drawerFocus
							? __( 'Review account', 'linker-commerce' )
							: __(
									'Accounts waiting for you',
									'linker-commerce'
								) }
					</h2>
					<button
						type="button"
						className="button"
						onClick={ () => setOpen( false ) }
					>
						{ __( 'Close', 'linker-commerce' ) }
					</button>
				</header>
				{ open && view( drawerFocus ) }
			</dialog>
		</>
	);
}
