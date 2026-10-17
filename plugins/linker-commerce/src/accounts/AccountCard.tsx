/**
 * WordPress dependencies
 */
import { useId, useState } from '@wordpress/element';
import { __ } from '@wordpress/i18n';

/**
 * Internal dependencies
 */
import type { Account, Decision } from './types';

interface Props {
	account: Account;
	focused?: boolean;
	onSave: ( id: number, status: Decision, reason: string ) => Promise< void >;
}

export function AccountCard( { account, focused = false, onSave }: Props ) {
	const id = useId();
	const [ decision, setDecision ] = useState< Decision | null >( null );
	const [ reason, setReason ] = useState( account.reason );
	const [ busy, setBusy ] = useState( false );
	const [ error, setError ] = useState( '' );
	const [ saved, setSaved ] = useState( false );

	async function save( status: Decision ) {
		if ( status !== 'approved' && ! reason.trim() ) {
			setError(
				__(
					'Enter a reason for the customer before restricting or rejecting the account.',
					'linker-commerce'
				)
			);
			return;
		}
		setBusy( true );
		setError( '' );
		setSaved( false );
		try {
			await onSave(
				account.id,
				status,
				status === 'approved' ? '' : reason
			);
			setDecision( null );
			setSaved( true );
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
			setBusy( false );
		}
	}

	const choose = ( status: Decision ) => {
		setSaved( false );
		setError( '' );
		if ( status === 'approved' ) {
			void save( status );
		} else {
			setReason( account.reason );
			setDecision( status );
		}
	};

	return (
		<article
			className={ `linker-account-card ${ focused ? 'is-focused' : '' }` }
			aria-labelledby={ `${ id }-title` }
			aria-busy={ busy }
			data-account-id={ account.id }
		>
			<h3 id={ `${ id }-title` }>{ account.company }</h3>
			<p className="description">
				{ [ account.country, account.businessType, account.registered ]
					.filter( Boolean )
					.join( ' · ' ) }
			</p>
			<p>
				{ account.contact } ·{ ' ' }
				<a href={ `mailto:${ account.email }` }>{ account.email }</a>
			</p>
			<p>
				<strong>{ account.statusLabel }</strong>
				{ account.audit && (
					<span className="description"> · { account.audit }</span>
				) }
			</p>
			{ account.reason && <p>{ account.reason }</p> }
			<ul
				className="linker-account-signals"
				aria-label={ __( 'Automatic checks', 'linker-commerce' ) }
			>
				{ account.signals.map( ( signal ) => (
					<li
						className={ `notice notice-${ signal.tone } inline` }
						key={ signal.text }
					>
						{ signal.text }
					</li>
				) ) }
			</ul>
			<p className="linker-account-links">
				{ account.links.map( ( link ) => (
					<a
						key={ link.url }
						href={ link.url }
						target="_blank"
						rel="noreferrer noopener"
					>
						{ link.label } ↗
					</a>
				) ) }
			</p>
			<details open={ focused }>
				<summary>{ __( 'Details', 'linker-commerce' ) }</summary>
				<dl className="linker-account-fields">
					{ account.fields.map( ( field ) => (
						<div key={ field.key }>
							<dt>{ field.label }</dt>
							<dd>
								{ field.website ? (
									<a
										href={ field.value }
										target="_blank"
										rel="noreferrer noopener"
									>
										{ field.value }
									</a>
								) : (
									field.value
								) }
							</dd>
						</div>
					) ) }
				</dl>
			</details>
			<p>
				{ account.switchUrl ? (
					<a href={ account.switchUrl }>
						{ __(
							'View the website as this customer',
							'linker-commerce'
						) }
					</a>
				) : (
					<span className="description">{ account.switchNote }</span>
				) }
			</p>
			<div className="linker-account-actions">
				<button
					type="button"
					className="button button-primary"
					disabled={ busy }
					onClick={ () => choose( 'approved' ) }
				>
					{ __( 'Approve', 'linker-commerce' ) }
				</button>
				<button
					type="button"
					className="button"
					disabled={ busy }
					onClick={ () => choose( 'restricted' ) }
				>
					{ __( 'Restrict', 'linker-commerce' ) }
				</button>
				<button
					type="button"
					className="button button-link-delete"
					disabled={ busy }
					onClick={ () => choose( 'rejected' ) }
				>
					{ __( 'Reject', 'linker-commerce' ) }
				</button>
			</div>
			{ decision && (
				<form
					className="linker-account-reason"
					onSubmit={ ( event ) => {
						event.preventDefault();
						void save( decision );
					} }
				>
					<label htmlFor={ `${ id }-reason` }>
						{ __( 'Reason for the customer', 'linker-commerce' ) }
					</label>
					<p className="description" id={ `${ id }-hint` }>
						{ __(
							'The customer receives this reason by email. Explain what information is needed or why the account cannot be approved.',
							'linker-commerce'
						) }
					</p>
					<textarea
						id={ `${ id }-reason` }
						aria-describedby={ `${ id }-hint` }
						required
						rows={ 3 }
						value={ reason }
						disabled={ busy }
						onChange={ ( event ) =>
							setReason( event.target.value )
						}
					/>
					<div className="linker-account-actions">
						<button
							type="submit"
							className="button button-primary"
							disabled={ busy }
						>
							{ decision === 'restricted'
								? __(
										'Restrict and notify customer',
										'linker-commerce'
									)
								: __(
										'Reject and notify customer',
										'linker-commerce'
									) }
						</button>
						<button
							type="button"
							className="button"
							disabled={ busy }
							onClick={ () => {
								setDecision( null );
								setError( '' );
							} }
						>
							{ __( 'Cancel', 'linker-commerce' ) }
						</button>
					</div>
				</form>
			) }
			{ busy && (
				<p role="status">
					{ __( 'Saving decision…', 'linker-commerce' ) }
				</p>
			) }
			{ error && (
				<div className="notice notice-error inline" role="alert">
					<p>{ error }</p>
				</div>
			) }
			{ saved && (
				<div className="notice notice-success inline" role="status">
					<p>
						{ __(
							'Decision saved. You can change it at any time.',
							'linker-commerce'
						) }
					</p>
				</div>
			) }
		</article>
	);
}
