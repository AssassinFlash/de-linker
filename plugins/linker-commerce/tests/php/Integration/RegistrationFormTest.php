<?php
/**
 * Integration: the two-step registration's fields, mail and bot boundary.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Inquiry\PublicGuard;
use Linker\Commerce\Mail\Throttle;
use Linker\Commerce\Registration\BlockedRegistrations;
use Linker\Commerce\Registration\BotGuard;
use Linker\Commerce\Registration\CustomerRole;
use Linker\Commerce\Registration\Fields;
use Linker\Commerce\Registration\VatProfile;
use Linker\Commerce\Registration\ViesClient;
use Linker\Commerce\Registration\Website;
use WP_Error;

/**
 * Owner ruling 2026-10-17 (AGENTS.md §2) and the field research (#224): the
 * company step with its verification value, the person step, the notification
 * with the same fields as the accounts page, and the shared bot guard before
 * any account or mail exists.
 *
 * @coversNothing
 */
final class RegistrationFormTest extends IntegrationTestCase {

	/**
	 * The fields of a complete registration.
	 *
	 * @param array<string, string> $overrides Values that differ.
	 * @return array<string, string>
	 */
	private function post( array $overrides = array() ): array {
		return array_merge(
			array(
				'billing_company'    => 'Solarbau Beispiel GmbH',
				CustomerRole::META   => 'installer',
				'billing_country'    => 'DE',
				Website::META        => 'example.com',
				VatProfile::VAT_META => '',
				'billing_first_name' => 'Maria',
				'billing_last_name'  => 'Beispiel',
				'email'              => 'tester225-' . self::tag() . '@example.test',
				'password'           => 'Muster-Solar-2026!',
				'register'           => 'Register',
			),
			$overrides
		);
	}

	/**
	 * Clears the posted form.
	 */
	public function tearDown(): void {
		$_POST = array();
		parent::tearDown();
	}

	/**
	 * Validates the fixture's post with a real Fields instance.
	 *
	 * @param array<string, string> $post Posted values.
	 */
	private function fields( array $post ): Fields {
		$_POST  = $post;
		$fields = new Fields( new VatProfile( new ViesClient() ) );
		$this->assertFalse( $fields->validate( new WP_Error() )->has_errors(), 'The fixture is a complete registration.' );
		return $fields;
	}

	/**
	 * A complete registration stores the two-step values, leaves the address
	 * for the Proforma request page, and the team letter carries the same
	 * fields as the accounts page, the website included.
	 */
	public function test_a_registration_saves_the_fields_and_the_team_letter_shows_them(): void {
		update_option( Throttle::OPTION, array_fill( 0, Throttle::PER_MINUTE, time() ), false );
		$post   = $this->post();
		$fields = $this->fields( $post );

		$id = wc_create_new_customer( $post['email'], 'tester225-' . self::tag(), $post['password'] );
		$this->assertIsInt( $id );
		$this->later(
			static function () use ( $id ): void {
				require_once ABSPATH . 'wp-admin/includes/user.php';
				wp_delete_user( $id );
			}
		);
		$marker = self::newest_mail_job();
		$fields->save( $id );

		$customer = new \WC_Customer( $id );
		$this->assertSame( 'Solarbau Beispiel GmbH', $customer->get_billing_company() );
		$this->assertSame( 'Maria', $customer->get_billing_first_name() );
		$this->assertSame( 'Beispiel', $customer->get_billing_last_name() );
		$this->assertSame( 'DE', $customer->get_billing_country() );
		$this->assertSame( 'installer', $customer->get_meta( CustomerRole::META ) );
		$this->assertSame( 'https://example.com', $customer->get_meta( Website::META ) );
		$this->assertSame( '', $customer->get_billing_address_1(), 'The street is collected by the Proforma request page.' );
		$this->assertSame( '', $customer->get_billing_postcode() );
		$this->assertSame( '', $customer->get_billing_city() );

		$team = array_values(
			array_filter(
				$this->jobs_after( $marker ),
				static fn ( array $row ): bool => str_starts_with( $row['subject'], 'New customer: Solarbau Beispiel GmbH' )
			)
		);
		$this->assertCount( 1, $team, 'One team notification.' );
		$body = $team[0]['body'];
		foreach ( array( 'Company name', 'Business type', 'Installer', 'Country / Region', 'Company website', 'VAT ID', 'First name', 'Last name', 'Login email' ) as $label ) {
			$this->assertStringContainsString( $label, $body, 'The team letter reads the same registration fields as the accounts page.' );
		}
		$this->assertStringContainsString( 'https://example.com', $body, 'The website is in the notification.' );
		$this->assertStringNotContainsString( 'Street address', $body );
		$this->assertStringNotContainsString( 'Postcode', $body );
		$this->assertStringContainsString( 'page=linker-accounts', $body, 'The review deep link stays in the letter.' );
	}

