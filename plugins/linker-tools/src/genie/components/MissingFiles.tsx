/** Existing file-reselection controls shared by both owned editors. */
import { __, sprintf } from '@wordpress/i18n';
interface Props {
	names: readonly string[];
	remove: ( name: string ) => void;
	choose: () => void;
}
export function MissingFiles( { names, remove, choose }: Props ) {
	if ( ! names.length ) {
		return null;
	}
	return (
		<div className="linker-genie-app__refused">
			{ names.map( ( name ) => (
				<p key={ name }>
					{ sprintf(
						// translators: %s is the name of a file that must be selected again.
						__( 'Select %s again before sending.', 'linker-tools' ),
						name
					) }{ ' ' }
					<button
						type="button"
						className="linker-genie-app__prompt"
						onClick={ () => remove( name ) }
					>
						{ __( 'Remove', 'linker-tools' ) }
					</button>
				</p>
			) ) }
			<button
				type="button"
				className="linker-genie-app__prompt"
				onClick={ choose }
			>
				{ __( 'Choose a file', 'linker-tools' ) }
			</button>
		</div>
	);
}
