<?php
/**
 * Internal authentication health in the daily digest (#297).
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Health;

use Linker\Commerce\Digest\Block;
use Linker\Commerce\Mail\InternalSmtp;
use Linker\Commerce\Mail\SmtpOutcome;

/**
 * One warning per digest while configuration is absent, invalid or mismatched.
 * No additional alert mail is sent for the fallback itself.
 */
final class InternalMail implements Block {

	/**
	 * Sets up the configuration health check.
	 *
	 * @param InternalSmtp $smtp    The same configuration rule as the Outbox.
	 * @param SmtpOutcome  $outcome The last SMTP result.
	 */
	public function __construct( private readonly InternalSmtp $smtp = new InternalSmtp(), private readonly SmtpOutcome $outcome = new SmtpOutcome() ) {}

	/**
	 * Stable digest block identifier.
	 */
	public function id(): string {
		return 'internal_mail';
	}

	/**
	 * Heading in the digest's language.
	 */
	public function title(): string {
		return __( 'Internal mail authentication', 'linker-commerce' );
	}

	/**
	 * A single explicit fallback diagnostic, without configuration values.
	 *
	 * @return list<array{label: string, url: string, link_text: string, detail: string}>
	 */
	public function entries(): array {
		$last = $this->outcome->last();
		if ( null !== $last && 'failure' === $last['status'] ) {
			return array(
				array(
					'label'     => __( 'The last SMTP attempt failed.', 'linker-commerce' ),
					'url'       => '',
					'link_text' => '',
					'detail'    => sprintf(
						/* translators: 1: UTC timestamp, 2: fixed diagnostic category. */
						__( 'Last attempt: %1$s UTC. Reason: %2$s. Internal notifications fall back to PHP mail().', 'linker-commerce' ),
						gmdate( 'Y-m-d H:i:s', $last['at'] ),
						$last['reason']
					),
				),
			);
		}
		if ( $this->smtp->authenticated() ) {
			return array();
		}
		return array(
			array(
				'label'     => __( 'Internal mail not authenticated.', 'linker-commerce' ),
				'url'       => '',
				'link_text' => '',
				'detail'    => __( 'Internal notifications use PHP mail(). Check the SMTP configuration on the server.', 'linker-commerce' ),
			),
		);
	}

	/**
	 * Configured does not claim a successful remote delivery.
	 */
	public function empty_text(): string {
		$last = $this->outcome->last();
		return null !== $last && 'success' === $last['status']
			? sprintf(
				/* translators: %s: UTC timestamp. */
				__( 'Last SMTP attempt succeeded at %s UTC.', 'linker-commerce' ),
				gmdate( 'Y-m-d H:i:s', $last['at'] )
			)
			: __( 'SMTP configured; no SMTP attempt has been recorded.', 'linker-commerce' );
	}
}
