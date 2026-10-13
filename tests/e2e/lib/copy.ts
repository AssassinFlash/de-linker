/**
 * Page-copy helpers for the suite's assertions.
 */

/**
 * The page text without the freight estimate's amounts: the estimate is
 * logistics information the live page shows to guests and pending accounts
 * too (measured 2026-10-13), so it is never what the price gate covers. The
 * German page renders the amounts before the sign ("39,00 €").
 */
export function withoutFreightEstimate(text: string): string {
	return text
		.replace(/Germany delivery estimate:[^·]*/i, '')
		.replace(/Voraussichtliche Lieferung[^·]*/i, '');
}