	/**
	 * The card needs a website or a VAT ID, and a written website must be an
	 * address; a VAT ID alone is enough.
	 */
	public function test_website_or_vat_id_is_required(): void {
		$_POST  = $this->post(
			array(
				Website::META        => '',
				VatProfile::VAT_META => '',
			)
		);
		$errors = ( new Fields( new VatProfile( new ViesClient() ) ) )->validate( new WP_Error() );
		$this->assertContains( Fields::ONE_OF, $errors->get_error_codes() );

		$_POST  = $this->post( array( Website::META => 'not a site' ) );
		$errors = ( new Fields( new VatProfile( new ViesClient() ) ) )->validate( new WP_Error() );
		$this->assertContains( Website::META, $errors->get_error_codes() );

		$_POST  = $this->post(
			array(
				Website::META        => '',
				VatProfile::VAT_META => 'DE 143 454 214',
			)
		);
		$errors = ( new Fields( new VatProfile( new ViesClient() ) ) )->validate( new WP_Error() );
		$this->assertFalse( $errors->has_errors() );
	}

	/**
	 * The real rendered form: company, business type, country, website, VAT ID,
	 * then the names; Germany is selected and leads the EU group; the three
	 * address fields are gone.
	 */
	public function test_the_rendered_form_keeps_the_step_order_and_drops_the_address(): void {
		$_POST = array();
		ob_start();
		( new Fields( new VatProfile( new ViesClient() ) ) )->render();
		$html = (string) ob_get_clean();

		$positions = array();
		foreach ( array( 'billing_company', CustomerRole::META, 'billing_country', Website::META, VatProfile::VAT_META, 'billing_first_name', 'billing_last_name' ) as $key ) {
			$positions[ $key ] = strpos( $html, 'name="' . $key . '"' );
			$this->assertNotFalse( $positions[ $key ], $key . ' renders.' );
		}
		$this->assertTrue( $positions['billing_company'] < $positions[ CustomerRole::META ] );
		$this->assertTrue( $positions[ CustomerRole::META ] < $positions['billing_country'] );
		$this->assertTrue( $positions['billing_country'] < $positions[ Website::META ] );
		$this->assertTrue( $positions[ Website::META ] < $positions[ VatProfile::VAT_META ] );
		$this->assertTrue( $positions[ VatProfile::VAT_META ] < $positions['billing_first_name'] );
		$this->assertTrue( $positions['billing_first_name'] < $positions['billing_last_name'] );

		$this->assertStringContainsString( "<option value=\"DE\" selected='selected'>Germany</option>", $html );
		$this->assertStringContainsString( '<optgroup label="Europe">', $html );
		$this->assertStringContainsString( '<optgroup label="Other countries">', $html );
		$this->assertTrue( strpos( $html, '<optgroup label="Europe">' ) < strpos( $html, '<optgroup label="Other countries">' ) );
		$this->assertStringNotContainsString( 'name="billing_address_1"', $html );
		$this->assertStringNotContainsString( 'name="billing_postcode"', $html );
		$this->assertStringNotContainsString( 'name="billing_city"', $html );
		$this->assertStringContainsString( 'type="radio"', $html, 'The business type is the three radio blocks.' );
	}

