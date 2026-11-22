/** The catalogue may include the manufacturer in its series name. */
export function brandSeries(
	brand: string | null,
	series: string | null
): string {
	const short =
		brand && series?.startsWith( brand + ' ' )
			? series.slice( brand.length + 1 )
			: series;
	return [ brand, short ].filter( Boolean ).join( ' · ' );
}
