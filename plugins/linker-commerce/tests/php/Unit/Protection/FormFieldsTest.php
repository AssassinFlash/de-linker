<?php
/**
 * Anonymous native forms and signed-in business submissions.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Protection;

use Linker\Commerce\Protection\FormFields;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Markup for native business and registration forms.
 *
 * @covers \Linker\Commerce\Protection\FormFields
 */
final class FormFieldsTest extends TestCase {

	/** A native form keeps its request identity and exposes the action of its widget. */
	public function test_guest_inquiry_has_a_widget_and_preserves_the_request_id(): void {
		$this->plain_text();
		$id = '01234567-0123-4123-8123-0123456789ab';
		WP_Mock::userFunction( 'is_user_logged_in' )->andReturn( false );
		WP_Mock::userFunction( 'wp_is_uuid' )->with( $id, 4 )->andReturn( true );
		WP_Mock::expectAction( 'linker_commerce_public_protection_assets' );
		$html = FormFields::render( 'inquiry', $id );
		$this->assertStringContainsString( 'name="linker_request_id" value="' . $id . '"', $html );
		$this->assertStringContainsString( 'data-linker-turnstile="inquiry"', $html );
		$this->assertStringContainsString( 'sales@de-linker.com', $html );
		$this->assertStringNotContainsString( 'linker_proof', $html );
	}

	/** A logged-in customer can send a regular inquiry with its native retry identity. */
	public function test_account_has_no_widget(): void {
		$this->plain_text();
		$id = '01234567-0123-4123-8123-0123456789ab';
		WP_Mock::userFunction( 'is_user_logged_in' )->andReturn( true );
		WP_Mock::userFunction( 'wp_is_uuid' )->with( $id, 4 )->andReturn( true );
		$html = FormFields::render( 'contact', $id );
		$this->assertStringContainsString( 'name="linker_request_id"', $html );
		$this->assertStringNotContainsString( 'turnstile', $html );
	}
}
