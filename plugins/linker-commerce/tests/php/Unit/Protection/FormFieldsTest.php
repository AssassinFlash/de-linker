<?php
/**
 * Required native forms cannot promise an unverified review path.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Protection;

use Linker\Commerce\Protection\FormFields;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WP_Mock;

/**
 * Required-policy messages follow the native write gate.
 *
 * @covers \Linker\Commerce\Protection\FormFields
 */
final class FormFieldsTest extends TestCase {
	/** Both business doors keep their required policy in the no-JavaScript explanation. */
	public function test_required_business_forms_explain_the_actual_no_script_path(): void {
		$this->plain_text();
		$previous_mode   = getenv( 'LINKER_PUBLIC_PROTECTION_MODE' );
		$previous_policy = getenv( 'LINKER_BUSINESS_VERIFICATION' );
		// phpcs:disable WordPress.PHP.DiscouragedPHPFunctions.runtime_configuration_putenv -- Test-only policy, restored in finally.
		putenv( 'LINKER_PUBLIC_PROTECTION_MODE=enforce' );
		putenv( 'LINKER_BUSINESS_VERIFICATION=required' );
		try {
			WP_Mock::userFunction( 'wp_is_uuid', array( 'return' => static fn ( string $id ): bool => '' !== $id ) );
			WP_Mock::userFunction( 'wp_generate_uuid4', array( 'return' => '01234567-0123-4123-8123-0123456789ab' ) );
			WP_Mock::userFunction( 'wp_parse_url', array( 'return' => 'linker.test' ) );
			$session = Mockery::mock();
			$session->shouldReceive( 'get' )->with( 'linker_intake_grouped', false )->andReturn( false );
			WP_Mock::userFunction( 'WC', array( 'return' => (object) array( 'session' => $session ) ) );
			foreach ( array( 'contact', 'inquiry' ) as $action ) {
				WP_Mock::expectAction( 'linker_commerce_public_protection_assets' );
				$html = FormFields::render( $action, '01234567-0123-4123-8123-0123456789ab' );
				$this->assertStringContainsString( '<noscript><p>Please enable JavaScript to verify this request, or email sales@de-linker.com.</p></noscript>', $html );
				$this->assertStringNotContainsString( 'submit your inquiry for staff review', $html );
				$this->assertStringContainsString( 'data-linker-protected-action="' . $action . '"', $html );
				$this->assertStringContainsString( 'data-linker-protection-recovery="true"', $html );
				WP_Mock::expectAction( 'linker_commerce_public_protection_assets' );
				$refused = FormFields::render( $action, '01234567-0123-4123-8123-0123456789ab', false, false );
				$this->assertStringNotContainsString( 'data-linker-protection-recovery=', $refused );
				WP_Mock::expectAction( 'linker_commerce_public_protection_assets' );
				$fresh = FormFields::render( $action );
				$this->assertStringNotContainsString( 'data-linker-protection-recovery=', $fresh );
			}
		} finally {
			putenv( false === $previous_mode ? 'LINKER_PUBLIC_PROTECTION_MODE' : 'LINKER_PUBLIC_PROTECTION_MODE=' . $previous_mode );
			putenv( false === $previous_policy ? 'LINKER_BUSINESS_VERIFICATION' : 'LINKER_BUSINESS_VERIFICATION=' . $previous_policy );
		}
		// phpcs:enable WordPress.PHP.DiscouragedPHPFunctions.runtime_configuration_putenv
	}
}
