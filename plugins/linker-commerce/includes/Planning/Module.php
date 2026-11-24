<?php
/**
 * Native Woo draft, inquiry and report-consumer integration.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Planning;

use Linker\Commerce\Abilities\ProductText;
use Linker\Commerce\Products\EngineeringReference;
use Linker\Commerce\Products\Materials;
use Linker\Commerce\Products\Publication;

/** All visual output remains native semantic data; no page template or CSS. */
final class Module {
	/** Register native product/context lifecycle and private file access. */
	public function register(): void {
		$context = new Context();
		add_filter( 'woocommerce_session_handler', array( $this, 'session_handler' ) );
		add_filter( 'linker_commerce_planning_inquiry_form', array( $this, 'inquiry_form' ), 10, 4 );
		add_filter( 'linker_commerce_planning_inquiry_retry', array( $this, 'inquiry_retry' ), 10, 4 );
		add_filter( 'linker_commerce_planning_draft_apply', array( new DraftTransfer(), 'apply' ), 10, 3 );
		add_filter( 'linker_commerce_planning_draft_preview', array( new DraftPreview(), 'read' ), 10, 3 );
		add_filter( 'linker_commerce_planning_draft_read', array( new DraftTransfer(), 'receipt' ), 10, 3 );
		add_filter( 'woocommerce_get_item_data', array( $context, 'item_data' ), 10, 2 );
		add_action( 'woocommerce_before_cart', array( $context, 'cart_phase_notices' ) );
		add_action( 'woocommerce_checkout_create_order_line_item', array( $context, 'line' ), 10, 3 );
		add_action( 'woocommerce_order_details_after_order_table', array( $context, 'render' ) );
		add_action( 'woocommerce_admin_order_data_after_order_details', array( $context, 'render' ) );
		add_action( 'woocommerce_email_after_order_table', array( $context, 'email' ), 10, 3 );
		add_action( 'woocommerce_cart_emptied', array( $context, 'emptied' ) );
		add_action( 'rest_api_init', array( new ReportDownload(), 'register' ) );
	}

	/** Woo validates cart tokens and decides whether to clone or restore.
	 *
	 * @param string $handler Woo's configured session handler.
	 */
	public function session_handler( string $handler ): string {
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended -- Only selects the adapter; Woo validates its own token.
		return isset( $_GET['session'] ) && \WC_Session_Handler::class === $handler ? SharedCartSession::class : $handler;
	}

	/** Native inquiry form and the current draft it will send.
	 *
	 * @param mixed                    $previous Earlier filter result.
	 * @param string                   $language Requested planner language.
	 * @param array<string,mixed>      $project  Owner-verified project revision.
	 * @param array<string,mixed>|null $proposal Owned report and optional native retry.
	 * @return array<string,mixed>|\WP_Error
	 */
	public function inquiry_form( mixed $previous, string $language, array $project, ?array $proposal = null ): array|\WP_Error {
		unset( $previous );
		wc_load_cart();
		$handoff = $proposal['handoff'] ?? null;
		$retry   = $proposal['retained'] ?? null;
		$preview = null;
		$bound   = null;
		if ( null !== $proposal ) {
			$command = $proposal['command'];
			if ( ! DraftTransfer::envelope_valid( $handoff, $project['project_id'], $command['report_run_id'], $project['revision'] ) ) {
				return Context::admission_unavailable();
			}
			$replay = InquiryTransfer::read( $proposal['replay'] );
			if ( null !== $proposal['replay'] && ( null === $replay || $replay->report !== $command['report_run_id'] || $replay->handoff !== $handoff['id'] ) ) {
				return Context::admission_unavailable();
			}
			if ( null !== $replay && ( null === $retry || '1' === ( $retry['fields']['linker_recovery_available'] ?? '' ) ) ) {
				$bound = $replay;
			} else {
				$preview = ( new DraftPreview() )->read( null, $command, $handoff, guided: true );
				if ( is_wp_error( $preview ) ) {
					return $preview;
				}
				$bound = new InquiryTransfer( $command['report_run_id'], $handoff['id'], $command['key'], $preview['draft_sha256'] );
			}
		}
		$lines = array();
		if ( null !== $handoff ) {
			foreach ( $handoff['snapshot']['items'] as $item ) {
				$lines[] = array(
					'product_id'    => $item['product_id'],
					'label'         => $item['label'],
					'quantity'      => $item['quantity'],
					'project_id'    => $project['project_id'],
					'project_title' => $project['title'],
				);
			}
		} else {
			$active = Context::active();
			foreach ( WC()->cart->get_cart() as $key => $line ) {
				$source  = $line[ DraftTransfer::LINE_META ] ?? '';
				$lines[] = array(
					'product_id'    => (int) $line['product_id'],
					'label'         => $line['data']->get_name(),
					'cart_key'      => '' === $source ? $key : null,
					'quantity'      => $line['quantity'],
					'project_id'    => $active[ $source ]['snapshot']['project_id'] ?? null,
					'project_title' => $active[ $source ]['snapshot']['title'] ?? null,
				);
			}
		}
		$changes = array_values( array_filter( $preview['changes'] ?? array(), static fn ( array $line ): bool => $line['before'] > 0 && $line['before'] !== $line['after'] ) );

		$locale = new \Linker\Commerce\Mail\LocaleSwitch();
		$locale->to( \Linker\Commerce\Inquiry\OrderLocale::current( $language ) );
		try {
			$facts = Context::review_facts( $project );
		} finally {
			$locale->back();
		}
		$display      = self::product_cards( array_column( array_merge( $lines, $changes ), 'product_id' ), $language );
		$with_details = static fn ( array $line ): array => $line + ( $display[ $line['product_id'] ] ?? array() );
		return array(
			'schema_version'          => 1,
			'inquiry_form_html'       => ( new \Linker\Commerce\Inquiry\Form() )->planning( $language, $project, $bound, $handoff, $retry ),
			'inquiry_draft_edit'      => array_filter( array_column( $lines, 'cart_key' ) ) ? array(
				'url'        => rest_url( 'wc/store/v1/cart/update-item' ),
				'nonce'      => wp_create_nonce( 'wc_store_api' ),
				'rest_nonce' => wp_create_nonce( 'wp_rest' ),
			) : null,
			'inquiry_lines'           => array_map( $with_details, $lines ),
			'inquiry_project_facts'   => $facts,
			'inquiry_changes'         => array_map( $with_details, $changes ),
			'inquiry_phase_conflicts' => $preview['phase_conflicts'] ?? array(),
		);
	}

