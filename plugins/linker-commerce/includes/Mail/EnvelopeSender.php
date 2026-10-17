<?php
/**
 * The envelope identity of all WordPress mail.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Mail;

use Linker\Commerce\Settings\Options;
use PHPMailer\PHPMailer\PHPMailer;

/**
 * Uses PHPMailer's native envelope sender, after WordPress resolves From.
 * Hostinger's mail() transport uses this as -f (the receiving server writes
 * Return-Path); a custom Return-Path header would not set the envelope.
 */
final class EnvelopeSender {

	/**
	 * Sets up the policy.
	 *
	 * @param Options $options Site mail settings.
	 */
	public function __construct( private readonly Options $options ) {}

	/**
	 * Applies on every wp_mail delivery, including a reused mailer and retries.
	 *
	 * @param PHPMailer $mailer WordPress's initialized mailer.
	 */
	public function apply( PHPMailer $mailer ): void {
		$mailer->Sender = $this->options->envelope_sender(); // phpcs:ignore WordPress.NamingConventions.ValidVariableName.UsedPropertyNotSnakeCase -- PHPMailer's native envelope property.
	}
}
