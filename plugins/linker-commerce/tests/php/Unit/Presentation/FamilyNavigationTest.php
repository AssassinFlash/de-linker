<?php
/**
 * Native family paging addresses and metadata.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Presentation;

use Linker\Commerce\Presentation\FamilyNavigation;
use Linker\Commerce\Presentation\FamilyPage;
use Linker\Commerce\Presentation\ProductShortcodes;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * One family page controls aliases, head metadata and current page bounds.
 *
 * @covers \Linker\Commerce\Presentation\FamilyNavigation
 */
final class FamilyNavigationTest extends TestCase {

	/**
	 * The native path's individual-product page.
	 *
	 * @var int
	 */
	private int $native_page = 0;

	/**
	 * Native request flags outside the family surface.
	 *
	 * @var array<string, bool>
	 */
	private array $excluded = array();

	/** Mock only the native request and URL seams. */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
		$_GET                      = array();
		$_SERVER['REQUEST_METHOD'] = 'GET';
		$this->native_page         = 0;
		$this->excluded            = array();
		foreach ( array( 'is_admin', 'wp_doing_ajax', 'is_404', 'is_feed', 'is_embed', 'is_preview', 'is_search' ) as $flag ) {
			WP_Mock::userFunction( $flag, array( 'return' => fn(): bool => $this->request_excluded( $flag ) ) );
		}
		WP_Mock::userFunction( 'is_main_query', array( 'return' => fn(): bool => ! $this->request_excluded( 'secondary' ) ) );
		WP_Mock::userFunction( 'is_shop', array( 'return' => true ) );
		WP_Mock::userFunction( 'get_query_var', array( 'return' => fn(): int => $this->native_page ) );
		WP_Mock::userFunction( 'wp_unslash', array( 'return' => static fn( $value ) => $value ) );
		WP_Mock::userFunction(
			'add_query_arg',
			array(
				'return' => static function ( string $key, int $value, string $base ): string {
					return $base . ( str_contains( $base, '?' ) ? '&' : '?' ) . $key . '=' . $value;
				},
			)
		);
	}

	/**
	 * Read the request flag when the native callback executes, after setup.
	 *
	 * @param string $flag Native request flag.
	 */
	private function request_excluded( string $flag ): bool {
		return $this->excluded[ $flag ] ?? false;
	}

	/**
	 * Build the actual data page from the current request.
	 *
	 * @param int $total Matching families.
	 */
	private function navigation( int $total = 65 ): FamilyNavigation {
		$rows = array();
		for ( $i = 1; $i <= $total; $i++ ) {
			$rows[] = array(
				'lead' => $i,
				'ids'  => array( $i, 1000 + $i ),
			);
		}
		return new FamilyNavigation(
			fn(): FamilyPage => new FamilyPage( $rows, wp_unslash( $_GET['product-page'] ?? $this->native_page ), ProductShortcodes::PER_PAGE_FAMILIES ), // phpcs:ignore WordPress.Security.NonceVerification.Recommended, WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- fixture input, validated by FamilyPage.
			static fn(): string => 'http://linker.test/products/?q=SAJ&sort=name'
		);
	}

	/** A duplicate native SAJ page resolves to its one valid family root. */
	public function test_native_product_page_does_not_create_a_second_saj_family_page(): void {
		$this->native_page = 2;
		self::assertSame( 'http://linker.test/products/?q=SAJ&sort=name', $this->navigation( 13 )->normalization_target() );
	}

	/** A real second family slice retains search and order on its native root. */
	public function test_native_alias_maps_to_the_real_family_slice(): void {
		$this->native_page = 2;
		self::assertSame( 'http://linker.test/products/?q=SAJ&sort=name&product-page=2', $this->navigation()->normalization_target() );
	}

	/** Explicit family input has deterministic precedence over a path alias. */
	public function test_explicit_page_takes_precedence_and_is_clamped(): void {
		$this->native_page    = 2;
		$_GET['product-page'] = str_repeat( '9', 100 );
		self::assertSame( 'http://linker.test/products/?q=SAJ&sort=name&product-page=3', $this->navigation()->normalization_target() );
	}

	/** A final normalized address does not redirect to itself. */
	public function test_normalized_later_page_has_no_redirect_loop(): void {
		$_GET['product-page'] = '2';
		self::assertSame( '', $this->navigation()->normalization_target() );
	}

	/**
	 * Invalid or root query aliases redirect once to the valid root.
	 *
	 * @dataProvider invalid_values
	 * @param mixed $value Public query page.
	 */
	public function test_invalid_query_pages_use_the_root( mixed $value ): void {
		$_GET['product-page'] = $value;
		self::assertSame( 'http://linker.test/products/?q=SAJ&sort=name', $this->navigation()->normalization_target() );
	}

	/**
	 * Representative invalid query shapes, including native arrays.
	 *
	 * @return array<string, array{mixed}>
	 */
	public function invalid_values(): array {
		return array(
			'page-one' => array( '1' ),
			'zero'     => array( '0' ),
			'negative' => array( '-2' ),
			'text'     => array( 'next' ),
			'array'    => array( array( '2' ) ),
		);
	}

	/** Native 404/feed/search/admin/secondary responses are not normalized. */
	public function test_other_native_consumers_are_not_redirected(): void {
		$this->native_page = 2;
		foreach ( array( 'is_admin', 'wp_doing_ajax', 'is_404', 'is_feed', 'is_embed', 'is_preview', 'is_search', 'secondary' ) as $flag ) {
			$this->excluded = array( $flag => true );
			self::assertSame( '', $this->navigation()->normalization_target(), $flag );
		}
		$this->excluded            = array();
		$_SERVER['REQUEST_METHOD'] = 'POST';
		self::assertSame( '', $this->navigation()->normalization_target() );
	}

	/** Real family paging follows the configured native paged-noindex gate. */
	public function test_existing_noindex_decisions_and_native_paged_policy_are_preserved(): void {
		$_GET['product-page'] = '2';
		WP_Mock::userFunction(
			'seopress_get_service',
			array(
				'return' => new class() {
					/** Native configured option value. */
					public function getPagedNoIndex(): string { // phpcs:ignore WordPress.NamingConventions.ValidFunctionName.MethodNameInvalid -- native method name.
						return '1';
					}
				},
			)
		);
		self::assertSame( '1', $this->navigation()->noindex( '' ) );
		self::assertSame( 'yes', $this->navigation()->noindex( 'yes' ) );
		self::assertSame( array(), $this->navigation()->hreflangs( array( 'en' => '/products/' ) ) );
		self::assertStringContainsString( '?q=SAJ&sort=name&product-page=2', $this->navigation()->canonical( '<link rel="canonical" href="/products/">' ) );
		$_GET = array();
		self::assertSame( '', $this->navigation()->noindex( '' ) );
		self::assertSame( array( 'en' => '/products/' ), $this->navigation()->hreflangs( array( 'en' => '/products/' ) ) );
	}

	/** SEOPress applies the same filter to its explicit custom-term element. */
	public function test_native_custom_term_canonical_remains_authoritative(): void {
		$_GET['product-page'] = '2';
		WP_Mock::userFunction( 'seopress_titles_canonical_term_option', array( 'return' => 'https://linker.test/preferred-products/' ) );
		$custom = '<link rel="canonical" href="https://linker.test/preferred-products/">';
		self::assertSame( $custom, $this->navigation()->canonical( $custom ) );
	}
}
