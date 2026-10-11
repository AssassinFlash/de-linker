<?php
/**
 * Tests for the Proforma module's hooks.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Proforma;

use Linker\Commerce\Account\PrivateFiles;
use Linker\Commerce\Gating\CommerceState;
use Linker\Commerce\Gating\PriceDisplay;
use Linker\Commerce\Proforma\AdminBox;
use Linker\Commerce\Proforma\Document;
use Linker\Commerce\Proforma\Emails\ProformaIssuedEmail;
use Linker\Commerce\Proforma\Issuer;
use Linker\Commerce\Proforma\Module;
use Linker\Commerce\Proforma\Renderer;
use Linker\Commerce\Proforma\Sequence;
use Linker\Commerce\Settings\Options;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Tests for Module.
 *
 * @covers \Linker\Commerce\Proforma\Module
 */
final class ModuleTest extends TestCase {

	/**
	 * The box, its button, the order actions, the list column (both storages) and the email are hooked.
	 */
	public function test_register_adds_the_hooks(): void {
		$options = new Options();
		$box     = new AdminBox( new Issuer( $options, new Sequence(), new Document( $options ), new Renderer( '/plugin/linker-commerce.php' ), new PrivateFiles( Issuer::DIRECTORY ), new PriceDisplay( $this->approved_state() ) ) );
		$module  = new Module( '/plugin/linker-commerce.php', $box );

		WP_Mock::expectActionAdded( 'add_meta_boxes', array( $box, 'add' ) );
		WP_Mock::expectActionAdded( 'woocommerce_process_shop_order_meta', array( $box, 'process' ), 60 );
		WP_Mock::expectFilterAdded( 'woocommerce_order_actions', array( $box, 'order_actions' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_shop_order_list_table_columns', array( $box, 'columns' ) );
		WP_Mock::expectActionAdded( 'woocommerce_shop_order_list_table_custom_column', array( $box, 'column' ), 10, 2 );
		WP_Mock::expectFilterAdded( 'manage_edit-shop_order_columns', array( $box, 'columns' ) );
		WP_Mock::expectActionAdded( 'manage_shop_order_posts_custom_column', array( $box, 'column' ), 10, 2 );
		WP_Mock::expectFilterAdded( 'woocommerce_email_actions', array( $module, 'email_actions' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_email_classes', array( $module, 'add_email' ) );

		$module->register();

		$this->assertSame( array( 'woocommerce_order_status_inquiry-received_to_proforma-issued' ), $module->email_actions( array() ) );
		$this->plain_text();
		WP_Mock::userFunction( 'plugin_dir_path', array( 'return' => '/plugin/' ) );
		$this->expect_action_on_any( 'woocommerce_order_status_inquiry-received_to_proforma-issued_notification', ProformaIssuedEmail::class, 'trigger', 10, 2 );
		$this->assertArrayHasKey( ProformaIssuedEmail::class, $module->add_email( array() ) );
		$this->assertConditionsMet();
	}
}
