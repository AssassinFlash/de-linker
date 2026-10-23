<?php
/**
 * Tests for saved solutions.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Account;

use Linker\Commerce\Account\PrivateFiles;
use Linker\Commerce\Account\SavedSolutions;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use RuntimeException;
use WP_Mock;
use WP_Post;

/**
 * Tests for SavedSolutions.
 *
 * @covers \Linker\Commerce\Account\SavedSolutions
 */
final class SavedSolutionsTest extends TestCase {

	/**
	 * Configurator kind and input of the tests.
	 */
	private const DESIGN = array(
		'kind'  => 'residential',
		'input' => array(
			'plz'        => '39179',
			'annual_kwh' => 4500,
		),
	);

	/**
	 * Post meta of solution 45.
	 *
	 * @var array<string, mixed>
	 */
	private array $meta = array();

	/**
	 * Post meta lives in $meta; solution 45 belongs to customer 5.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::userFunction( 'wp_json_encode', array( 'return' => static fn ( $value ) => json_encode( $value ) ) );
		WP_Mock::userFunction( 'wp_slash', array( 'return' => static fn ( $value ) => $value ) );
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => false ) );
		WP_Mock::userFunction(
			'update_post_meta',
			array(
				'return' => function ( int $id, string $key, $value ): bool {
					$this->meta[ $key ] = $value;
					return true;
				},
			)
		);
		WP_Mock::userFunction( 'get_post_meta', array( 'return' => fn ( int $id, string $key ) => $this->meta[ $key ] ?? '' ) );
		$post = new WP_Post(
			(object) array(
				'ID'          => 45,
				'post_type'   => SavedSolutions::POST_TYPE,
				'post_author' => '5',
			)
		);
		WP_Mock::userFunction( 'get_post', array( 'return' => static fn ( int $id ) => 45 === $id ? $post : null ) );
	}

	/**
	 * The store of a test.
	 */
	private function store(): SavedSolutions {
		return new SavedSolutions( new PrivateFiles( SavedSolutions::REPORTS_DIRECTORY ), '/plugin/templates/' );
	}

	/**
	 * A saved solution is a private post of its customer with its products and design; invalid lines are dropped.
	 */
	public function test_save_and_read(): void {
		WP_Mock::userFunction(
			'wp_insert_post',
			array(
				'times'  => 1,
				'args'   => array(
					array(
						'post_type'   => SavedSolutions::POST_TYPE,
						'post_status' => 'private',
						'post_author' => 5,
						'post_title'  => 'House Barleben',
					),
					true,
				),
				'return' => 45,
			)
		);
		$saved = $this->store();

		$this->assertSame(
			45,
			$saved->save(
				5,
				'House Barleben',
				array(
					array(
						'product_id' => 4107,
						'quantity'   => 1,
					),
					array(
						'product_id' => 0,
						'quantity'   => 2,
					),
					array(
						'product_id' => 2067,
						'quantity'   => -1,
					),
				),
				self::DESIGN
			)
		);
		$this->assertSame( json_encode( self::DESIGN ), $this->meta[ SavedSolutions::DESIGN_META ] );
		$this->assertSame(
			array(
				array(
					'product_id' => 4107,
					'quantity'   => 1,
				),
			),
			$saved->items( 45 )
		);
		$this->assertSame( 5, $saved->owner( 45 ) );
		$this->assertSame( 0, $saved->owner( 46 ) );
		$this->assertSame( '', $saved->report_path( 45 ) );
	}

	/**
	 * A customer's solutions are their private posts, newest first; without a customer there are none.
	 */
	public function test_for_customer(): void {
		WP_Mock::userFunction(
			'get_posts',
			array(
				'times'  => 1,
				'args'   => array(
					array(
						'post_type'      => SavedSolutions::POST_TYPE,
						'post_status'    => 'private',
						'author'         => 5,
						'posts_per_page' => -1,
						'orderby'        => 'date',
						'order'          => 'DESC',
					),
				),
				'return' => array( new WP_Post( (object) array( 'ID' => 45 ) ) ),
			)
		);
		$saved = $this->store();

		$this->assertCount( 1, $saved->for_customer( 5 ) );
		$this->assertSame( array(), $saved->for_customer( 0 ) );
	}

