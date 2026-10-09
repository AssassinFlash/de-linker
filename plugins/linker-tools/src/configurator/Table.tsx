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

export function Table( { caption, columns, rows }: TableProps ) {
	const kind = ( column: TableColumn ) =>
		column.numeric ? 'linker-table__number' : undefined;
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
							className={ kind( column ) }
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
								className={ kind( columns[ index ] ) }
								data-label={
									columns[ index ].hidden
										? undefined
										: columns[ index ].label
								}
							>
								{ cell }
							</td>
						) ) }
					</tr>
				) ) }
			</tbody>
		</table>
	);
}
