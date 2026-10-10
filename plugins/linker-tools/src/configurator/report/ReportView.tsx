/**
 * The design report under the solution, and its PDF with the installer's logo.
 */

/**
 * WordPress dependencies
 */
import { useState } from '@wordpress/element';
import { __, sprintf } from '@wordpress/i18n';

/**
 * Internal dependencies
 */
import type { EngineClient } from '../api/engine';
import { FilePicker } from '../FilePicker';
import { Table } from '../Table';
import type { Report, ResidentialInput } from '../types';

const LOGO_BYTES = 500 * 1024; // the engine accepts data URLs up to about 700 kB of text

type PdfState = 'idle' | 'working' | 'failed';

export interface ReportViewProps {
	report: Report;
	input: ResidentialInput;
	engine: EngineClient;
}

function readLogo( file: File ): Promise< string > {
	return new Promise( ( resolve, reject ) => {
		const reader = new FileReader();
		reader.onload = () => resolve( String( reader.result ) );
		reader.onerror = () => reject( reader.error );
		reader.readAsDataURL( file );
	} );
}

export function ReportView( { report, input, engine }: ReportViewProps ) {
	const [ logo, setLogo ] = useState< { name: string; data: string } | null >(
		null
	);
	const [ logoError, setLogoError ] = useState( '' );
	const [ pdf, setPdf ] = useState< PdfState >( 'idle' );

	async function chooseLogo( file: File | undefined ) {
		setLogoError( '' );
		if ( ! file ) {
			setLogo( null );
			return;
		}
		if ( ! [ 'image/png', 'image/jpeg' ].includes( file.type ) ) {
			setLogoError( __( 'Choose a PNG or JPEG file.', 'linker-tools' ) );
			return;
		}
		if ( file.size > LOGO_BYTES ) {
			setLogoError(
				__( 'Choose a logo of at most 500 kB.', 'linker-tools' )
			);
			return;
		}
		setLogo( { name: file.name, data: await readLogo( file ) } );
	}

	async function download() {
		setPdf( 'working' );
		try {
			const blob = await engine.reportPdf( input, logo?.data ?? null );
			const url = URL.createObjectURL( blob );
			const link = document.createElement( 'a' );
			link.href = url;
			link.download = `linker-design-report-${ input.plz }-${ input.locale }.pdf`;
			link.click();
			URL.revokeObjectURL( url );
			setPdf( 'idle' );
		} catch {
			setPdf( 'failed' );
		}
	}

	return (
		<div className="linker-report">
			<div className="linker-report__tools">
				<FilePicker
					id="linker-logo"
					label={ __(
						'Your logo on the PDF (optional)',
						'linker-tools'
					) }
					button={ __( 'Choose logo', 'linker-tools' ) }
					accept="image/png,image/jpeg"
					chosen={
						logo?.name ?? __( 'No logo chosen', 'linker-tools' )
					}
					hint={ __(
						'PNG or JPEG, at most 500 kB.',
						'linker-tools'
					) }
					error={ logoError }
					onChoose={ chooseLogo }
				/>
				{ logo ? (
					<img
						className="linker-report__logo"
						src={ logo.data }
						alt={ __( 'Your logo', 'linker-tools' ) }
					/>
				) : null }
				<div className="linker-report__download">
					<button
						type="button"
						className="linker-button linker-button--primary"
						onClick={ download }
						disabled={ pdf === 'working' }
						aria-busy={ pdf === 'working' }
					>
						{ pdf === 'working'
							? __( 'Preparing PDF…', 'linker-tools' )
							: __( 'Download PDF', 'linker-tools' ) }
					</button>
					<p className="linker-report__status" role="status">
						{ pdf === 'failed'
							? __(
									'The PDF could not be created. Try again.',
									'linker-tools'
								)
							: '' }
					</p>
				</div>
			</div>
			<p className="linker-report__meta">
				{ sprintf(
					/* translators: 1: report title, 2: date and time */
					__( '%1$s, %2$s', 'linker-tools' ),
					report.subtitle,
					report.generated_at
						.replace( 'T', ' ' )
						.replace( 'Z', ' UTC' )
				) }
			</p>
			{ report.sections.map( ( section ) => (
				<section
					key={ section.id }
					className="linker-report__section"
					aria-labelledby={ `linker-report-${ section.id }` }
				>
					<h4 id={ `linker-report-${ section.id }` }>
						{ section.title }
					</h4>
					{ section.rows.length > 0 ? (
						<dl className="linker-report__rows">
							{ section.rows.map( ( row, index ) => (
								<div key={ `${ row.label }-${ index }` }>
									<dt>{ row.label }</dt>
									<dd>
										{ row.href ? (
											<a href={ row.href }>
												{ row.value }
											</a>
										) : (
											row.value
										) }
									</dd>
								</div>
							) ) }
						</dl>
					) : null }
					{ section.table ? (
						<Table
							columns={ section.table.columns.map(
								( label ) => ( { label } )
							) }
							rows={ section.table.rows.map(
								( cells, index ) => ( {
									key: String( index ),
									cells,
								} )
							) }
						/>
					) : null }
					{ section.paragraphs.map( ( text ) => (
						<p key={ text }>{ text }</p>
					) ) }
				</section>
			) ) }
		</div>
	);
}
