/**
 * The files picked for the next turn, over the composer (#236): each with
 * its name, "Preparing file…" while it is read or redrawn, or why it will not be
 * sent; each can be taken out again.
 */

/**
 * WordPress dependencies
 */
import { __, _n, sprintf } from '@wordpress/i18n';

/**
 * Internal dependencies
 */
import { MAX_FILES, MAX_PDF_BYTES } from '../attachments/prepare';
import type { PickRefusal, Picked } from '../attachments/useAttachments';
import { CloseIcon } from './Icons';

const MEBIBYTE = 1024 * 1024;

/**
 * Why a file is not sent, in the customer's words. The proxy's refusals
 * (`linker_genie_attachment_<reason>`) read the same.
 *
 * @param reason The refusal.
 */
export function refusalText( reason: PickRefusal | 'throttled' ): string {
	switch ( reason ) {
		case 'type':
			return __(
				'This file type cannot be sent. Genie reads photos (JPEG, PNG, WebP or HEIC) and PDFs.',
				'linker-tools'
			);
		case 'size':
		case 'turn_size':
			return sprintf(
				// translators: %d is the largest PDF in megabytes.
				__(
					'This file is too large. A PDF can be up to %d MB.',
					'linker-tools'
				),
				MAX_PDF_BYTES / MEBIBYTE
			);
		case 'heic':
			return __(
				'This browser cannot open HEIC photos. Please attach the photo as a JPEG.',
				'linker-tools'
			);
		case 'unreadable':
			return __(
				'This photo could not be opened. Please choose another one.',
				'linker-tools'
			);
		case 'count':
			return sprintf(
				// translators: %d is the number of files one message can carry.
				_n(
					'You can attach up to %d file at a time.',
					'You can attach up to %d files at a time.',
					MAX_FILES,
					'linker-tools'
				),
				MAX_FILES
			);
		case 'throttled':
			return __(
				'You have reached the hourly limit for files. Please try again later; typed questions still work.',
				'linker-tools'
			);
	}
}

export function AttachmentChips( {
	picked,
	onRemove,
}: {
	picked: Picked[];
	onRemove: ( key: number ) => void;
} ) {
	if ( picked.length === 0 ) {
		return null;
	}
	return (
		<ul className="linker-genie-app__attachments">
			{ picked.map( ( item ) => (
				<li
					key={ item.key }
					className={ `linker-genie-app__attachment${
						item.state === 'refused'
							? ' linker-genie-app__attachment--refused'
							: ''
					}` }
				>
					<span className="linker-genie-app__attachment-name">
						{ item.name }
					</span>
					{ item.state === 'preparing' ? (
						<span
							className="linker-genie-app__attachment-state"
							role="status"
						>
							{ __( 'Preparing file…', 'linker-tools' ) }
						</span>
					) : null }
					{ item.state === 'refused' && item.reason ? (
						<span
							className="linker-genie-app__attachment-state"
							role="alert"
						>
							{ refusalText( item.reason ) }
						</span>
					) : null }
					<button
						type="button"
						className="linker-genie-app__attachment-remove"
						aria-label={
							// translators: %s is the attached file's name.
							__(
								'Remove attachment %s',
								'linker-tools'
							).replace( '%s', item.name )
						}
						onClick={ () => onRemove( item.key ) }
					>
						<CloseIcon size={ 14 } />
					</button>
				</li>
			) ) }
		</ul>
	);
}
