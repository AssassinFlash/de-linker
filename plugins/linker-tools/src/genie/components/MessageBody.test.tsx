/** Answer formatting is observed through rendered, safe semantic content. */
import { render, screen } from '@testing-library/react';
import { expect, test } from 'vitest';
import { MessageBody } from './MessageBody';

test( 'an answer preserves paragraphs, emphasis and a semantic list', () => {
	render(
		<MessageBody
			text={
				'Choose the **hybrid inverter**.\n\nCheck these details:\n\n- Phase\n- Battery compatibility'
			}
		/>
	);
	expect( screen.getByText( 'hybrid inverter' ).tagName ).toBe( 'STRONG' );
	expect( screen.getByRole( 'list' ).children ).toHaveLength( 2 );
	expect( screen.getByText( 'Check these details:' ).tagName ).toBe( 'P' );
} );

test( 'model text cannot load an image, create a destination or execute raw HTML', () => {
	const { container } = render(
		<MessageBody
			text={
				'<script>alert(1)</script>\n\n[Source](https://example.com) ![Image](https://example.com/a.png)'
			}
		/>
	);
	expect( container.querySelector( 'script, img, a' ) ).toBeNull();
	expect( screen.getByText( '<script>alert(1)</script>' ) ).toBeVisible();
	expect( screen.getByText( 'Source' ) ).toBeVisible();
} );

test( 'long plain prose has reading paragraphs without rewriting any words', () => {
	const original =
		'Auf der Produktseite können Sie die Produkte über die Filter nach Kategorie, Anwendung, Marke, Phase, Leistung und nutzbarer Energie eingrenzen. Sicherer wird die Auswahl über den Lösungskonfigurator: Er plant aus Ihren Standortdaten ein Speichersystem und erzeugt daraus einen Lösungsentwurf, den Sie als Anfrage senden können. Wie groß Speicher und Wechselrichter für Ihr Projekt ausfallen sollen, ermittelt der Lösungskonfigurator für Sie – dort schlagen wir Ihnen die passenden Produkte vor.';
	const { container } = render(
		<MessageBody text={ original } locale="de" />
	);
	expect( container.querySelectorAll( 'p' ) ).toHaveLength( 3 );
	expect( container.querySelector( 'p' ) ).toHaveTextContent(
		'Auf der Produktseite können Sie die Produkte über die Filter nach Kategorie, Anwendung, Marke, Phase, Leistung und nutzbarer Energie eingrenzen.'
	);
	expect( container.textContent!.replace( /\s+/g, ' ' ).trim() ).toBe(
		original
	);
} );
