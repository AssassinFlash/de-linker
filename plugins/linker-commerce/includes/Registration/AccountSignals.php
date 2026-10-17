<?php
/**
 * Explainable review clues, independent of the approval decision.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Registration;

/** Existing VAT evidence and explicit clues; none automatically approves or rejects. */
final class AccountSignals {

	/**
	 * Initial recognized providers from the owner-selected variant C:
	 * docs/prototypes/2026-10-17-accounts/accounts-prototype.js, FREEMAIL.
	 * This is a recognition list, not a claim that every other domain is a business.
	 */
	private const FREE_EMAIL = array( 'gmail.com', 'gmx.com', 'gmx.de', 'web.de', 'outlook.com', 'hotmail.com', 'yahoo.com', 'qq.com', '163.com', 'icloud.com' );

	/**
	 * Providers are replaceable so fixtures use reserved example.test domains.
	 *
	 * @param array $free_email_domains Recognized providers.
	 * @phpstan-param list<string> $free_email_domains
	 */
	public function __construct( private readonly array $free_email_domains = self::FREE_EMAIL ) {}

	/**
	 * The email domain is a verification lead, never a verified company website.
	 *
	 * @param string $email Login email.
	 */
	public function website_from_email( string $email ): string {
		$domain = $this->email_domain( $email );
		return '' === $domain || in_array( $domain, $this->free_email_domains, true ) ? '' : esc_url_raw( 'https://' . $domain );
	}

	/**
	 * Signals grounded in the saved account, without another model or network call.
	 *
	 * @param int    $user_id Customer.
	 * @param string $company Company as entered.
	 * @param string $email   Login email.
	 * @return list<array{tone: string, text: string}>
	 */
	public function for_account( int $user_id, string $company, string $email ): array {
		$domain = $this->email_domain( $email );
		$free   = in_array( $domain, $this->free_email_domains, true );
		$clues  = array(
			array(
				'tone' => $free ? 'warning' : 'info',
				'text' => sprintf(
					/* translators: %s: email domain. */
					$free ? __( 'Free email provider: %s', 'linker-commerce' ) : __( 'Email domain: %s (not verified)', 'linker-commerce' ),
					$domain
				),
			),
		);
		// Literal patterns of the selected prototype; no customer identity is
		// needed to exercise them. A match only prompts a human check.
		if ( preg_match( '/\b(?:gsa\s+search|what\s+is|seo)\b|https?:\/\/|www\./iu', $company, $match ) ) {
			$clues[] = array(
				'tone' => 'warning',
				'text' => sprintf( /* translators: %s: matched text in the company name. */ __( 'Possible automated registration: company name contains "%s".', 'linker-commerce' ), $match[0] ),
			);
		} else {
			$clues[] = array(
				'tone' => 'info',
				'text' => __( 'No suspicious company-name pattern found. Please verify the company.', 'linker-commerce' ),
			);
		}
		$vat     = (string) get_user_meta( $user_id, VatProfile::STATUS_META, true );
		$clues[] = array(
			'tone' => VatProfile::VALID === $vat ? 'success' : 'info',
			'text' => VatProfile::label( $vat ),
		);
		return $clues;
	}

	/**
	 * Extracts the domain without inferring anything about its owner.
	 *
	 * @param string $email Login email.
	 */
	private function email_domain( string $email ): string {
		$at = strrchr( $email, '@' );
		return strtolower( false === $at ? '' : substr( $at, 1 ) );
	}
}
