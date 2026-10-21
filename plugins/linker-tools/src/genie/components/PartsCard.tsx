/**
 * A parts list the service matched (#251): every row with what code made of it,
 * the first unclear row's question, and one button that writes every confirmed
 * row to the solution draft in one Store API call.
 *
 * The statuses are the service's (`services/genie parts.py`): the card only
 * words them. A row's confirmation is an ordinary message ("Row 3: SAJ
 * H2-10K-T3"), so the next turn rebuilds the same list with that row settled —
 * no state is kept in the shell. The add is the customer's click and the
 * shell's one `store.addAll`; the service never writes a draft.
 */

/**
 * WordPress dependencies
 */
import { __, sprintf } from '@wordpress/i18n';

/**
 * Internal dependencies
 */
import { useState } from '@wordpress/element';
import type { PartsBlock, PartsRow } from '../api/turn';

/** How the one draft write ended, for the card's own line. */
export type PartsAddResult = 'added' | 'unverified' | 'retry';

export interface PartsActions {
	/** Sends a message as the customer (a candidate, skip). */
	onAsk: ( message: string ) => void;
	/** The one Store API write for every confirmed row. */
	onAdd: (
		items: { product_id: number; quantity: number }[]
	) => Promise< PartsAddResult >;
	/** Puts the cursor in the composer, for the model typed by hand. */
	onTypeModel: () => void;
}

function rowStatus( row: PartsRow, asked: boolean ) {
	switch ( row.status ) {
		case 'matched':
			return sprintf(
				// translators: %s is our model name, as the product titles write it.
				__( 'In our range: %s', 'linker-tools' ),
				row.label ?? ''
			);
		case 'missing':
			return __( 'Not in our range.', 'linker-tools' );
		case 'skipped':
			return __( 'Skipped.', 'linker-tools' );
		case 'uncertain':
			return asked
				? __( 'Which model does this line mean?', 'linker-tools' )
				: __( 'This line needs your confirmation.', 'linker-tools' );
	}
}

export function PartsCard( {
	block,
	onAsk,
	onAdd,
	onTypeModel,
}: { block: PartsBlock } & PartsActions ) {
	const [ phase, setPhase ] = useState< 'idle' | 'sending' | PartsAddResult >(
		'idle'
	);

	async function add() {
		// A failed write can be tried again: every other state is final (or
		// already running) for this card.
		if (
			! block.add ||
			phase === 'sending' ||
			phase === 'added' ||
			phase === 'unverified'
		) {
			return;
		}
		setPhase( 'sending' );
		try {
			setPhase( await onAdd( block.add.items ) );
		} catch {
			setPhase( 'retry' );
		}
	}

	const addText = ( () => {
		switch ( phase ) {
			case 'sending':
				return __( 'Adding…', 'linker-tools' );
			case 'added':
				return __( 'In your solution draft.', 'linker-tools' );
			case 'unverified':
				return __(
					'Sent, but the solution draft does not show the change yet.',
					'linker-tools'
				);
			case 'retry':
				return __(
					'Not everything was added. Try again.',
					'linker-tools'
				);
			default:
				return block.add && block.add.products === 1
					? __(
							'Add the product to the solution draft',
							'linker-tools'
						)
					: sprintf(
							// translators: %d is the number of distinct products.
							__(
								'Add %d products to the solution draft',
								'linker-tools'
							),
							block.add?.products ?? 0
						);
		}
	} )();

	return (
		<div
			className="linker-genie-parts"
			role="group"
			aria-label={ __( 'Your parts list', 'linker-tools' ) }
		>
			<p className="linker-genie-parts__title">
				{ __( 'Your parts list', 'linker-tools' ) }
			</p>
			<ol className="linker-genie-parts__rows">
				{ block.rows.map( ( row ) => (
					<li
						key={ row.line }
						className={ `linker-genie-parts__row linker-genie-parts__row--${ row.status }` }
					>
						<div className="linker-genie-parts__line">
							<span
								className="linker-genie-parts__number"
								aria-hidden="true"
							>
								{ row.line }
							</span>
							<span className="linker-genie-parts__quantity">
								{ sprintf(
									// translators: %d is how many of this product the customer listed.
									__( '%d ×', 'linker-tools' ),
									row.quantity
								) }
							</span>
							<span className="linker-genie-parts__text">
								{ row.text }
							</span>
						</div>
						<p className="linker-genie-parts__status">
							{ rowStatus( row, row.line === block.ask_line ) }
						</p>
						{ row.status === 'uncertain' &&
						row.line === block.ask_line ? (
							<div className="linker-genie-parts__actions">
								{ ( row.options ?? [] ).map( ( option ) => (
									<button
										key={ option.product_id }
										type="button"
										className="linker-genie-app__prompt"
										onClick={ () =>
											onAsk(
												sprintf(
													// translators: 1: the line's number, 2: our model name.
													__(
														'Row %1$d: %2$s',
														'linker-tools'
													),
													row.line,
													option.label
												)
											)
										}
									>
										{ option.label }
									</button>
								) ) }
								<button
									type="button"
									className="linker-genie-app__prompt"
									onClick={ onTypeModel }
								>
									{ __( 'Type the model', 'linker-tools' ) }
								</button>
								<button
									type="button"
									className="linker-genie-app__prompt"
									onClick={ () =>
										onAsk(
											sprintf(
												// translators: %d is the line's number.
												__(
													'Row %d: skip',
													'linker-tools'
												),
												row.line
											)
										)
									}
								>
									{ __( 'Skip this line', 'linker-tools' ) }
								</button>
							</div>
						) : null }
					</li>
				) ) }
			</ol>
			{ block.add ? (
				<div className="linker-genie-parts__add">
					<button
						type="button"
						className="linker-genie-app__action"
						aria-busy={ phase === 'sending' || undefined }
						onClick={ add }
						disabled={
							phase === 'sending' ||
							phase === 'added' ||
							phase === 'unverified'
						}
					>
						{ addText }
					</button>
				</div>
			) : null }
		</div>
	);
}
