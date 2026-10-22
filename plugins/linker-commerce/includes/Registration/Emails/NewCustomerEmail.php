<?php
/**
 * Notification of a new customer, to the team.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Registration\Emails;

use Linker\Commerce\Mail\TeamEmail;
use Linker\Commerce\Registration\Fields;
use Linker\Commerce\Registration\RegistrationInformation;
use Linker\Commerce\Settings\Options;
use WP_User;
use Linker\Commerce\Mail\Message;
use Linker\Commerce\Mail\Prepared;

/**
 * Sent to the team mailbox when a customer registered (docs/specs/11-commerce.md,
 * journey step 2: "公司'新客户'提醒"), with company, business type and the
 * VAT check.
 */
final class NewCustomerEmail extends TeamEmail {
	/**
	 * Prospective native rows, present only during pre-create capture.
	 *
	 * @var list<array{key:string,label:string,value:string,website:bool}>|null
	 */
	private ?array $preview_rows = null;

	/**
	 * Email id.
	 */
	public const ID = 'linker_new_customer';

	/**
	 * Sets up the email.
	 *
	 * @param string                  $plugin_file Absolute path of the main plugin file.
	 * @param Options                 $options     The plugin settings.
	 * @param RegistrationInformation $information The same field reader as the accounts page.
	 */
	public function __construct( string $plugin_file, Options $options, private readonly RegistrationInformation $information ) {
		$this->id            = self::ID;
		$this->title         = __( 'New customer', 'linker-commerce' );
		$this->description   = __( 'Sent to the internal notification address, with blind copies, when a customer registers.', 'linker-commerce' );
		$this->template_html = 'emails/linker-new-customer.php';
		$this->placeholders  = array( '{company}' => '' );
		add_action( Fields::REGISTERED_ACTION . '_notification', array( $this, 'trigger' ) );
		parent::__construct( $plugin_file, $options );
	}

	/**
	 * Sends the notification about a customer.
	 *
	 * @param int $customer_id Customer.
	 */
	public function trigger( $customer_id ): void {
		$user = get_userdata( (int) $customer_id );
		if ( ! $user instanceof WP_User ) {
			return;
		}
		$this->placeholders['{company}'] = (string) get_user_meta( $user->ID, 'billing_company', true );
		$this->notify( $user );
	}

	/**
	 * Capture the configured native message without a database account or mail.
	 *
	 * @param WP_User              $user Prospective identity, without a password.
	 * @param array<string,string> $values Validated business values.
	 */
	public function preview( WP_User $user, array $values ): ?Message {
		$this->preview_rows              = $this->information->prospective( $values, $user );
		$this->placeholders['{company}'] = $values['billing_company'] ?? '';
		try {
			return Prepared::capture( fn () => $this->notify( $user ) );
		} finally {
			$this->preview_rows = null;
			$this->object       = false;
		}
	}

	/**
	 * Default subject.
	 */
	public function get_default_subject() {
		/* translators: {company}: the customer's company. */
		return __( 'New customer: {company}', 'linker-commerce' );
	}

	/**
	 * Default heading.
	 */
	public function get_default_heading() {
		return __( 'New customer', 'linker-commerce' );
	}

	/**
	 * The customer for the template, with the same registration rows the
	 * accounts page shows (RegistrationInformation, ticket #225).
	 *
	 * @return array<string, mixed>
	 */
	protected function template_args(): array {
		return array(
			'customer'          => $this->object,
			'registration_rows' => $this->preview_rows ?? ( $this->object instanceof WP_User ? $this->information->rows( $this->object ) : array() ),
		);
	}
}
