<?php
/**
 * Hooks of the registration module.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Registration;

use Linker\Commerce\Digest\Block as DigestBlock;
use Linker\Commerce\Registration\Emails\ApprovedEmail;
use Linker\Commerce\Registration\Emails\NewCustomerEmail;
use Linker\Commerce\Registration\Emails\RegistrationReceivedEmail;
use Linker\Commerce\Registration\Emails\RejectedEmail;
use Linker\Commerce\Registration\Emails\RestrictedEmail;
use Linker\Commerce\Registration\Emails\VatReviewEmail;
use Linker\Commerce\Settings\Options;

/**
 * The registration fields, the VAT ID as a billing field with its VIES check,
 * the three approval actions in WordPress's own screens and the notifications
 * about customers.
 */
final class Module {

	/**
	 * Sets up the module.
	 *
	 * @param string           $plugin_file Absolute path of the main plugin file.
	 * @param Options          $options     The plugin settings.
	 * @param Fields           $fields      The registration fields.
	 * @param BillingVatField  $vat_field   The VAT ID billing field.
	 * @param AddressForm      $address     The address form rules.
	 * @param Approval         $approval    The account approval rule.
	 * @param ApprovalAdmin    $admin       The approval actions in WordPress's screens.
	 * @param PendingApprovals $pending     The waiting accounts of the daily digest.
	 */
	public function __construct(
		private readonly string $plugin_file,
		private readonly Options $options,
		private readonly Fields $fields,
		private readonly BillingVatField $vat_field,
		private readonly AddressForm $address,
		private readonly Approval $approval = new Approval(),
		private readonly ApprovalAdmin $admin = new ApprovalAdmin( new Approval() ),
		private readonly PendingApprovals $pending = new PendingApprovals()
	) {}

	/**
	 * Adds the module's hooks.
	 */
	public function register(): void {
		add_action( 'woocommerce_register_form_start', array( $this->fields, 'render' ) );
		add_filter( 'woocommerce_process_registration_errors', array( $this->fields, 'validate' ) );
		add_action( 'woocommerce_created_customer', array( $this->fields, 'save' ), 5 );

		add_filter( 'woocommerce_billing_fields', array( $this->vat_field, 'billing_fields' ) );
		add_filter( 'woocommerce_admin_billing_fields', array( $this->vat_field, 'admin_billing_fields' ) );
		add_action( 'woocommerce_admin_order_data_after_billing_address', array( $this->vat_field, 'admin_order_verdict' ) );
		add_filter( 'woocommerce_customer_meta_fields', array( $this->vat_field, 'profile_fields' ) );
		add_action( 'woocommerce_customer_save_address', array( $this->vat_field, 'after_address_saved' ), 10, 2 );
		add_action( 'woocommerce_checkout_create_order', array( $this->vat_field, 'on_inquiry' ) );
		add_action( 'woocommerce_before_customer_object_save', array( $this->vat_field, 'normalize' ) );

		add_filter( 'option_woocommerce_default_country', array( $this->address, 'base_location' ) );
		add_filter( 'woocommerce_get_country_locale', array( $this->address, 'country_locale' ) );

		$this->approval->register();
		$this->admin->register();
		add_filter( 'linker_commerce_digest_blocks', array( $this, 'digest_blocks' ) );

		add_filter( 'woocommerce_email_actions', array( $this, 'email_actions' ) );
		add_filter( 'woocommerce_email_classes', array( $this, 'add_emails' ) );
	}

	/**
	 * Puts the waiting accounts in front of the daily digest's own blocks: the
	 * owner's approvals lead the email (docs/specs/74-daily-digest.md, the
	 * block interface). The digest's assembly applies this filter; without the
	 * digest the filter has no reader and this adds nothing.
	 *
	 * @param DigestBlock[] $blocks The digest's blocks.
	 * @return DigestBlock[]
	 */
	public function digest_blocks( array $blocks ): array {
		array_unshift( $blocks, $this->pending );
		return $blocks;
	}

	/**
	 * WooCommerce sends emails only on the actions in this list.
	 *
	 * @param string[] $actions Actions.
	 * @return string[]
	 */
	public function email_actions( array $actions ): array {
		$actions[] = Fields::REGISTERED_ACTION;
		$actions[] = VatProfile::CHANGED_ACTION;
		$actions[] = Approval::CHANGED_ACTION;
		return $actions;
	}

	/**
	 * Adds the notifications about customers.
	 *
	 * @param array<string, object> $emails Email objects by class.
	 * @return array<string, object>
	 */
	public function add_emails( array $emails ): array {
		$emails[ NewCustomerEmail::class ]          = new NewCustomerEmail( $this->plugin_file, $this->options );
		$emails[ RegistrationReceivedEmail::class ] = new RegistrationReceivedEmail( $this->plugin_file );
		$emails[ VatReviewEmail::class ]            = new VatReviewEmail( $this->plugin_file, $this->options );
		$emails[ ApprovedEmail::class ]             = new ApprovedEmail( $this->plugin_file );
		$emails[ RestrictedEmail::class ]           = new RestrictedEmail( $this->plugin_file );
		$emails[ RejectedEmail::class ]             = new RejectedEmail( $this->plugin_file );
		return $emails;
	}
}
