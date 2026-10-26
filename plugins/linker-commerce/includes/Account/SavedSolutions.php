<?php
/**
 * Solutions a customer saved.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Account;

use WP_Post;

/**
 * The one store of saved solutions: products with quantities, the Solution
 * Configurator input that reproduces the design and, when the configurator
 * sent one, its design report PDF. The configurator (#14) saves through
 * SolutionsRoute; the account lists the solutions under "Saved solutions" and
 * "Documents" and can put a saved solution's products into the current
 * solution draft. Each saved solution is a private post of its customer.
 *
 * A guest's solution waits in their WooCommerce session, which lasts 48 hours
 * for guests (WC_Session_Handler::set_session_expiration()). WooCommerce hands
 * that session to the customer at login, and claim() then moves the solution
 * into the account: the session cookie is the guest's claim.
 */
final class SavedSolutions {

	/**
	 * Post type of a saved solution.
	 */
	public const POST_TYPE = 'linker_solution';

	/**
	 * Post meta: the products, the configurator input and the design report.
	 */
	public const ITEMS_META  = '_linker_solution_items';
	public const DESIGN_META = '_linker_solution_design';
	public const REPORT_META = '_linker_solution_report';

	/**
	 * Session key of the solutions a guest saved.
	 */
	public const SESSION_KEY = 'linker_saved_solutions';

	/**
	 * Directory under uploads of the design reports.
	 */
	public const REPORTS_DIRECTORY = 'solution-reports';

	/**
	 * Form action and nonce of "put into the solution draft".
	 */
	public const ADD_ACTION = 'linker_solution_to_draft';

	/**
	 * Sets up the store.
	 *
	 * @param PrivateFiles $reports      Where the design reports are kept.
	 * @param string       $template_dir Directory of the plugin's templates.
	 */
	public function __construct(
		private readonly PrivateFiles $reports,
		private readonly string $template_dir
	) {}

	/**
	 * Registers the post type; runs on init.
	 */
	public function register_post_type(): void {
		register_post_type(
			self::POST_TYPE,
			array(
				'label'           => __( 'Saved solutions', 'linker-commerce' ),
				'public'          => false,
				'show_ui'         => false,
				'rewrite'         => false,
				'query_var'       => false,
				'supports'        => array( 'title', 'author' ),
				'capability_type' => 'post',
			)
		);
	}

	/**
	 * Saves a solution for a customer.
	 *
	 * @param int                                         $customer_id Customer.
	 * @param string                                      $title       Name of the solution.
	 * @param list<array{product_id: int, quantity: int}> $items       Products and quantities.
	 * @param array<string, mixed>                        $design      Configurator kind and input.
	 * @param string                                      $report_pdf  Design report PDF bytes, '' for none.
	 * @return int Solution id, 0 when it could not be saved.
	 */
	public function save( int $customer_id, string $title, array $items, array $design, string $report_pdf = '' ): int {
		$id = wp_insert_post(
			array(
				'post_type'   => self::POST_TYPE,
				'post_status' => 'private',
				'post_author' => $customer_id,
				'post_title'  => $title,
			),
			true
		);
		if ( is_wp_error( $id ) ) {
			return 0;
		}
		update_post_meta( $id, self::ITEMS_META, wp_slash( (string) wp_json_encode( self::clean_items( $items ) ) ) );
		update_post_meta( $id, self::DESIGN_META, wp_slash( (string) wp_json_encode( $design ) ) );
		if ( '' !== $report_pdf ) {
			update_post_meta( $id, self::REPORT_META, $this->reports->write( $id, sanitize_title( $title ), $report_pdf ) );
		}
		return $id;
	}

	/**
	 * Keeps a guest's solution in their WooCommerce session until they log in.
	 *
	 * @param string                                      $title  Name of the solution.
	 * @param list<array{product_id: int, quantity: int}> $items  Products and quantities.
	 * @param array<string, mixed>                        $design Configurator kind and input.
	 * @return int Slot of this newly kept record, for final-check compensation.
	 */
	public function keep_for_guest( string $title, array $items, array $design ): int {
		// REST requests start without WooCommerce's session; this loads it from the guest's cookie.
		wc_load_cart();
		$kept   = (array) WC()->session->get( self::SESSION_KEY, array() );
		$kept[] = array(
			'title'  => $title,
			'items'  => self::clean_items( $items ),
			'design' => $design,
		);
		WC()->session->set( self::SESSION_KEY, $kept );
		$session = WC()->session;
		if ( $session instanceof \WC_Session_Handler ) {
			// A guest without a solution draft has no session cookie yet.
			$session->set_customer_session_cookie( true );
		}
		return (int) array_key_last( $kept );
	}

