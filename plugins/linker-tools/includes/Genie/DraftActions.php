<?php
/**
 * Current Genie product-list writes reuse the native account and Woo stores.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );
namespace Linker\Tools\Genie;

use Linker\Commerce\Account\AtomicSolutionDraft;
use Linker\Commerce\Account\DesignProof;
use Linker\Commerce\Account\PrivateFiles;
use Linker\Commerce\Account\SavedSolutions;
use WP_Error;
use WP_REST_Request;
use WP_REST_Response;

/** A browser chooses a signed artifact, never individual lines from its list. */
final class DraftActions {
	/**
	 * Native stores and current authority have explicit fixture seams.
	 *
	 * @param DraftProof                                                                      $proof Signed complete artifact reader.
	 * @param SavedSolutions|null                                                             $solutions Existing private history store.
	 * @param callable(array<string,mixed>):(array<array{id:int,quantity:int}>|WP_Error)|null $add Exact native whole-list write.
	 * @param callable(array<string,mixed>):bool|null                                         $current Fresh current dependency reader.
	 */
	public function __construct( private readonly DraftProof $proof = new DraftProof(), private readonly ?SavedSolutions $solutions = null, private $add = null, private $current = null ) {}

	/** Register two explicit product-list actions, without an engineering fallback. */
	public function register(): void {
		foreach ( array(
			'/genie/draft'    => 'draft',
			'/genie/solution' => 'save',
		) as $route => $callback ) {
			register_rest_route(
				Proxy::NAMESPACE,
				$route,
				array(
					'methods'             => 'POST',
					'callback'            => array( $this, $callback ),
					'permission_callback' => array( $this, 'permission' ),
					'args'                => array(
						'proof' => array(
							'type'     => 'string',
							'required' => true,
						),
					),
				)
			);
		}
	}

	/**
	 * Retain native Woo session CSRF permission alongside the signed identity.
	 *
	 * @param WP_REST_Request $request Native request.
	 */
	public function permission( WP_REST_Request $request ): bool|WP_Error {
		$nonce = $request->get_header( 'Nonce' );
		return is_string( $nonce ) && wp_verify_nonce( $nonce, 'wc_store_api' ) ? true : new WP_Error( 'woocommerce_rest_invalid_nonce', __( 'Your request could not be completed. Your input is still here. Please try again.', 'linker-tools' ), array( 'status' => 403 ) );
	}

	/**
	 * Add the complete server-signed list atomically.
	 *
	 * @phpstan-impure Reads current owner/authority and writes the native cart.
	 *
	 * @param WP_REST_Request $request Signed artifact token only.
	 */
	public function draft( WP_REST_Request $request ): WP_REST_Response|WP_Error {
		$result = $this->proof->verify( (string) $request->get_param( 'proof' ) );
		if ( $result instanceof WP_Error ) {
			return $result;
		}
		$items = is_callable( $this->add ) ? ( $this->add )( $result ) : ( new AtomicSolutionDraft() )->add( $result );
		if ( $items instanceof WP_Error && 'linker_solution_changed' === $items->get_error_code() ) {
			return DraftProof::changed();
		}
		return $items instanceof WP_Error ? $items : $this->response(
			array(
				'items'       => $items,
				'publication' => $result['publication'],
			)
		);
	}

	/**
	 * Save a product-list snapshot without inventing engineering inputs/results.
	 *
	 * @param WP_REST_Request $request Signed artifact token only.
	 */
	public function save( WP_REST_Request $request ): WP_REST_Response|WP_Error {
		$result = $this->proof->verify( (string) $request->get_param( 'proof' ) );
		if ( $result instanceof WP_Error ) {
			return $result;
		}
		$current = $this->current_error( $result );
		if ( null !== $current ) {
			return $current;
		}
		$solutions = $this->solutions ?? new SavedSolutions( new PrivateFiles( SavedSolutions::REPORTS_DIRECTORY ), '' );
		$items     = DesignProof::items( $result );
		$labels    = array();
		foreach ( $result['selected']['lines'] as $line ) {
			$labels[] = trim( $line['product']['brand'] . ' ' . $line['product']['model'] );
		}
		$title    = implode( ', ', $labels );
		$design   = array(
			'kind'                  => 'genie',
			'input'                 => array(),
			'selection_fingerprint' => $result['selection_fingerprint'],
			'snapshot'              => $result,
		);
		$customer = get_current_user_id();
		if ( $customer > 0 ) {
			$id = $solutions->save( $customer, $title, $items, $design );
			if ( $id < 1 ) {
				return new WP_Error( 'linker_solution_save', __( 'Not saved. Try again.', 'linker-tools' ), array( 'status' => 500 ) );
			}
			$current = $this->current_error( $result );
			if ( null !== $current ) {
				$solutions->discard( $id );
				return $current;
			}
			return $this->response(
				array(
					'id'          => $id,
					'url'         => SavedSolutions::url( $id ),
					'publication' => $result['publication'],
				),
				201
			);
		}
		$slot    = $solutions->keep_for_guest( $title, $items, $design );
		$current = $this->current_error( $result );
		if ( null !== $current ) {
			$solutions->discard_guest( $slot, $result['selection_fingerprint'] );
			return $current;
		}
		return $this->response(
			array(
				'id'          => 0,
				'url'         => SavedSolutions::url( 0 ),
				'publication' => $result['publication'],
			),
			202
		);
	}

	/**
	 * Recheck current authority before and after the write.
	 *
	 * @phpstan-impure
	 * @param array<string,mixed> $result Trusted complete artifact.
	 */
	private function current_error( array $result ): ?WP_Error {
		if ( is_callable( $this->current ) ) {
			return ( $this->current )( $result ) ? null : DraftProof::changed();
		}
		$error = ( new DesignProof() )->current_error( $result );
		return $error instanceof WP_Error && 'linker_solution_changed' === $error->get_error_code() ? DraftProof::changed() : $error;
	}

	/**
	 * Current writes and history never enter a shared HTTP cache.
	 *
	 * @param array<string,mixed> $data Result with current publication proof.
	 * @param int                 $status Native result status.
	 */
	private function response( array $data, int $status = 200 ): WP_REST_Response {
		$reply = new WP_REST_Response( $data, $status );
		$reply->header( 'Cache-Control', 'private, no-store' );
		return $reply;
	}
}
