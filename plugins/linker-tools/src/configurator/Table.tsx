/**
 * A table on wide screens, one block per row on phones: each cell then shows
 * its column's name (data-label, configurator.css). The installer's scope, the
 * Stückliste of the report and the C&I cap options use it.
 */

/* eslint-disable jsx-a11y/no-redundant-roles, jsx-a11y/no-interactive-element-to-noninteractive-role --
   The phone layout changes the display of the table elements, and WebKit then
   drops their implicit roles; the explicit roles (the elements' own) keep the
   table a table for screen readers. */

/**
 * External dependencies
 */
import type { ReactNode } from 'react';

export interface TableColumn {
	label: string;
	/** Read by screen readers only (an action column, for example). */
	hidden?: boolean;
	numeric?: boolean;
}

export interface TableProps {
	caption?: string;
	columns: TableColumn[];
	rows: { key: string; cells: ReactNode[] }[];
}

function isEmpty( cell: ReactNode ): boolean {
	return (
		cell === null ||
		cell === undefined ||
		cell === '' ||
		( Array.isArray( cell ) && cell.length === 0 )
	);
}

function classes( ...names: ( string | false )[] ): string | undefined {
	return names.filter( Boolean ).join( ' ' ) || undefined;
}

export function Table( { caption, columns, rows }: TableProps ) {
	return (
		<table className="linker-table" role="table">
			{ caption ? <caption>{ caption }</caption> : null }
			<thead role="rowgroup">
				<tr role="row">
					{ columns.map( ( column ) => (
						<th
							key={ column.label }
							scope="col"
							role="columnheader"
							className={ classes(
								!! column.numeric && 'linker-table__number'
							) }
						>
							{ column.hidden ? (
								<span className="linker-sr-only">
									{ column.label }
								</span>
							) : (
								column.label
							) }
						</th>
					) ) }
				</tr>
			</thead>
			<tbody role="rowgroup">
				{ rows.map( ( row ) => (
					<tr key={ row.key } role="row">
						{ row.cells.map( ( cell, index ) => (
							<td
								key={ columns[ index ].label }
								role="cell"
								className={ classes(
									!! columns[ index ].numeric &&
										'linker-table__number',
									// Hidden on phones, where the cell is a labelled line.
									isEmpty( cell ) && 'linker-table__empty'
								) }
								data-label={
									columns[ index ].hidden
										? undefined
										: columns[ index ].label
								}
							>
								{ /* One element: on phones the label sits beside it. */ }
								<span className="linker-table__value">
									{ cell }
								</span>
							</td>
						) ) }
					</tr>
				) ) }
			</tbody>
		</table>
	);
}