	/**
	 * "Add to solution draft" puts the products into the current draft for the owner only, after the nonce check.
	 */
	public function test_legacy_solution_without_snapshot_cannot_be_added_as_a_current_design(): void {
		$this->meta = array(
			SavedSolutions::ITEMS_META => json_encode(
				array(
					array(
						'product_id' => 4107,
						'quantity'   => 2,
					),
				)
			),
		);
		$_POST      = array(
			SavedSolutions::ADD_ACTION => '45',
			'_wpnonce'                 => 'nonce',
		);
		WP_Mock::userFunction( 'absint', array( 'return' => static fn ( $value ): int => abs( (int) $value ) ) );
		WP_Mock::userFunction( 'sanitize_text_field', array( 'return' => static fn ( string $value ): string => $value ) );
		WP_Mock::userFunction( 'wp_unslash', array( 'return' => static fn ( $value ) => $value ) );
		WP_Mock::userFunction(
			'wp_verify_nonce',
			array(
				'args'   => array( 'nonce', SavedSolutions::ADD_ACTION . '_45' ),
				'return' => 1,
			)
		);
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 5 ) );
		WP_Mock::passthruFunction( '__' );
		$cart = Mockery::mock();
		$cart->expects( 'add_to_cart' )->never();
		$woocommerce       = new \stdClass();
		$woocommerce->cart = $cart;
		WP_Mock::userFunction( 'WC', array( 'return' => $woocommerce ) );
		WP_Mock::userFunction(
			'wc_add_notice',
			array(
				'times' => 1,
				'args'  => array( 'This solution needs a new calculation before it can be saved or added to your solution draft.', 'error' ),
			)
		);
		WP_Mock::userFunction( 'wc_get_cart_url', array( 'return' => 'https://example.test/cart/' ) );
		WP_Mock::userFunction(
			'wp_safe_redirect',
			array(
				'return' => static function ( string $url ): void {
					throw new RuntimeException( $url );
				},
			)
		);

		try {
			$this->store()->add_to_draft();
			$this->fail( 'No redirect.' );
		} catch ( RuntimeException $redirect ) {
			$this->assertSame( 'https://example.test/cart/', $redirect->getMessage() );
		} finally {
			$_POST = array();
		}
	}

	/**
	 * Without the form nothing happens; another customer's solution is refused.
	 */
	public function test_add_to_draft_refusals(): void {
		$this->store()->add_to_draft();

		$_POST = array(
			SavedSolutions::ADD_ACTION => '45',
			'_wpnonce'                 => 'nonce',
		);
		WP_Mock::userFunction( 'absint', array( 'return' => static fn ( $value ): int => abs( (int) $value ) ) );
		WP_Mock::userFunction( 'sanitize_text_field', array( 'return' => static fn ( string $value ): string => $value ) );
		WP_Mock::userFunction( 'wp_unslash', array( 'return' => static fn ( $value ) => $value ) );
		WP_Mock::userFunction( 'wp_verify_nonce', array( 'return' => 1 ) );
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 6 ) );
		WP_Mock::userFunction( 'wp_safe_redirect', array( 'times' => 0 ) );

		$this->store()->add_to_draft();
		$_POST = array();
		$this->assertConditionsMet();
	}

	/**
	 * A guest's solution joins the solutions already in their session, with clean lines, and the session gets its cookie.
	 */
	public function test_keep_for_guest(): void {
		WP_Mock::userFunction( 'wc_load_cart', array( 'times' => 1 ) );
		$earlier = array(
			'title'  => 'Earlier',
			'items'  => array(),
			'design' => array(),
		);
		$session = Mockery::mock( \WC_Session_Handler::class );
		$session->expects( 'get' )->with( SavedSolutions::SESSION_KEY, array() )->andReturn( array( $earlier ) );
		$session->expects( 'set' )->with(
			SavedSolutions::SESSION_KEY,
			array(
				$earlier,
				array(
					'title'  => 'House Barleben',
					'items'  => array(
						array(
							'product_id' => 4107,
							'quantity'   => 1,
						),
					),
					'design' => self::DESIGN,
				),
			)
		);
		$session->expects( 'set_customer_session_cookie' )->with( true );
		$this->woocommerce_session( $session );

		$this->store()->keep_for_guest(
			'House Barleben',
			array(
				array(
					'product_id' => 4107,
					'quantity'   => 1,
				),
				array(
					'product_id' => 4108,
					'quantity'   => 0,
				),
			),
			self::DESIGN
		);
		$this->assertConditionsMet();
	}

	/**
	 * Once the guest is a logged-in customer, each kept solution becomes theirs and leaves the session.
	 */
	public function test_claim(): void {
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 5 ) );
		$session = Mockery::mock();
		$session->expects( 'get' )->with( SavedSolutions::SESSION_KEY )->andReturn(
			array(
				array(
					'title'  => 'House Barleben',
					'items'  => array(
						array(
							'product_id' => 4107,
							'quantity'   => 1,
						),
					),
					'design' => self::DESIGN,
				),
				'not a solution',
			)
		);
		$session->expects( 'set' )->with( SavedSolutions::SESSION_KEY, null );
		$this->woocommerce_session( $session );
		WP_Mock::userFunction(
			'wp_insert_post',
			array(
				'times'  => 1,
				'args'   => array(
					array(
						'post_type'   => SavedSolutions::POST_TYPE,
						'post_status' => 'private',
						'post_author' => 5,
						'post_title'  => 'House Barleben',
					),
					true,
				),
				'return' => 45,
			)
		);

		$this->store()->claim();

		$this->assertSame( json_encode( self::DESIGN ), $this->meta[ SavedSolutions::DESIGN_META ] );
		$this->assertSame( 4107, $this->store()->items( 45 )[0]['product_id'] );
	}

	/**
	 * A guest keeps their solutions in the session; a customer without kept solutions has nothing to claim.
	 */
	public function test_claim_needs_a_customer_and_solutions(): void {
		$session = Mockery::mock();
		$session->allows( 'get' )->with( SavedSolutions::SESSION_KEY )->andReturn( array( array( 'title' => 'House' ) ), null );
		$session->expects( 'set' )->never();
		$this->woocommerce_session( $session );
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 0 ) );
		WP_Mock::userFunction( 'wp_insert_post', array( 'times' => 0 ) );

		$this->store()->claim();
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 5 ) );
		$this->store()->claim();

		$this->assertConditionsMet();
	}

	/**
	 * A saved solution opens at its row of the account page.
	 */
	public function test_url(): void {
		WP_Mock::userFunction(
			'wc_get_account_endpoint_url',
			array(
				'args'   => array( 'saved-solutions' ),
				'return' => 'https://example.test/my-account/saved-solutions/',
			)
		);

		$this->assertSame( 'https://example.test/my-account/saved-solutions/#linker-solution-45', SavedSolutions::url( 45 ) );
		$this->assertSame( 'https://example.test/my-account/saved-solutions/', SavedSolutions::url( 0 ) );
	}

	/**
	 * WC() of a test, with the given session.
	 *
	 * @param object $session The session.
	 */
	private function woocommerce_session( object $session ): void {
		$woocommerce          = new \stdClass();
		$woocommerce->session = $session;
		WP_Mock::userFunction( 'WC', array( 'return' => $woocommerce ) );
	}
}
