/**
 * Style sheets imported for their side effect; the build extracts them to
 * build/<entry>.css.
 */
declare module '*.css';

/**
 * Text files imported as a string (Vite's `?raw`), in stories and tests only.
 */
declare module '*?raw' {
	const text: string;
	export default text;
}
