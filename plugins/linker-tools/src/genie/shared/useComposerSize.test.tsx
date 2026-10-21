// @vitest-environment jsdom
/** The real hook sees actual ref replacement, opening, width and font events. */
import { act, render, screen, cleanup } from '@testing-library/react';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { useComposerSize } from './useComposerSize';
let width = 200;
let lineHeight = 24;
const watching: Array< {
	callback: ResizeObserverCallback;
	disconnect: ReturnType< typeof vi.fn >;
} > = [];
let fontDescriptor: PropertyDescriptor | undefined;
function Editor( {
	value = 'A long restored schematic question',
	visible = true,
	mounted = true,
}: {
	value?: string;
	visible?: boolean;
	mounted?: boolean;
} ) {
	const { ref } = useComposerSize( value, visible );
	return mounted ? (
		<textarea
			aria-label="Draft"
			ref={ ref }
			value={ value }
			readOnly
			style={ { display: visible ? 'block' : 'none' } }
		/>
	) : null;
}
beforeEach( () => {
	width = 200;
	lineHeight = 24;
	watching.length = 0;
	fontDescriptor = Object.getOwnPropertyDescriptor( document, 'fonts' );
	vi.spyOn(
		HTMLTextAreaElement.prototype,
		'getBoundingClientRect'
	).mockImplementation( function ( this: HTMLTextAreaElement ) {
		return { width: this.style.display === 'none' ? 0 : width } as DOMRect;
	} );
	vi.spyOn(
		HTMLTextAreaElement.prototype,
		'scrollHeight',
		'get'
	).mockImplementation( function ( this: HTMLTextAreaElement ) {
		return (
			Math.max(
				this.value.split( '\n' ).length,
				width < 250 && this.value.length > 25 ? 2 : 1
			) * lineHeight
		);
	} );
	vi.stubGlobal(
		'ResizeObserver',
		class {
			disconnect = vi.fn();
			observe = vi.fn();
			unobserve = vi.fn();
			constructor( callback: ResizeObserverCallback ) {
				watching.push( { callback, disconnect: this.disconnect } );
			}
		}
	);
} );
afterEach( () => {
	cleanup();
	vi.restoreAllMocks();
	vi.unstubAllGlobals();
	if ( fontDescriptor ) {
		Object.defineProperty( document, 'fonts', fontDescriptor );
	} else {
		delete ( document as unknown as { fonts?: unknown } ).fonts;
	}
} );
test( 'a restored unchanged value is measured when its hidden panel opens', () => {
	const view = render( <Editor visible={ false } /> );
	expect( screen.getByLabelText( 'Draft' ).style.height ).toBe( '' );
	view.rerender( <Editor visible /> );
	expect( screen.getByLabelText( 'Draft' ).style.height ).toBe( '48px' );
} );
test( 'a field remounted with the same value is measured and the old observer is synchronously disconnected', () => {
	const view = render( <Editor /> );
	const original = screen.getByLabelText( 'Draft' );
	const old = watching.at( -1 )!;
	view.rerender( <Editor mounted={ false } /> );
	expect( old.disconnect ).toHaveBeenCalled();
	view.rerender( <Editor /> );
	expect( screen.getByLabelText( 'Draft' ) ).not.toBe( original );
	expect( screen.getByLabelText( 'Draft' ).style.height ).toBe( '48px' );
} );
test( 'width changes remeasure, height-only notifications do not loop, and eight lines scroll at the existing limit', () => {
	width = 350;
	const view = render( <Editor /> );
	const field = screen.getByLabelText< HTMLTextAreaElement >( 'Draft' );
	expect( field.style.height ).toBe( '24px' );
	width = 200;
	act( () => watching.at( -1 )!.callback( [], {} as ResizeObserver ) );
	expect( field.style.height ).toBe( '48px' );
	const height = vi.spyOn( field.style, 'height', 'set' );
	act( () => watching.at( -1 )!.callback( [], {} as ResizeObserver ) );
	expect( height ).not.toHaveBeenCalled();
	view.rerender(
		<Editor
			value={ Array.from( { length: 8 }, () => 'line' ).join( '\n' ) }
		/>
	);
	expect( field.style.height ).toBe( '144px' );
	expect( field.style.overflowY ).toBe( 'auto' );
} );
test( 'font readiness and loading completion remeasure while mounted, with no stale measurement after unmount', async () => {
	let ready!: () => void;
	const fonts = Object.assign( new EventTarget(), {
		ready: new Promise< void >( ( resolve ) => {
			ready = resolve;
		} ),
	} );
	Object.defineProperty( document, 'fonts', {
		configurable: true,
		value: fonts,
	} );
	const view = render( <Editor /> );
	const field = screen.getByLabelText< HTMLTextAreaElement >( 'Draft' );
	lineHeight = 30;
	await act( async () => ready() );
	expect( field.style.height ).toBe( '60px' );
	lineHeight = 24;
	act( () => fonts.dispatchEvent( new Event( 'loadingdone' ) ) );
	expect( field.style.height ).toBe( '48px' );
	view.unmount();
	const height = vi.spyOn( field.style, 'height', 'set' );
	act( () => fonts.dispatchEvent( new Event( 'loadingdone' ) ) );
	expect( height ).not.toHaveBeenCalled();
} );
