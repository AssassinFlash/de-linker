<?php
/**
 * Tests for the registration module's hooks.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Registration;

use Linker\Commerce\Digest\Block;
use Linker\Commerce\Registration\AddressForm;
use Linker\Commerce\Registration\Approval;
use Linker\Commerce\Registration\ApprovalAdmin;
use Linker\Commerce\Registration\BillingVatField;
use Linker\Commerce\Registration\BotGuard;
use Linker\Commerce\Registration\CountryField;
use Linker\Commerce\Registration\Emails\ApprovedEmail;
use Linker\Commerce\Registration\Emails\NewCustomerEmail;
use Linker\Commerce\Registration\Emails\RegistrationReceivedEmail;
use Linker\Commerce\Registration\Emails\RejectedEmail;
use Linker\Commerce\Registration\Emails\RestrictedEmail;
use Linker\Commerce\Registration\Emails\VatReviewEmail;
use Linker\Commerce\Registration\Fields;
use Linker\Commerce\Registration\Module;
use Linker\Commerce\Registration\PendingApprovals;
use Linker\Commerce\Registration\RoleField;
use Linker\Commerce\Registration\VatProfile;
use Linker\Commerce\Registration\ViesClient;
use Linker\Commerce\Settings\Options;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Tests for Module.
 *
 * @covers \Linker\Commerce\Registration\Module
 */
final class ModuleTest extends TestCase {

	/**
	 * The module under test.
	 *
	 * @var Module
	 */
	private Module $module;

	/**
	 * Its field classes.
	 *
	 * @var array{0: Fields, 1: BillingVatField, 2: AddressForm}
	 */
	private array $parts;

	/**
	 * A module with real parts.
	 */
	public function setUp(): void {
		parent::setUp();
		$vat          = new VatProfile( new ViesClient(), new \Linker\Commerce\Tests\Fixtures\VatNoticeMemory() );
		$this->parts  = array( new Fields( $vat ), new BillingVatField( $vat ), new AddressForm() );
		$this->module = new Module( '/plugin/linker-commerce.php', new Options(), $this->parts[0], $this->parts[1], $this->parts[2] );
	}