	/**
	 * Compensate only the just-written guest record; prior history remains.
	 *
	 * @param int    $slot        Slot returned by keep_for_guest().
	 * @param string $fingerprint Confirmed design identity.
	 */
	public function discard_guest( int $slot, string $fingerprint ): void {
		$kept = WC()->session->get( self::SESSION_KEY, array() );
		if ( is_array( $kept ) && ( $kept[ $slot ]['design']['selection_fingerprint'] ?? null ) === $fingerprint ) {
			unset( $kept[ $slot ] );
			WC()->session->set( self::SESSION_KEY, array_values( $kept ) );
		}
	}

	/**
	 * Moves the solutions a guest saved into their account once they are
	 * logged in; runs when WooCommerce loads the session's solution draft.
	 */
	public function claim(): void {
		$customer_id = get_current_user_id();
		$kept        = WC()->session->get( self::SESSION_KEY );
		if ( 0 === $customer_id || ! is_array( $kept ) || array() === $kept ) {
			return;
		}
		WC()->session->set( self::SESSION_KEY, null );
		foreach ( $kept as $solution ) {
			if ( is_array( $solution ) ) {
				$this->save(
					$customer_id,
					(string) ( $solution['title'] ?? '' ),
					self::clean_items( (array) ( $solution['items'] ?? array() ) ),
					(array) ( $solution['design'] ?? array() )
				);
			}
		}
	}

	/**
	 * Where the account shows a saved solution.
	 *
	 * @param int $solution_id Solution, 0 for the list.
	 */
	public static function url( int $solution_id ): string {
		$url = wc_get_account_endpoint_url( 'saved-solutions' );
		return $solution_id > 0 ? $url . '#linker-solution-' . $solution_id : $url;
	}

	/**
	 * A customer's saved solutions, newest first.
	 *
	 * @param int $customer_id Customer.
	 * @return WP_Post[]
	 */
	public function for_customer( int $customer_id ): array {
		if ( $customer_id <= 0 ) {
			return array();
		}
		return get_posts(
			array(
				'post_type'      => self::POST_TYPE,
				'post_status'    => 'private',
				'author'         => $customer_id,
				'posts_per_page' => -1,
				'orderby'        => 'date',
				'order'          => 'DESC',
			)
		);
	}

	/**
	 * The products and quantities of a saved solution.
	 *
	 * @param int $solution_id Solution.
	 * @return list<array{product_id: int, quantity: int}>
	 */
	public function items( int $solution_id ): array {
		$items = json_decode( (string) get_post_meta( $solution_id, self::ITEMS_META, true ), true );
		return self::clean_items( is_array( $items ) ? $items : array() );
	}

	/**
	 * The customer a saved solution belongs to, 0 for none.
	 *
	 * @param int $solution_id Solution.
	 */
	public function owner( int $solution_id ): int {
		$post = get_post( $solution_id );
		return $post instanceof WP_Post && self::POST_TYPE === $post->post_type ? (int) $post->post_author : 0;
	}

	/**
	 * Absolute path of a saved solution's design report, '' for none.
	 *
	 * @param int $solution_id Solution.
	 */
	public function report_path( int $solution_id ): string {
		return $this->reports->path( (string) get_post_meta( $solution_id, self::REPORT_META, true ) );
	}

	/**
	 * Immutable engine result stored when the customer saved this design.
	 * A legacy record without a snapshot does not re-run today's engine.
	 *
	 * @param int $solution_id Solution.
	 * @return array<string, mixed>|null
	 */
	public function snapshot( int $solution_id ): ?array {
		$design = json_decode( (string) get_post_meta( $solution_id, self::DESIGN_META, true ), true );
		return is_array( $design ) && is_array( $design['snapshot'] ?? null ) ? $design['snapshot'] : null;
	}

