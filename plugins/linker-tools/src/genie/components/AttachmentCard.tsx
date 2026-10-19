/**
 * What Genie read from a file the customer attached (#236): a nameplate with
 * the products it matched and the way to confirm, a document with the pages
 * read, or why nothing could be read.
 *
 * The match is the service's, decided by our product data (services/genie
 * nameplate.py); the card only words it. Confirming sends an ordinary message
 * that names the model, so the next turn goes to the product or what works
 * with it by the usual route. "Type the model" is the way out when the photo
 * was misread or could not be read.
 */

/**
 * WordPress dependencies
 */
import { __, _n, sprintf } from '@wordpress/i18n';

/**
 * Internal dependencies
 */
import type { AttachmentCard as Card } from '../api/turn';

export interface AttachmentActions {
	/** Sends a message as the customer. */
	onAsk: ( message: string ) => void;
	/** Puts the model's opening words in the field and focuses it. */
	onTypeModel: () => void;
	/** Opens the file picker for another photo. */
	onPhoto: () => void;
}

/**
 * The model as the customer names it: with its brand when the label lacks it.
 *
 * @param brand The brand read from the nameplate.
 * @param label The model as our products write it.
 */
export function deviceName( brand: string | null | undefined, label: string ) {
	if ( ! brand || label.toLowerCase().startsWith( brand.toLowerCase() ) ) {
		return label;
	}
	return `${ brand } ${ label }`;
}

export function AttachmentCard( {
	card,
	onAsk,
	onTypeModel,
	onPhoto,
}: { card: Card } & AttachmentActions ) {
	if ( card.failed ) {
		return (
			<div className="linker-genie-attachment" role="status">
				<p className="linker-genie-attachment__status">
					{ sprintf(
						// translators: %s is the name of the file the customer attached.
						__( '%s could not be read.', 'linker-tools' ),
						card.name
					) }
				</p>
				{ 'document' === card.kind ? null : (
					<div className="linker-genie-attachment__actions">
						<button
							type="button"
							className="linker-genie-app__prompt"
							onClick={ onPhoto }
						>
							{ 'list' === card.kind
								? __( 'Choose a file', 'linker-tools' )
								: __( 'Choose another photo', 'linker-tools' ) }
						</button>
					</div>
				) }
			</div>
		);
	}
	if ( 'nameplate' !== card.kind || ! card.match ) {
		return (
			<div className="linker-genie-attachment" role="status">
				<p className="linker-genie-attachment__status">
					{ card.pages
						? sprintf(
								// translators: 1: the file's name, 2: pages read, 3: pages in the file.
								_n(
									'Read: %1$s (%2$d of %3$d page)',
									'Read: %1$s (%2$d of %3$d pages)',
									card.pages,
									'linker-tools'
								),
								card.name,
								card.pages_read ?? 0,
								card.pages
							)
						: sprintf(
								// translators: %s is the name of the file the customer attached.
								__( 'Read: %s', 'linker-tools' ),
								card.name
							) }
				</p>
			</div>
		);
	}
	const products = card.products ?? [];
	const exact = 'exact' === card.match ? products[ 0 ] : undefined;
	return (
		<div className="linker-genie-attachment linker-genie-attachment--nameplate">
			<p className="linker-genie-attachment__title">
				{ __( 'Read from your nameplate photo', 'linker-tools' ) }
			</p>
			{ card.brand || card.model || card.product_type ? (
				<dl className="linker-genie-attachment__facts">
					{ card.brand ? (
						<div>
							<dt>{ __( 'Brand', 'linker-tools' ) }</dt>
							<dd>{ card.brand }</dd>
						</div>
					) : null }
					{ card.model ? (
						<div>
							<dt>{ __( 'Model', 'linker-tools' ) }</dt>
							<dd>{ card.model }</dd>
						</div>
					) : null }
					{ card.product_type ? (
						<div>
							<dt>{ __( 'Device', 'linker-tools' ) }</dt>
							<dd>{ card.product_type }</dd>
						</div>
					) : null }
				</dl>
			) : null }
			<p className="linker-genie-attachment__status" role="status">
				{ exact
					? sprintf(
							// translators: %s is one of our models, e.g. "SAJ H2-10K-T3".
							__(
								'In our range: %s. Is this your device?',
								'linker-tools'
							),
							deviceName( card.brand, exact.label )
						)
					: {
							exact: '',
							partial: __(
								'No exact match. Is it one of these?',
								'linker-tools'
							),
							none: __(
								'This model is not in our product range.',
								'linker-tools'
							),
							unreadable: __(
								'The model could not be read.',
								'linker-tools'
							),
						}[ card.match ] }
			</p>
			<div className="linker-genie-attachment__actions">
				{ exact ? (
					<>
						<button
							type="button"
							className="linker-genie-app__prompt"
							onClick={ () =>
								onAsk(
									sprintf(
										// translators: %s is the confirmed model, e.g. "SAJ H2-10K-T3".
										__(
											"Yes, it's the %s. Show me its documents.",
											'linker-tools'
										),
										deviceName( card.brand, exact.label )
									)
								)
							}
						>
							{ __( 'Yes, show its documents', 'linker-tools' ) }
						</button>
						<button
							type="button"
							className="linker-genie-app__prompt"
							onClick={ () =>
								onAsk(
									sprintf(
										// translators: %s is the confirmed model, e.g. "SAJ H2-10K-T3".
										__(
											"Yes, it's the %s. What works with it?",
											'linker-tools'
										),
										deviceName( card.brand, exact.label )
									)
								)
							}
						>
							{ __( 'Yes, what works with it?', 'linker-tools' ) }
						</button>
					</>
				) : null }
				{ 'partial' === card.match
					? products.map( ( product ) => (
							<button
								key={ product.product_id }
								type="button"
								className="linker-genie-app__prompt"
								onClick={ () =>
									onAsk(
										sprintf(
											// translators: %s is the chosen model, e.g. "SAJ H2-10K-T3".
											__(
												"It's the %s.",
												'linker-tools'
											),
											deviceName(
												card.brand,
												product.label
											)
										)
									)
								}
							>
								{ sprintf(
									// translators: %s is one of our models, e.g. "H2-10K-T3".
									__( "It's the %s", 'linker-tools' ),
									product.label
								) }
							</button>
						) )
					: null }
				{ 'unreadable' === card.match ? (
					<button
						type="button"
						className="linker-genie-app__prompt"
						onClick={ onPhoto }
					>
						{ __( 'Choose another photo', 'linker-tools' ) }
					</button>
				) : null }
				<button
					type="button"
					className="linker-genie-app__prompt"
					onClick={ onTypeModel }
				>
					{ exact
						? __( 'No, type the model', 'linker-tools' )
						: __( 'Type the model', 'linker-tools' ) }
				</button>
			</div>
		</div>
	);
}