	/**
	 * Current shop cards for the native planner, keyed by the original Woo identity.
	 *
	 * @param int[]  $ids  Requested product IDs.
	 * @param string $language Page language.
	 * @return array<int,array<string,string>>
	 * @phpstan-impure Current Woo publication and visibility can change during a request.
	 */
	public static function product_cards( array $ids, string $language ): array {
		if ( array() === $ids ) {
			return array();
		}
		$lang       = ProductText::lang( $language );
		$translated = array();
		$published  = Publication::published_ids(
			static function () use ( $ids, $lang, &$translated ): array {
				$posts = get_posts(
					array(
						'post_type'        => 'product',
						'post_status'      => 'publish',
						'post__in'         => array_values( array_unique( $ids ) ),
						'posts_per_page'   => -1,
						'suppress_filters' => true,
						'lang'             => '',
					)
				);
				foreach ( $posts as $post ) {
					$id                = $post->ID;
					$translated[ $id ] = function_exists( 'pll_get_post' ) ? (int) pll_get_post( $id, $lang ) : $id;
				}
				return array_values( array_unique( array_merge( array_keys( $translated ), array_values( $translated ), array_map( array( Publication::class, 'canonical_id' ), array_keys( $translated ) ) ) ) );
			}
		);
		$public     = array();
		foreach ( $published as $id ) {
			$product = wc_get_product( $id );
			if ( $product instanceof \WC_Product && 'hidden' !== $product->get_catalog_visibility() && '' === get_post_field( 'post_password', $id ) && ! EngineeringReference::is_reference( $id ) ) {
				$public[ $id ] = $product;
			}
		}
		$cards  = array();
		$locale = new \Linker\Commerce\Mail\LocaleSwitch();
		$locale->to( ProductText::locale( $lang ) );
		try {
			foreach ( $translated as $id => $twin ) {
				$source = Publication::canonical_id( $id );
				if ( ! isset( $public[ $source ], $public[ $id ], $public[ $twin ] ) ) {
					continue;
				}
				$product      = $public[ $twin ];
				$fact         = Materials::card_facts( $product, 1 )[0] ?? null;
				$cards[ $id ] = array_filter(
					array(
						'sku'          => (string) $public[ $source ]->get_sku(),
						'availability' => $public[ $source ]->is_in_stock() ? 'in-stock' : 'unavailable',
						'label'        => $product->get_name(),
						'product_url'  => (string) get_permalink( $twin ),
						'image_url'    => (string) wp_get_attachment_image_url( (int) $product->get_image_id(), 'woocommerce_thumbnail' ),
						'highlight'    => $fact ? $fact['label'] . ' · ' . $fact['value'] : wp_strip_all_tags( $product->get_short_description(), true ),
					)
				);
			}
		} finally {
			$locale->back();
		}
		return $cards;
	}

	/**
	 * Recover an explicitly continued guided inquiry from this native Woo session.
	 *
	 * @param mixed  $previous Prior filter outcome.
	 * @param string $handle    Opaque retry handle.
	 * @param string $binding   Owned project and revision.
	 * @param string $report    Selected report for this retry.
	 * @return array<string,mixed>|null
	 */
	public function inquiry_retry( mixed $previous, string $handle, string $binding, string $report ): ?array {
		unset( $previous );
		wc_load_cart();
		$retry = \Linker\Commerce\Inquiry\CheckoutRetry::read( $handle );
		if ( null === $retry || ( $retry['fields'][ Context::PROJECT_FIELD ] ?? null ) !== $binding || InquiryTransfer::read( $retry['fields'][ InquiryTransfer::FIELD ] ?? null )?->report !== $report ) {
			return null;
		}
		return $retry + array( 'retry' => $handle );
	}
}