	/**
	 * Recorded item labels only, never current facts from a withdrawn product.
	 *
	 * @param int $solution_id Solution.
	 * @return list<array{product_id:int,quantity:int,label:string}>
	 */
	public function historical_items( int $solution_id ): array {
		$snapshot = $this->snapshot( $solution_id );
		$labels   = array();
		$selected = is_array( $snapshot['selected'] ?? null ) ? $snapshot['selected'] : array();
		if ( array() === $selected && is_int( $snapshot['selected_system_index'] ?? null ) && is_array( $snapshot['systems'][ $snapshot['selected_system_index'] ] ?? null ) ) {
			$selected = $snapshot['systems'][ $snapshot['selected_system_index'] ];
		}
		foreach ( is_array( $selected['lines'] ?? null ) ? $selected['lines'] : array() as $line ) {
			if ( is_array( $line ) && is_array( $line['product'] ?? null ) ) {
				$product                                 = $line['product'];
				$labels[ (int) ( $product['id'] ?? 0 ) ] = trim( (string) ( $product['brand'] ?? '' ) . ' ' . (string) ( $product['model'] ?? '' ) );
			}
		}
		$items = array();
		foreach ( $this->items( $solution_id ) as $item ) {
			/* translators: %d: product ID recorded in a historical solution. */
			$item['label'] = $labels[ $item['product_id'] ] ?? sprintf( __( 'Product %d', 'linker-commerce' ), $item['product_id'] );
			$items[]       = $item;
		}
		return $items;
	}

	/**
	 * Removes only a new write rejected by its final publication check.
	 *
	 * @param int $solution_id Newly inserted solution.
	 */
	public function discard( int $solution_id ): void {
		$this->reports->delete( (string) get_post_meta( $solution_id, self::REPORT_META, true ) );
		wp_delete_post( $solution_id, true );
	}

	/**
	 * Prints the "Saved solutions" page of the account; runs on its endpoint.
	 */
	public function render(): void {
		wc_get_template(
			'myaccount/linker-saved-solutions.php',
			array(
				'solutions' => $this->for_customer( get_current_user_id() ),
				'saved'     => $this,
			),
			'',
			$this->template_dir
		);
	}

	/**
	 * Puts a saved solution's products into the current solution draft and
	 * opens it; runs on wp_loaded, before WooCommerce sends the page.
	 */
	public function add_to_draft(): void {
		// phpcs:ignore WordPress.Security.NonceVerification.Missing -- verified below.
		$solution_id = isset( $_POST[ self::ADD_ACTION ] ) ? absint( $_POST[ self::ADD_ACTION ] ) : 0;
		if ( 0 === $solution_id ) {
			return;
		}
		$nonce = isset( $_POST['_wpnonce'] ) ? sanitize_text_field( wp_unslash( $_POST['_wpnonce'] ) ) : '';
		if ( ! wp_verify_nonce( $nonce, self::ADD_ACTION . '_' . $solution_id ) || get_current_user_id() !== $this->owner( $solution_id ) ) {
			return;
		}
		$snapshot = $this->snapshot( $solution_id );
		$added    = null !== $snapshot ? ( new AtomicSolutionDraft() )->add( $snapshot ) : DesignProof::unavailable();
		if ( $added instanceof \WP_Error ) {
			wc_add_notice( $added->get_error_message(), 'error' );
		} else {
			wc_add_notice( __( 'The products of the saved solution are in your solution draft.', 'linker-commerce' ) );
		}
		wp_safe_redirect( $added instanceof \WP_Error ? self::url( 0 ) : wc_get_cart_url() );
		exit;
	}

	/**
	 * Valid items only: positive product ids and quantities.
	 *
	 * @param array<mixed> $items Items.
	 * @return list<array{product_id: int, quantity: int}>
	 */
	private static function clean_items( array $items ): array {
		$clean = array();
		foreach ( $items as $item ) {
			if ( ! is_array( $item ) ) {
				continue;
			}
			$product_id = (int) ( $item['product_id'] ?? 0 );
			$quantity   = (int) ( $item['quantity'] ?? 0 );
			if ( $product_id > 0 && $quantity > 0 ) {
				$clean[] = array(
					'product_id' => $product_id,
					'quantity'   => $quantity,
				);
			}
		}
		return $clean;
	}
}
