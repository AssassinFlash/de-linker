<?php
/**
 * The retired addresses on the real site.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Integration;

/**
 * The retired addresses of the live catalogue and of this site's own history,
 * driven against a local instance carrying the live snapshot: real withdrawn
 * products, real retired shelves, the real checkout page — and the addresses
 * that must keep answering for themselves.
 *
 * @covers \Linker\Tools\Redirects
 */
final class RedirectsTest extends SiteTestCase {

	/**
	 * A withdrawn product of the live catalogue goes to the shelf of its line.
	 */
	public function test_a_withdrawn_product_goes_to_the_shelf_of_its_line(): void {
		$this->assertRedirects( '/product/pylontech-force-h2-system-7-1/', '/product-category/home-storage/' );
	}

	/**
	 * The German address of a withdrawn product — the same slug under the
	 * German base — lands on the German shelf, not on the English one.
	 */
	public function test_a_german_product_address_lands_on_the_german_shelf(): void {
		$this->assertRedirects( '/de/produkt/pylontech-force-h2-system-7-1/', '/de/produkt-kategorie/heimspeicher/' );
	}

	/**
	 * A withdrawn product that was replaced goes to its replacement, in both
	 * languages.
	 */
	public function test_a_replaced_product_goes_to_its_replacement(): void {
		$this->assertRedirects( '/product/saj-b2-5-0-hv5/', '/product/saj-b2-5-0-hv1/' );
		$this->assertRedirects( '/de/produkt/saj-b2-5-0-hv5/', '/de/produkt/saj-b2-5-0-hv1/' );
	}

	/**
	 * A product the catalogue sells is served again — the map never shadows a
	 * published product.
	 */
	public function test_a_product_the_catalogue_sells_is_served(): void {
		$this->assertStays( '/product/goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh/', 200 );
	}

	/**
	 * A retired shelf whose term is gone goes to the catalogue, and one that
	 * was kept empty goes to the shelf that holds its products now — at that
	 * shelf's own nested address, so the visitor does not meet the flat alias.
	 */
	public function test_a_retired_shelf_goes_to_the_shelf_that_holds_it(): void {
		$this->assertRedirects( '/product-category/solar-modules/', '/products/' );
		$this->assertRedirects( '/product-category/ci-hybrid/', '/product-category/commercial-storage/all-in-one-systems/' );
		$this->assertRedirects( '/de/produkt-kategorie/ci-hybrid/', '/de/produkt-kategorie/gewerbespeicher/all-in-one-systeme/' );
	}

	/**
	 * A shelf that fills again is served again, whatever the map says: a
	 * product filed on it — here a fixture — keeps the shelf's own address
	 * answering.
	 */
	public function test_a_shelf_that_fills_again_is_served_again(): void {
		$product = (int) self::wp(
			array(
				'post',
				'create',
				'--post_type=product',
				'--post_status=publish',
				'--post_title=Linker redirect fixture',
				'--porcelain',
			)
		);
		self::assertGreaterThan( 0, $product );
		try {
			self::wp( array( 'post', 'term', 'add', (string) $product, 'product_cat', 'res-batteries-lv', '--by=slug' ) );
			self::wp( array( 'wc', 'product', 'update', (string) $product, '--regular_price=1' ) );

			$this->assertStays( '/product-category/res-batteries-lv/', 200 );
		} finally {
			self::wp( array( 'post', 'delete', (string) $product, '--force' ) );
		}
	}

	/**
	 * A retired page path goes to the page that answers it now.
	 */
	public function test_a_retired_page_goes_to_the_page_that_answers_it(): void {
		$this->assertRedirects( '/application/residential-storage/', '/solution/residential-storage/' );
		$this->assertRedirects( '/for-oem-odm/', '/for-installer/' );
	}

	/**
	 * The retired checkout slug goes to the checkout page, in both languages;
	 * a rest of the path (WooCommerce's received page) rides along.
	 */
	public function test_the_retired_checkout_slug_goes_to_the_checkout_page(): void {
		$this->assertRedirects( '/checkout/', '/proforma-request/' );
		$this->assertRedirects( '/de/kasse/', '/de/proforma-anfrage/' );
		$this->assertRedirects( '/checkout/order-received/4711/', '/proforma-request/order-received/4711/' );
	}

	/**
	 * The tool addresses this site itself retired go to the configurator's
	 * roof step, per language.
	 */
	public function test_the_retired_tool_addresses_go_to_the_configurator(): void {
		$this->assertRedirects( '/design-canvas/', '/linker-planner/?step=roof' );
		$this->assertRedirects( '/de/entwurfsflache/', '/de/linker-planer/?step=roof' );
	}

	/**
	 * Live addresses stay where they are, and an unknown address stays a 404
	 * rather than becoming a redirect.
	 */
	public function test_live_and_unknown_addresses_stay(): void {
		$this->assertStays( '/products/', 200 );
		$this->assertStays( '/de/produkte/', 200 );
		$this->assertStays( '/product-category/home-storage/', 200 );
		$this->assertStays( '/de/produkt-kategorie/heimspeicher/', 200 );
		$this->assertStays( '/no-such-address-at-all/', 404 );
	}
}