	/** The registration, VAT, read-only user-screen links and email hooks. */
	public function test_register_adds_the_hooks(): void {
		[ $fields, $vat_field, $address ] = $this->parts;

		WP_Mock::expectActionAdded( 'woocommerce_register_form_start', array( $fields, 'render' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_process_registration_errors', array( $fields, 'validate' ) );
		WP_Mock::expectActionAdded( 'woocommerce_created_customer', array( $fields, 'save' ), 5 );
		// The public form's traps and the refusal that runs after the fields
		// but before WooCommerce creates the account (#225).

		// @phpstan-ignore argument.type (an AnyInstance callback, see expect_action_on_any)
		WP_Mock::expectActionAdded( 'woocommerce_register_form', array( new WP_Mock\Matcher\AnyInstance( BotGuard::class ), 'fields' ) );
		// @phpstan-ignore argument.type (an AnyInstance callback, see expect_action_on_any)
		WP_Mock::expectFilterAdded( 'woocommerce_process_registration_errors', array( new WP_Mock\Matcher\AnyInstance( BotGuard::class ), 'validate' ), 20 );
		// @phpstan-ignore argument.type (an AnyInstance callback, see expect_action_on_any)
		WP_Mock::expectFilterAdded( 'woocommerce_form_field_linker_country', array( new WP_Mock\Matcher\AnyInstance( CountryField::class ), 'render' ), 10, 4 );
		// @phpstan-ignore argument.type (an AnyInstance callback, see expect_action_on_any)
		WP_Mock::expectFilterAdded( 'woocommerce_form_field_linker_role', array( new WP_Mock\Matcher\AnyInstance( RoleField::class ), 'render' ), 10, 4 );
		WP_Mock::expectFilterAdded( 'woocommerce_billing_fields', array( $vat_field, 'billing_fields' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_admin_billing_fields', array( $vat_field, 'admin_billing_fields' ) );
		WP_Mock::expectActionAdded( 'woocommerce_admin_order_data_after_billing_address', array( $vat_field, 'admin_order_verdict' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_customer_meta_fields', array( $vat_field, 'profile_fields' ) );
		WP_Mock::expectActionAdded( 'woocommerce_customer_save_address', array( $vat_field, 'after_address_saved' ), 10, 2 );
		WP_Mock::expectActionAdded( 'woocommerce_checkout_create_order', array( $vat_field, 'on_inquiry' ) );
		WP_Mock::expectActionAdded( 'woocommerce_before_customer_object_save', array( $vat_field, 'normalize' ) );
		WP_Mock::expectFilterAdded( 'option_woocommerce_default_country', array( $address, 'base_location' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_get_country_locale', array( $address, 'country_locale' ) );
		// @phpstan-ignore argument.type (an AnyInstance callback, see expect_action_on_any)
		WP_Mock::expectFilterAdded( 'authenticate', array( new WP_Mock\Matcher\AnyInstance( Approval::class ), 'gate_login' ), 100 );
		// @phpstan-ignore argument.type (an AnyInstance callback, see expect_action_on_any)
		WP_Mock::expectFilterAdded( 'login_errors', array( new WP_Mock\Matcher\AnyInstance( Approval::class ), 'login_errors' ), 20 );
		// @phpstan-ignore argument.type (an AnyInstance callback, see expect_action_on_any)
		WP_Mock::expectFilterAdded( 'manage_users_columns', array( new WP_Mock\Matcher\AnyInstance( ApprovalAdmin::class ), 'column_header' ) );
		// @phpstan-ignore argument.type (an AnyInstance callback, see expect_action_on_any)
		WP_Mock::expectFilterAdded( 'manage_users_custom_column', array( new WP_Mock\Matcher\AnyInstance( ApprovalAdmin::class ), 'column_cell' ), 10, 3 );
		// @phpstan-ignore argument.type (an AnyInstance callback, see expect_action_on_any)
		WP_Mock::expectFilterAdded( 'user_row_actions', array( new WP_Mock\Matcher\AnyInstance( ApprovalAdmin::class ), 'row_action' ), 10, 2 );
		// @phpstan-ignore argument.type (an AnyInstance callback, see expect_action_on_any)
		WP_Mock::expectActionAdded( 'edit_user_profile', array( new WP_Mock\Matcher\AnyInstance( ApprovalAdmin::class ), 'profile_block' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_email_actions', array( $this->module, 'email_actions' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_email_classes', array( $this->module, 'add_emails' ) );
		WP_Mock::expectFilterAdded( 'linker_commerce_digest_blocks', array( $this->module, 'digest_blocks' ) );

		$this->module->register();

		$this->assertConditionsMet();
	}

	/**
	 * The digest's assembly gets the waiting-accounts block in front of its own
	 * blocks (docs/specs/74-daily-digest.md: the owner's approvals lead the email).
	 */
	public function test_digest_blocks_puts_the_waiting_accounts_first(): void {
		$own    = array( $this->block( 'digest_one' ), $this->block( 'digest_two' ) );
		$blocks = $this->module->digest_blocks( $own );

		$this->assertInstanceOf( PendingApprovals::class, $blocks[0] ?? null );
		$this->assertSame( $own, array_slice( $blocks, 1 ), 'The digest\'s own blocks keep their order behind it.' );
	}

	/**
	 * A block of the digest's own, as its assembly builds them.
	 *
	 * @param string $id Block id.
	 */
	private function block( string $id ): Block {
		return new class( $id ) implements Block {
			/**
			 * Sets up the stub.
			 *
			 * @param string $id Block id.
			 */
			public function __construct( private readonly string $id ) {}

			/**
			 * Stable identifier of the block.
			 */
			public function id(): string {
				return $this->id;
			}

			/**
			 * Heading of the block.
			 */
			public function title(): string {
				return '';
			}

			/**
			 * The open items.
			 */
			public function entries(): array {
				return array();
			}

			/**
			 * The sentence a block with no open items shows.
			 */
			public function empty_text(): string {
				return '';
			}
		};
	}

	/**
	 * WooCommerce sends the notifications on the registration and verdict-change actions; the
	 * actions fired in code carry the same names.
	 */
	public function test_email_actions_and_classes(): void {
		$this->assertSame( array( 'other', 'linker_commerce_customer_registered', 'linker_commerce_vat_status_changed', Approval::CHANGED_ACTION ), $this->module->email_actions( array( 'other' ) ) );
		$this->assertSame( 'linker_commerce_customer_registered', Fields::REGISTERED_ACTION );
		$this->assertSame( 'linker_commerce_vat_status_changed', VatProfile::CHANGED_ACTION );

		$this->plain_text();
		WP_Mock::userFunction( 'plugin_dir_path', array( 'return' => '/plugin/' ) );
			$this->expect_action_on_any( Fields::REGISTERED_ACTION . '_notification', NewCustomerEmail::class, 'trigger' );
			$this->expect_action_on_any( Fields::REGISTERED_ACTION . '_notification', RegistrationReceivedEmail::class, 'trigger' );
		$this->expect_action_on_any( VatProfile::CHANGED_ACTION . '_notification', VatReviewEmail::class, 'trigger', 10, 3 );
		$this->expect_action_on_any( Approval::CHANGED_ACTION . '_notification', ApprovedEmail::class, 'trigger', 10, 4 );
		$this->expect_action_on_any( Approval::CHANGED_ACTION . '_notification', RestrictedEmail::class, 'trigger', 10, 4 );
		$this->expect_action_on_any( Approval::CHANGED_ACTION . '_notification', RejectedEmail::class, 'trigger', 10, 4 );
		$emails = $this->module->add_emails( array() );
			$this->assertInstanceOf( NewCustomerEmail::class, $emails[ NewCustomerEmail::class ] );
			$this->assertInstanceOf( RegistrationReceivedEmail::class, $emails[ RegistrationReceivedEmail::class ] );
		$this->assertInstanceOf( VatReviewEmail::class, $emails[ VatReviewEmail::class ] );
		$this->assertInstanceOf( ApprovedEmail::class, $emails[ ApprovedEmail::class ] );
		$this->assertInstanceOf( RestrictedEmail::class, $emails[ RestrictedEmail::class ] );
		$this->assertInstanceOf( RejectedEmail::class, $emails[ RejectedEmail::class ] );
	}
}
