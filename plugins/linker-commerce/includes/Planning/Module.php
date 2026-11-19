<?php
/**
 * Native Woo draft, inquiry and report-consumer integration.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Planning;

/** All visual output remains native semantic data; no page template or CSS. */
final class Module {
	/** Register native product/context lifecycle and private file access. */
	public function register(): void {
		$context = new Context();
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
			foreach ( WC()->cart->get_cart() as $line ) {
				$source  = $line[ DraftTransfer::LINE_META ] ?? '';
				$lines[] = array(
					'product_id'    => (int) $line['product_id'],
					'label'         => $line['data']->get_name(),
					'quantity'      => $line['quantity'],
					'project_id'    => $active[ $source ]['snapshot']['project_id'] ?? null,
					'project_title' => $active[ $source ]['snapshot']['title'] ?? null,
				);
			}
		}
		return array(
			'schema_version'          => 1,
			'inquiry_form_html'       => ( new \Linker\Commerce\Inquiry\Form() )->planning( $language, $project, $bound, $handoff, $retry ),
			'inquiry_lines'           => $lines,
			'inquiry_changes'         => array_values( array_filter( $preview['changes'] ?? array(), static fn ( array $line ): bool => $line['before'] > 0 && $line['before'] !== $line['after'] ) ),
			'inquiry_phase_conflicts' => $preview['phase_conflicts'] ?? array(),
		);
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
