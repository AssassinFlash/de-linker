/**
 * Display the manufacturer once when the catalogue includes it in the series name.
 *
 * @param brand  Manufacturer name from the catalogue.
 * @param series Published series name.
 */
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