	/**
	 * A bot that fills everything but the trap, or posts too fast, or comes
	 * back over the shared limit, is refused before any account or mail and
	 * the refusal is counted.
	 */
	public function test_the_guard_refuses_and_counts_before_an_account_or_mail_exists(): void {
		$previous = get_option( BlockedRegistrations::OPTION );
		BlockedRegistrations::reset();
		$this->later(
			static function () use ( $previous ): void {
				if ( false === $previous ) {
					delete_option( BlockedRegistrations::OPTION );
				} else {
					update_option( BlockedRegistrations::OPTION, $previous, false );
				}
			}
		);
		$marker = self::newest_mail_job();

		$stamp = (string) ( time() - 5 );
		$base  = $this->post(
			array(
				'linker_started'       => $stamp,
				'linker_started_nonce' => wp_create_nonce( 'linker_inquiry_started_' . $stamp ),
			)
		);

		$_POST  = array_merge( $base, array( 'website' => 'http://spam.example' ) );
		$errors = ( new BotGuard() )->validate( new WP_Error() );
		$this->assertContains( BotGuard::ERROR, $errors->get_error_codes() );

		$now    = (string) time();
		$_POST  = array_merge(
			$this->post(),
			array(
				'linker_started'       => $now,
				'linker_started_nonce' => wp_create_nonce( 'linker_inquiry_started_' . $now ),
			)
		);
		$errors = ( new BotGuard() )->validate( new WP_Error() );
		$this->assertContains( BotGuard::ERROR, $errors->get_error_codes() );
		$counts = BlockedRegistrations::counts();
		$this->assertSame( 1, $counts['counts'][ PublicGuard::REFUSAL_HONEYPOT ] );
		$this->assertSame( 1, $counts['counts'][ PublicGuard::REFUSAL_TOO_FAST ] );

		// Three accepted attempts spend the connection's allowance; the fourth is refused.
		$_POST = $base;
		for ( $attempt = 0; $attempt < PublicGuard::LIMIT; ++$attempt ) {
			$this->assertFalse( ( new BotGuard() )->validate( new WP_Error() )->has_errors(), 'Within the shared allowance.' );
		}
		$this->assertContains( BotGuard::ERROR, ( new BotGuard() )->validate( new WP_Error() )->get_error_codes() );
		$this->assertSame( 1, BlockedRegistrations::counts()['counts'][ BotGuard::LIMIT ] );

		$this->assertSame( array(), self::mail_jobs_after( $marker ), 'A refused registration queues no mail.' );
		$users = get_users(
			array(
				'search' => $base['email'],
				'fields' => 'ID',
			)
		);
		$this->assertSame( array(), $users, 'A refused registration creates no account.' );
	}

	/**
	 * Every queued message written after $marker, with its body.
	 *
	 * @param int $marker Newest row id before the test.
	 * @return list<array{subject: string, to: list<string>, headers: list<string>, body: string}>
	 */
	private function jobs_after( int $marker ): array {
		$rows = array();
		foreach ( self::mail_jobs_after( $marker ) as $id ) {
			$data   = json_decode( (string) get_post_meta( $id, '_linker_mail_message', true ), true );
			$data   = is_array( $data ) ? $data : array();
			$rows[] = array(
				'subject' => (string) ( $data['subject'] ?? '' ),
				'to'      => array_values( array_map( 'strval', (array) ( $data['to'] ?? array() ) ) ),
				'headers' => array_values( array_map( 'strval', (array) ( $data['headers'] ?? array() ) ) ),
				'body'    => (string) ( $data['body'] ?? '' ),
			);
		}
		return $rows;
	}
}
