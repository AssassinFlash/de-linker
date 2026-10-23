<?php
/**
 * The accounts waiting for the team's approval.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Registration;

use Linker\Commerce\Digest\Block;
use WP_User;

/**
 * The first block of the daily digest (docs/specs/74-daily-digest.md, the
 * block interface): only pending plain customers, oldest first, each with
 * the way to its review card. The set agrees with the staff queue: an absent
 * state defaults to pending. A separate summary line keeps restricted accounts
 * awaiting customer information visible without adding them to the pending
 * count. Approval defines both identity and status. The digest's
 * assembly reaches this block through the linker_commerce_digest_blocks filter
 * (Registration\Module), which puts it in front of the digest's own blocks.
 */
final class PendingApprovals implements Block {

	/**
	 * Pending entries, reused between the title and body.
	 *
	 * @var list<array{label: string, url: string, link_text: string, detail: string}>
	 */
	private array $pending = array();

	/**
	 * Restricted is a separate follow-up set, never part of the red flag.
	 *
	 * @var int
	 */
	private int $restricted = 0;

	/**
	 * User-data epoch of this request's block contents.
	 *
	 * @var string
	 */
	private string $version = '';

	/**
	 * Stable identifier of the block.
	 */
	public const ID = 'pending_accounts';

	/**
	 * Sets up the block.
	 *
	 * @param Approval $approval The account approval rule.
	 */
	public function __construct( private readonly Approval $approval = new Approval() ) {}

	/**
	 * Stable identifier of the block.
	 */
	public function id(): string {
		return self::ID;
	}

	/**
	 * Heading of the block.
	 */
	public function title(): string {
		return __( 'Accounts waiting for approval', 'linker-commerce' ) . ' (' . number_format_i18n( $this->pending_count() ) . ')';
	}

	/**
	 * Applications awaiting staff approval, excluding decorative summary rows.
	 */
	public function pending_count(): int {
		$this->load();
		return count( $this->pending );
	}

	/**
	 * Only pending customers, oldest first, also when cron has no logged-in user.
	 *
	 * @return list<array{label: string, url: string, link_text: string, detail: string}>
	 */
	public function entries(): array {
		$this->load();
		$entries = $this->pending;
		if ( array() === $entries ) {
			$entries[] = array(
				'label'     => $this->empty_text(),
				'url'       => '',
				'link_text' => '',
				'detail'    => '',
			);
		}
		$entries[] = array(
			'label'     => sprintf( /* translators: %s: number of restricted accounts awaiting information. */ __( 'Restricted, awaiting customer information: %s', 'linker-commerce' ), number_format_i18n( $this->restricted ) ),
			'url'       => add_query_arg( 'status', Approval::RESTRICTED, AccountsAdmin::url() ),
			'link_text' => __( 'View restricted accounts', 'linker-commerce' ),
			'detail'    => '',
		);
		return $entries;
	}

	/** Reuses one customer read while rendering the block's heading and entries. */
	private function load(): void {
		$version = get_current_blog_id() . ':' . wp_cache_get_last_changed( 'users' );
		if ( $this->version === $version ) {
			return;
		}
		$this->pending    = array();
		$this->restricted = 0;
		foreach ( get_users(
			array(
				'role'    => 'customer',
				'orderby' => 'registered',
				'order'   => 'ASC',
			)
		) as $customer ) {
			if ( ! $customer instanceof WP_User || ! $this->approval->is_subject( $customer->ID ) ) {
				continue;
			}
			$status = $this->approval->status( $customer->ID );
			if ( Approval::PENDING === $status ) {
				$this->pending[] = $this->entry( $customer );
			} elseif ( Approval::RESTRICTED === $status ) {
				++$this->restricted;
			}
		}
		$this->version = $version;
	}

	/**
	 * The sentence a block with no open items shows.
	 */
	public function empty_text(): string {
		return __( 'No account is waiting for approval.', 'linker-commerce' );
	}

	/**
	 * One account as the digest lists it: the company, when it registered and
	 * the way to its review card. The date is written as an
	 * unambiguous day, not through the site's date format option: the digest
	 * speaks the site's language, and that option need not be that language's
	 * format (docs/specs/74-daily-digest.md, the mail's own rule).
	 *
	 * @param WP_User $customer The account.
	 * @return array{label: string, url: string, link_text: string, detail: string}
	 */
	private function entry( WP_User $customer ): array {
		$company = (string) get_user_meta( $customer->ID, 'billing_company', true );
		return array(
			'label'     => '' !== $company ? $company : $customer->display_name,
			'url'       => AccountsAdmin::url( $customer->ID ),
			'link_text' => __( 'Open the customer', 'linker-commerce' ),
			'detail'    => sprintf(
				/* translators: %s: the day and time the account registered. */
				__( 'Registered on %s', 'linker-commerce' ),
				(string) mysql2date( 'Y-m-d H:i', $customer->user_registered )
			),
		);
	}
}
