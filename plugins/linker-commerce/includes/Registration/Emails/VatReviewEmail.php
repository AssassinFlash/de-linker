<?php
/**
 * Notification of a changed VAT check, to the team.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Registration\Emails;

use Linker\Commerce\Mail\TeamEmail;
use Linker\Commerce\Registration\VatProfile;
use Linker\Commerce\Settings\Options;
use WP_User;

/**
 * Sent to the team mailbox when the VIES verdict of a customer's VAT ID
 * changes (only then: docs/specs/11-commerce.md, Mail).
 */
final class VatReviewEmail extends TeamEmail {

	/**
	 * Email id.
	 */
	public const ID = 'linker_vat_review';

	/**
	 * The verdict before and after the change.
	 *
	 * @var array{previous: string, current: string}
	 */
	private array $change = array(
		'previous' => '',
		'current'  => '',
	);

	/**
	 * Sets up the email.
	 *
	 * @param string  $plugin_file Absolute path of the main plugin file.
	 * @param Options $options     The plugin settings.
	 */
	public function __construct( string $plugin_file, Options $options ) {
		$this->id            = self::ID;
		$this->title         = __( 'VAT check changed', 'linker-commerce' );
		$this->description   = __( 'Sent to the internal notification address, with blind copies, when the VIES verdict of a customer changes.', 'linker-commerce' );
		$this->template_html = 'emails/linker-vat-review.php';
		$this->placeholders  = array( '{company}' => '' );
		add_action( VatProfile::CHANGED_ACTION . '_notification', array( $this, 'trigger' ), 10, 3 );
		parent::__construct( $plugin_file, $options );
	}

	/**
	 * Sends the notification about a changed verdict.
	 *
	 * @param int    $customer_id Customer.
	 * @param string $previous    Verdict before.
	 * @param string $current     Verdict now.
	 */
	public function trigger( $customer_id, $previous = '', $current = '' ): void {
		$user = get_userdata( (int) $customer_id );
		if ( ! $user instanceof WP_User ) {
			return;
		}
		$this->change                    = array(
			'previous' => (string) $previous,
			'current'  => (string) $current,
		);
		$this->placeholders['{company}'] = (string) get_user_meta( $user->ID, 'billing_company', true );
		$this->notify( $user );
	}

	/**
	 * Default subject.
	 */
	public function get_default_subject() {
		/* translators: {company}: the customer's company. */
		return __( 'VAT check changed: {company}', 'linker-commerce' );
	}

	/**
	 * Default heading.
	 */
	public function get_default_heading() {
		return __( 'VAT check changed', 'linker-commerce' );
	}

	/**
	 * The customer and the change for the template.
	 *
	 * @return array<string, mixed>
	 */
	protected function template_args(): array {
		return array(
			'customer' => $this->object,
			'previous' => $this->change['previous'],
			'current'  => $this->change['current'],
		);
	}
}
