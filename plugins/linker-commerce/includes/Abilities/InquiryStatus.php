<?php
/**
 * Ability linker/inquiry-status.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Abilities;

use Linker\Commerce\Gating\CommerceState;
use Linker\Commerce\Gating\PriceDisplay;
use Linker\Commerce\Inquiry\Statuses;
use Linker\Commerce\Proforma\Issuer;
use WC_Order;

/**
 * The current customer's inquiries and their four statuses (AGENTS.md §3).
 * Logged-in only; guests are refused by the permission callback.
 */
final class InquiryStatus {

	/**
	 * Ability name.
	 */
	public const NAME = 'linker/inquiry-status';

	/**
	 * Arguments for wp_register_ability(), apart from the category.
	 *
	 * @return array<string, mixed>
	 */
	public function args(): array {
		$inquiry = array(
			'type'                 => 'object',
			'properties'           => array(
				'id'              => array(
					'type'        => 'integer',
					'description' => __( 'Inquiry ID.', 'linker-commerce' ),
				),
				'number'          => array(
					'type'        => 'string',
					'description' => __( 'Inquiry number as the customer sees it.', 'linker-commerce' ),
				),
				'status'          => array(
					'type'        => 'string',
					'description' => __( 'Status slug without the wc- prefix.', 'linker-commerce' ),
				),
				'status_label'    => array(
					'type'        => 'string',
					'description' => __( 'Status name in the page language.', 'linker-commerce' ),
				),
				'date'            => array(
					'type'        => 'string',
					'description' => __( 'Date created, GMT.', 'linker-commerce' ),
				),
				'total'           => array(
					'type'        => 'string',
					'description' => __( 'Amount as stored on the inquiry.', 'linker-commerce' ),
				),
				'proforma_number' => array(
					'type'        => 'string',
					'description' => __( 'Proforma number when one has been issued.', 'linker-commerce' ),
				),
			),
			'required'             => array( 'id', 'number', 'status', 'status_label', 'date' ),
			'additionalProperties' => false,
		);

		return array(
			'label'               => __( 'List my inquiries', 'linker-commerce' ),
			'description'         => __( 'Returns this account\'s inquiries and their status. Requires a logged-in customer.', 'linker-commerce' ),
			'input_schema'        => array(
				'type'                 => 'object',
				'properties'           => array(),
				'additionalProperties' => false,
				// A GET with no parameters means "empty input" (the abilities
				// REST controller reads null without a declared default).
				'default'              => array(),
			),
			'output_schema'       => array(
				'type'                 => 'object',
				'properties'           => array(
					'inquiries' => array(
						'type'  => 'array',
						'items' => $inquiry,
					),
				),
				'required'             => array( 'inquiries' ),
				'additionalProperties' => false,
			),
			'execute_callback'    => array( $this, 'execute' ),
			'permission_callback' => array( $this, 'can_execute' ),
			'meta'                => RestMeta::readonly(),
		);
	}

	/**
	 * Only a logged-in customer may read their inquiries.
	 */
	public function can_execute(): bool {
		return is_user_logged_in();
	}

	/**
	 * This account's inquiries, newest first.
	 *
	 * @param array<string, mixed>|object $input Unused; the schema is empty.
	 * @return array{inquiries: list<array<string, mixed>>}
	 */
	public function execute( $input = array() ): array {
		unset( $input );
		if ( ! is_user_logged_in() ) {
			return array( 'inquiries' => array() );
		}
		$orders = wc_get_orders(
			array(
				'customer_id' => get_current_user_id(),
				'limit'       => -1,
				'orderby'     => 'date',
				'order'       => 'DESC',
			)
		);
		$labels = ( new Statuses() )->names( array() );
		$prices = new PriceDisplay( new CommerceState() );
		$list   = array();
		foreach ( is_array( $orders ) ? $orders : array() as $order ) {
			$list[] = $this->item( $order, $labels, $prices );
		}

		return array( 'inquiries' => $list );
	}

	/**
	 * One inquiry as the ability returns it.
	 *
	 * @param WC_Order              $order  Inquiry.
	 * @param array<string, string> $labels Status key → name.
	 * @param PriceDisplay          $prices The account page's monetary-total rule.
	 * @return array<string, mixed>
	 */
	private function item( WC_Order $order, array $labels, PriceDisplay $prices ): array {
		$status = $order->get_status();
		$key    = 'wc-' . $status;
		$item   = array(
			'id'           => $order->get_id(),
			'number'       => (string) $order->get_order_number(),
			'status'       => $status,
			'status_label' => $labels[ $key ] ?? $status,
			'date'         => (string) $order->get_date_created()?->format( 'c' ),
		);
		// Account-page parity (#414): shows_order_total(), not sees_prices()
		// alone. A pending or restricted account, and an approved account's
		// contact message or unpriced line, get no amount. The field is
		// absent, so English and German stay one payload. The Proforma file
		// is DocumentDownload (#425); this payload does not carry its URL.
		if ( $prices->shows_order_total( $order ) ) {
			$item['total'] = (string) $order->get_total();
		}
		$proforma = (string) $order->get_meta( Issuer::NUMBER_META );
		if ( '' !== $proforma ) {
			$item['proforma_number'] = $proforma;
		}

		return $item;
	}
}
