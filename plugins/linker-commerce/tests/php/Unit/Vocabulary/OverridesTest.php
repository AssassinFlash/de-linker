<?php
/**
 * Tests for applying the site's words.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Vocabulary;

use Linker\Commerce\Tests\TestCase;
use Linker\Commerce\Vocabulary\Overrides;
use Linker\Commerce\Vocabulary\Terms;
use WP_Mock;

/**
 * Tests for Overrides, with the real vocabulary.
 *
 * @covers \Linker\Commerce\Vocabulary\Overrides
 */
final class OverridesTest extends TestCase {

	/**
	 * What this plugin's translation appends to a source string, to tell languages apart.
	 *
	 * @var string
	 */
	private string $language = ' [de]';

	/**
	 * This plugin's translations append the current "language"; init has run.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::userFunction( '__', array( 'return' => fn ( string $text ): string => $text . $this->language ) );
		WP_Mock::userFunction(
			'_n_noop',
			array(
				'return' => static fn ( string $singular, string $plural, string $domain ): array => array(
					'singular' => $singular,
					'plural'   => $plural,
					'domain'   => $domain,
				),
			)
		);
		WP_Mock::userFunction( 'did_action', array( 'return' => 1 ) );
	}

	/**
	 * Replaced strings get the site's word in the current language; other strings keep WooCommerce's translation.
	 */
	public function test_gettext(): void {
		$overrides = new Overrides( new Terms() );

		$this->assertSame( 'Add to solution draft [de]', $overrides->gettext( 'In den Warenkorb', 'Add to cart' ) );
		$this->assertSame( 'Zwischensumme', $overrides->gettext( 'Zwischensumme', 'Subtotal' ) );
		$this->assertSame( 'Fertiggestellt', $overrides->gettext_with_context( 'Fertiggestellt', 'Completed', 'Order status' ) );
	}

	/**
	 * Plural strings are translated through the plugin's nooped plural with the same number.
	 */
	public function test_ngettext(): void {
		WP_Mock::userFunction(
			'translate_nooped_plural',
			array(
				'times'  => 1,
				'args'   => array(
					array(
						'singular' => '%1$s (%2$s unit)',
						'plural'   => '%1$s (%2$s units)',
						'domain'   => 'linker-commerce',
					),
					3,
					'linker-commerce',
				),
				'return' => '%1$s (%2$s Stück)',
			)
		);
		$overrides = new Overrides( new Terms() );

		$this->assertSame( '%1$s (%2$s Stück)', $overrides->ngettext( '%1$s für %2$s Artikel', '%1$s for %2$s item', '%1$s for %2$s items', 3 ) );
		$this->assertSame( 'x', $overrides->ngettext( 'x', 'Other', 'Others', 3 ) );
	}

	/**
	 * The replacements are built once per language and built again after a language switch.
	 */
	public function test_replacements_follow_the_language(): void {
		$overrides = new Overrides( new Terms() );

		$this->assertSame( 'Solution draft updated. [de]', $overrides->gettext( 'Warenkorb aktualisiert.', 'Cart updated.' ) );
		$this->language = ' [en]';
		$this->assertSame( 'Solution draft updated. [de]', $overrides->gettext( 'Cart updated.', 'Cart updated.' ) );
		$overrides->reset();
		$this->assertSame( 'Solution draft updated. [en]', $overrides->gettext( 'Cart updated.', 'Cart updated.' ) );
	}

	/**
	 * Before init, when this plugin's translations are not registered yet, nothing is replaced.
	 *
	 * @runInSeparateProcess
	 * @preserveGlobalState disabled
	 */
	public function test_nothing_is_replaced_before_init(): void {
		WP_Mock::userFunction(
			'did_action',
			array(
				'args'   => array( 'init' ),
				'return' => 0,
			)
		);

		$this->assertSame( 'Warenkorb', ( new Overrides( new Terms() ) )->gettext( 'Warenkorb', 'Cart' ) );
	}
}
