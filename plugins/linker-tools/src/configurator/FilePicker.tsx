/**
 * A file field in the site's button style, with the chosen file's name beside
 * it in the page's language (the browser's own control words "Choose file" in
 * the browser's language). The native input stays in the page, visually
 * hidden, for the keyboard and screen readers; it carries the field's label.
 */

export interface FilePickerProps {
	id: string;
	label: string;
	/** The button's text, for example "Choose file". */
	button: string;
	accept: string;
	/** The chosen file's name, or the text for none. */
	chosen: string;
	hint?: string;
	error?: string;
	onChoose: ( file: File | undefined ) => void;
}

export function FilePicker( {
	id,
	label,
	button,
	accept,
	chosen,
	hint,
	error,
	onChoose,
}: FilePickerProps ) {
	const described = [ hint ? `${ id }-hint` : '', `${ id }-error` ]
		.filter( Boolean )
		.join( ' ' );
	return (
		<div
			className={ `linker-field${ error ? ' linker-field--error' : '' }` }
		>
			<p className="linker-field__label" id={ `${ id }-label` }>
				{ label }
			</p>
			<div className="linker-file">
				<input
					id={ id }
					type="file"
					className="linker-file__input"
					accept={ accept }
					aria-labelledby={ `${ id }-label` }
					aria-describedby={ described }
					aria-invalid={ error ? true : undefined }
					onChange={ ( event ) =>
						onChoose( event.target.files?.[ 0 ] )
					}
				/>
				<label
					htmlFor={ id }
					className="linker-button linker-button--secondary linker-file__button"
				>
					{ button }
				</label>
				<span className="linker-file__name">{ chosen }</span>
			</div>
			{ hint ? (
				<p className="linker-field__hint" id={ `${ id }-hint` }>
					{ hint }
				</p>
			) : null }
			<p
				className="linker-field__error"
				id={ `${ id }-error` }
				role="alert"
			>
				{ error ?? '' }
			</p>
		</div>
	);
}
