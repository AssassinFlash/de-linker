<?php
/**
 * Native admin review against a real WordPress/WooCommerce and the Outbox.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Mail\Throttle;
use Linker\Commerce\Digest\Blocks;
use Linker\Commerce\Digest\DigestEmail;
use Linker\Commerce\Registration\Accounts;
use Linker\Commerce\Registration\AccountSignals;
use Linker\Commerce\Registration\AccountsAdmin;
use Linker\Commerce\Registration\AccountsTable;
use Linker\Commerce\Registration\Approval;
use Linker\Commerce\Registration\Fields;
use Linker\Commerce\Registration\Emails\NewCustomerEmail;
use Linker\Commerce\Registration\Emails\VatReviewEmail;
use Linker\Commerce\Registration\PendingApprovals;
use Linker\Commerce\Registration\RegistrationInformation;
use Linker\Commerce\Registration\VatProfile;
use Linker\Commerce\Registration\ViesClient;
use Linker\Commerce\Registration\Website;
use Linker\Commerce\Settings\Options;
use WC_Customer;
use WP_REST_Request;
use WP_REST_Response;
use WP_User;

/**
 * Real admin routes, field readers, native surfaces and queued customer mail.
 *
 * @coversNothing
 */
final class AccountsAdminTest extends IntegrationTestCase {

	/**
	 * Staff in this actual snapshot (no hard-coded live user id).
	 *
	 * @var int
	 */
	private int $staff;

	/**
	 * The shared readers under test.
	 *
	 * @var Accounts
	 */
	private Accounts $accounts;

	/** Isolates queued mail so no transport attempt is needed. */
	protected function setUp(): void {
		parent::setUp();
		$staff       = get_users(
			array(
				'role'   => 'administrator',
				'number' => 1,
			)
		)[0];
		$this->staff = $staff->ID;
		$this->as_user( $this->staff );
		$staff_locale = get_user_meta( $this->staff, 'locale', true );
		update_user_meta( $this->staff, 'locale', 'en_US' );
		$this->later(
			function () use ( $staff_locale ): void {
				update_user_meta( $this->staff, 'locale', $staff_locale );
			}
		);
		$before   = $this->job_ids();
		$throttle = get_option( Throttle::OPTION, array() );
		update_option( Throttle::OPTION, array_fill( 0, Throttle::PER_DAY, time() ) );
		$this->later(
			static function () use ( $throttle ): void {
				update_option( Throttle::OPTION, $throttle );
			}
		);
		$this->later(
			function () use ( $before ): void {
				foreach ( array_diff( $this->job_ids(), $before ) as $id ) {
						as_unschedule_all_actions( \Linker\Commerce\Mail\Outbox::HOOK, array( $id ), \Linker\Commerce\Mail\Outbox::GROUP );
						wp_delete_post( $id, true );
				}
			}
		);
		$approval       = new Approval();
		$this->accounts = new Accounts( $approval, new RegistrationInformation( new Fields( new VatProfile( new ViesClient() ), $approval ) ) );
		rest_get_server();
	}

	/** Defaults, explicit decisions and staff roles agree with the one Approval rule. */
	public function test_queue_counts_only_pending_plain_customers(): void {
		$baseline  = $this->accounts->counts();
		$customers = array();
		foreach ( Approval::states() as $state ) {
			$customer = $this->customer();
			update_user_meta( $customer->get_id(), Approval::STATUS_META, $state );
			$customers[ $state ] = $customer;
		}
		delete_user_meta( $customers[ Approval::PENDING ]->get_id(), Approval::STATUS_META );
		foreach ( Approval::states() as $state ) {
			$this->assertSame( $baseline[ $state ] + 1, $this->accounts->counts()[ $state ] );
		}
		$ids = array_column( $this->accounts->items(), 'id' );
		$this->assertContains( $customers[ Approval::PENDING ]->get_id(), $ids );
		$this->assertNotContains( $customers[ Approval::RESTRICTED ]->get_id(), $ids );
		$this->assertNotContains( $customers[ Approval::REJECTED ]->get_id(), $ids );
		$user = new WP_User( $customers[ Approval::PENDING ]->get_id() );
		$user->add_role( 'shop_manager' );
		$this->assertNotContains( $user->ID, array_column( $this->accounts->items(), 'id' ) );
	}

	/** A field supplied by the real Woo field definition appears without a card edit. */
	public function test_registration_fields_and_old_addresses_are_dynamic(): void {
		$customer = $this->customer();
		$customer->update_meta_data( 'billing_company_website', 'https://example.test/legal/' );
		$customer->update_meta_data( 'internal_secret', 'must-not-leave-server' );
		$customer->save();
		$field = static function ( array $fields ): array {
			$fields['billing_company_website'] = array(
				'type'  => 'url',
				'label' => 'Company website',
			);
			return $fields;
		};
		add_filter( 'woocommerce_billing_fields', $field ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound, WooCommerce.Commenting.CommentHooks.MissingHookComment -- supplies Woo's native field definition in a fixture.
		try {
			$item = $this->accounts->items( $customer->get_id() )[0];
			$rows = array_column( $item['fields'], 'value', 'key' );
			$this->assertSame( 'https://example.test/legal/', $rows['billing_company_website'] );
			$this->assertSame( 'Teststraße 1', $rows['billing_address_1'] );
			$this->assertContains( 'https://example.test/legal/', array_column( $item['links'], 'url' ) );
			$this->assertNotContains( 'Website (from email domain)', array_column( $item['links'], 'label' ), 'A submitted website takes priority over a domain lead.' );
			$this->assertStringNotContainsString( 'must-not-leave-server', (string) wp_json_encode( $item ) );
			$this->assertArrayNotHasKey( 'user_pass', $item );
		} finally {
			remove_filter( 'woocommerce_billing_fields', $field ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- removes the fixture.
		}
	}

	/**
	 * The website added to the registration form (#225) reaches the review
	 * card and its link through the same field reader; no card edit.
	 */
	public function test_the_registered_website_appears_in_the_review_card(): void {
		$customer = $this->customer();
		$customer->update_meta_data( Website::META, 'https://example.com/' );
		$customer->save();

		$item = $this->accounts->items( $customer->get_id() )[0];
		$rows = array_column( $item['fields'], 'value', 'key' );
		$this->assertSame( 'https://example.com/', $rows[ Website::META ] );
		$this->assertContains( 'https://example.com/', array_column( $item['links'], 'url' ) );
		$this->assertContains( 'Company website', array_column( $item['links'], 'label' ) );
	}

	/** Synthetic text, replaceable free-mail providers and saved VAT outcomes are only clues. */
	public function test_signals_use_saved_evidence_and_skip_free_email_websites(): void {
		$customer = $this->customer();
		$customer->set_billing_company( 'Example What is SEO Services' );
		$customer->set_email( 'a227-bot@free-mail.example.test' );
		$customer->save();
		$approval = new Approval();
		$accounts = new Accounts( $approval, new RegistrationInformation( new Fields( new VatProfile( new ViesClient() ), $approval ) ), new AccountSignals( array( 'free-mail.example.test' ) ) );
		foreach ( array( VatProfile::VALID, VatProfile::INVALID, VatProfile::UNVERIFIED, VatProfile::NONE, '' ) as $vat ) {
			update_user_meta( $customer->get_id(), VatProfile::STATUS_META, $vat );
			$item = $accounts->items( $customer->get_id() )[0];
			$text = implode( ' ', array_column( $item['signals'], 'text' ) );
			$this->assertStringContainsString( 'Free email provider: free-mail.example.test', $text );
			$this->assertStringContainsString( 'Possible automated registration', $text );
			$this->assertStringContainsString( VatProfile::label( $vat ), $text );
			$this->assertNotContains( 'https://free-mail.example.test', array_column( $item['links'], 'url' ) );
			$this->assertSame( Approval::APPROVED, $item['status'] );
		}
	}

	/** Count aggregation is reused by all readers, with no hydrated customer list. */
	public function test_counts_use_one_request_cached_aggregate_and_invalidate_after_changes(): void {
		$customer = $this->customer();
		update_user_meta( $customer->get_id(), Approval::STATUS_META, Approval::PENDING );
		$queries = array();
		$capture = static function ( string $sql ) use ( &$queries ): string {
			$queries[] = $sql;
			return $sql;
		};
		add_filter( 'query', $capture ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- observes real SQL without changing it.
		try {
			$first = $this->accounts->counts();
			$this->accounts->counts();
			$this->accounts->counts();
			$approval = new Approval();
			$other    = new Accounts( $approval, new RegistrationInformation( new Fields( new VatProfile( new ViesClient() ), $approval ) ) );
			$this->assertSame( $first, $other->counts(), 'All entry points share the request result.' );
			$this->assertCount( 1, $queries, 'Counting must not fetch full customer rows or repeat the aggregation.' );
			$this->assertStringContainsString( 'COUNT(DISTINCT', $queries[0] );
			$this->assertStringContainsString( 'GROUP BY account_state', $queries[0] );
			update_user_meta( $customer->get_id(), Approval::STATUS_META, Approval::RESTRICTED );
			$changed = $this->accounts->counts();
			$this->assertSame( $first[ Approval::PENDING ] - 1, $changed[ Approval::PENDING ] );
			$this->assertSame( $first[ Approval::RESTRICTED ] + 1, $changed[ Approval::RESTRICTED ] );
			( new WP_User( $customer->get_id() ) )->add_role( 'shop_manager' );
			$this->assertSame( $first[ Approval::RESTRICTED ], $this->accounts->counts()[ Approval::RESTRICTED ], 'A mixed staff role is excluded by the SQL count too.' );
		} finally {
			remove_filter( 'query', $capture ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- restores the query filter.
		}
	}

	/** Website links expose their origin; Google uses a country name. */
	public function test_verification_links_use_saved_website_before_email_domain(): void {
		$customer = $this->customer();
		$customer->set_email( 'maria@solar.example.test' );
		$customer->save();
		$item  = $this->accounts->items( $customer->get_id() )[0];
		$links = array_column( $item['links'], 'url', 'label' );
		$this->assertSame( 'https://solar.example.test', $links['Website (from email domain)'] );
		$this->assertStringContainsString( 'Germany', rawurldecode( $links['Google'] ) );
		$this->assertArrayNotHasKey( 'VIES', $links, 'An account without a VAT ID has no blank VIES link.' );
		foreach ( array(
			'de 000.000.000' => 'DE/vat/000000000',
			'EL000000000'    => 'EL/vat/000000000',
			'XI000000000'    => 'XI/vat/000000000',
		) as $input => $path ) {
			update_user_meta( $customer->get_id(), VatProfile::VAT_META, $input );
			$links = array_column( $this->accounts->items( $customer->get_id() )[0]['links'], 'url', 'label' );
			$this->assertSame( 'https://ec.europa.eu/taxation_customs/vies/rest-api/ms/' . $path, $links['VIES'], 'The official number-specific query carries the normalized saved VAT.' );
		}
		update_user_meta( $customer->get_id(), VatProfile::VAT_META, 'GB000000000' );
		$this->assertNotContains( 'VIES', array_column( $this->accounts->items( $customer->get_id() )[0]['links'], 'label' ), 'A number outside the VIES territory has no misleading link.' );
	}

	/** Real route -> Approval -> Woo email -> Outbox, for both customer languages. */
	public function test_decisions_reasons_revisions_and_idempotency_reach_the_outbox(): void {
		foreach ( array( 'en_US', 'de_DE_formal' ) as $locale ) {
			$customer = $this->customer();
			update_user_meta( $customer->get_id(), 'locale', $locale );
			update_user_meta( $customer->get_id(), Approval::STATUS_META, Approval::PENDING );
			$before = $this->job_ids();
			foreach ( array(
				Approval::APPROVED   => '',
				Approval::RESTRICTED => 'Please provide your company website.',
				Approval::REJECTED   => 'We could not verify this registration.',
			) as $status => $reason ) {
				$response = $this->decision( $customer, $status, $reason );
				$this->assertSame( 200, $response->get_status() );
				$this->assertSame( $status, ( new Approval() )->status( $customer->get_id() ) );
				$this->assertSame( $reason, ( new Approval() )->reason( $customer->get_id() ) );
				$this->assertSame( $this->staff, ( new Approval() )->changed_by( $customer->get_id() )['by'] );
			}
			$ids = array_values( array_diff( $this->job_ids(), $before ) );
			$this->assertCount( 3, $ids );
			$messages = array();
			foreach ( $ids as $id ) {
				$job = ( new JobStore() )->load( $id );
				$this->assertNotNull( $job );
				$messages[] = $job['message'];
			}
			foreach ( $messages as $message ) {
				$this->assertSame( array( $customer->get_email() ), $message->to );
			}
			$text = implode( '\n', array_map( static fn ( $message ): string => $message->body, $messages ) );
			$this->assertStringContainsString( 'Please provide your company website.', $text );
			$this->assertStringContainsString( 'We could not verify this registration.', $text );
			$this->assertStringContainsString( 'de_DE_formal' === $locale ? 'Ihr Partner-Konto' : 'Your partner account', implode( '\n', array_map( static fn ( $message ): string => $message->subject, $messages ) ) );
			$this->decision( $customer, Approval::REJECTED, 'We could not verify this registration.' );
			$this->assertCount( 3, array_diff( $this->job_ids(), $before ), 'An identical decision sends no duplicate.' );
			$this->decision( $customer, Approval::REJECTED, 'Updated explanation for the customer.' );
			$this->assertCount( 4, array_diff( $this->job_ids(), $before ), 'A changed explanation reaches the customer.' );
			$this->decision( $customer, Approval::APPROVED );
			$this->assertTrue( ( new Approval() )->sees_prices( $customer->get_id() ), 'A historical rejection can be approved again.' );
			$this->assertSame( '', ( new Approval() )->reason( $customer->get_id() ) );
		}
	}

	/** A reason-less action cannot change the state or enqueue customer mail. */
	public function test_reason_is_required_and_bad_statuses_are_rejected(): void {
		$customer = $this->customer();
		$before   = $this->job_ids();
		foreach ( array( Approval::RESTRICTED, Approval::REJECTED, Approval::PENDING, 'unknown' ) as $status ) {
			$this->assertSame( 400, $this->decision( $customer, $status )->get_status() );
		}
		$this->assertSame( Approval::APPROVED, ( new Approval() )->status( $customer->get_id() ) );
		$this->assertSame( $before, $this->job_ids() );
	}

	/** Staff-only reads/writes, per-target checks and no mutating GET. */
	public function test_routes_reject_anonymous_customer_and_staff_targets(): void {
		$customer = $this->customer();
		foreach ( array( 0, $customer->get_id() ) as $user ) {
			$this->as_user( $user );
			$this->assertSame( 403, rest_do_request( new WP_REST_Request( 'GET', '/linker/v1/accounts' ) )->get_status() );
			$this->assertSame( 403, $this->decision( $customer, Approval::REJECTED, 'Not allowed.' )->get_status() );
		}
		$this->as_user( $this->staff );
		$request = new WP_REST_Request( 'POST', '/linker/v1/accounts/' . $this->staff . '/approval' );
		$request->set_param( 'status', Approval::APPROVED );
		$this->assertSame( 403, rest_do_request( $request )->get_status() );
		$this->assertSame( 404, rest_do_request( new WP_REST_Request( 'GET', '/linker/v1/accounts/' . $customer->get_id() . '/approval' ) )->get_status() );
	}

	/** Deep links still resolve reviewed accounts, and missing IDs are explicit errors. */
	public function test_focused_links_include_reviewed_accounts(): void {
		$customer = $this->customer();
		$url      = AccountsAdmin::url( $customer->get_id() );
		$this->assertStringContainsString( 'page=linker-accounts', $url );
		$this->assertStringContainsString( 'focus=' . $customer->get_id(), $url );
		$request = new WP_REST_Request( 'GET', '/linker/v1/accounts' );
		$request->set_param( 'focus', $customer->get_id() );
		$response = rest_do_request( $request );
		$this->assertSame( 200, $response->get_status() );
		$this->assertSame( Approval::APPROVED, $response->get_data()['accounts'][0]['status'] );
		$request->set_param( 'focus', PHP_INT_MAX );
		$this->assertSame( 404, rest_do_request( $request )->get_status() );
	}

	/** Native entry points register, and the history searches company/contact/email. */
	public function test_native_widget_toolbar_and_history(): void {
		// Native screen setup must not turn later storefront tests into admin requests.
		$globals = array();
		foreach ( array( 'current_screen', 'taxnow', 'typenow', 'wp_meta_boxes' ) as $key ) {
			$globals[ $key ] = array(
				'exists' => array_key_exists( $key, $GLOBALS ),
				'value'  => $GLOBALS[ $key ] ?? null,
			);
		}
		$this->later(
			static function () use ( $globals ): void {
				foreach ( $globals as $key => $before ) {
					if ( $before['exists'] ) {
						// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedVariableFound -- Restore WordPress's existing screen globals.
						$GLOBALS[ $key ] = $before['value'];
					} else {
						unset( $GLOBALS[ $key ] );
					}
				}
			}
		);
		require_once ABSPATH . 'wp-admin/includes/admin.php';
		require_once ABSPATH . 'wp-admin/includes/dashboard.php';
		require_once ABSPATH . 'wp-admin/includes/class-wp-list-table.php';
		set_current_screen( 'dashboard' );
		$admin = new AccountsAdmin( dirname( __DIR__, 3 ) . '/linker-commerce.php', $this->accounts, new Approval() );
		$admin->dashboard();
		$this->assertArrayHasKey( 'linker-accounts-widget', $GLOBALS['wp_meta_boxes']['dashboard']['normal']['high'] );
		$this->assertStringContainsString( 'data-linker-account-count="pending">' . $this->accounts->counts()[ Approval::PENDING ] . '</span>', $GLOBALS['wp_meta_boxes']['dashboard']['normal']['high']['linker-accounts-widget']['title'] );
		require_once ABSPATH . 'wp-includes/class-wp-admin-bar.php';
		$bar = new \WP_Admin_Bar();
		$admin->bar( $bar );
		$node = $bar->get_node( AccountsAdmin::PAGE );
		$this->assertNotNull( $node );
		$this->assertArrayHasKey( 'href', get_object_vars( $node ) );
			$this->assertSame( AccountsAdmin::url(), get_object_vars( $node )['href'] );
		$customer = $this->customer();
		$customer->set_billing_company( 'A227 Searchable Solar GmbH' );
		$customer->save();
		$table = new AccountsTable( $this->accounts, new Approval(), 'all', 'A227 Searchable' );
		$table->prepare_items();
		ob_start();
		$table->display();
		$html = (string) ob_get_clean();
		$this->assertStringContainsString( 'A227 Searchable Solar GmbH', $html );
		$this->assertStringContainsString( 'data-linker-account="' . $customer->get_id() . '"', $html );
		$this->assertSame( 1, substr_count( $html, 'class="toggle-row"' ), 'The native primary column has one responsive details control.' );
		$this->assertStringNotContainsString( 'linker_approval_action=', $html );
	}

	/** User Switching owns its nonce and authorization; the site is the destination. */
	public function test_switching_links_use_the_native_plugin_when_available(): void {
		$customer = $this->customer();
		$item     = $this->accounts->items( $customer->get_id() )[0];
		if ( class_exists( 'user_switching' ) ) {
			$this->assertStringContainsString( 'action=switch_to_user', $item['switchUrl'] );
			$this->assertStringContainsString( '_wpnonce=', $item['switchUrl'] );
			$this->assertStringContainsString( 'redirect_to=', $item['switchUrl'] );
			parse_str( (string) wp_parse_url( $item['switchUrl'], PHP_URL_QUERY ), $query );
			$this->assertSame( (string) $customer->get_id(), $query['user_id'] );
			$this->assertArrayHasKey( '_wpnonce', $query );
		} else {
			$this->assertSame( '', $item['switchUrl'] );
			$this->assertSame( 'User Switching is not active.', $item['switchNote'] );
		}
	}

	/** Staff locale controls card values even when Polylang booted the REST request in English. */
	public function test_staff_language_applies_to_all_card_values(): void {
		$customer = $this->customer();
		update_user_meta( $this->staff, 'locale', 'de_DE_formal' );
		$request = new WP_REST_Request( 'GET', '/linker/v1/accounts' );
		$request->set_param( 'focus', $customer->get_id() );
		$item = rest_do_request( $request )->get_data()['accounts'][0];
		$this->assertSame( 'Deutschland', $item['country'] );
		$this->assertSame( 'Freigegeben', $item['statusLabel'] );
		$this->assertStringContainsString( 'nicht geprüft', implode( ' ', array_column( $item['signals'], 'text' ) ) );
		update_user_meta( $customer->get_id(), 'locale', 'de_DE_formal' );
		$changed = $this->decision( $customer, Approval::RESTRICTED, 'Bitte ergänzen Sie Ihre Unternehmenswebsite.' )->get_data()['account'];
		$this->assertSame( 'Eingeschränkt', $changed['statusLabel'], 'An email in the same language must not pop the outer staff locale.' );
		$this->assertStringContainsString( 'nicht geprüft', implode( ' ', array_column( $changed['signals'], 'text' ) ) );
		$this->assertSame( 'en_US', get_locale(), 'The response restores its caller locale.' );
	}

	/** TeamEmail keeps its routing and language while both account notifications link to the review card. */
	public function test_internal_notifications_link_directly_to_the_account_in_both_languages(): void {
		$this->internal_mail_options();
		$emails       = WC()->mailer()->get_emails();
		$new_customer = $emails[ NewCustomerEmail::class ];
		$vat_review   = $emails[ VatReviewEmail::class ];
		$this->assertInstanceOf( NewCustomerEmail::class, $new_customer );
		$this->assertInstanceOf( VatReviewEmail::class, $vat_review );
		$this->later(
			static function () use ( $new_customer, $vat_review ): void {
				$new_customer->init_settings();
				$vat_review->init_settings();
			}
		);
		foreach ( array( 'en_US', 'de_DE_formal' ) as $locale ) {
			update_option( 'WPLANG', $locale );
			// Each locale represents a separate site request. Woo caches the first
			// default subject in memory, so reload its native settings between them.
			$new_customer->init_settings();
			$vat_review->init_settings();
			$customer = $this->customer();
			update_user_meta( $customer->get_id(), Approval::STATUS_META, Approval::PENDING );
			update_user_meta( $customer->get_id(), 'locale', 'en_US' === $locale ? 'de_DE_formal' : 'en_US' );
			$marker = self::newest_mail_job();
			$new_customer->trigger( $customer->get_id() );
			$vat_review->trigger( $customer->get_id(), VatProfile::UNVERIFIED, VatProfile::INVALID );
			$ids = self::mail_jobs_after( $marker );
			$this->assertCount( 2, $ids );
			$focus_url = '';
			foreach ( $ids as $id ) {
				$job = ( new JobStore() )->load( $id );
				$this->assertNotNull( $job );
				$message = $job['message'];
				$this->assertSame( array( Options::DEFAULT_NOTIFY_TO ), $message->to );
				$this->assertContains( 'Bcc: a227-copy@example.test', $message->headers );
				$body = html_entity_decode( $message->body, ENT_QUOTES, 'UTF-8' );
				$this->assertSame( 1, preg_match( '/href="([^"]*page=linker-accounts[^"]*)"/', $body, $match ) );
				$focus_url = $match[1] ?? '';
				$this->assertSame( AccountsAdmin::url( $customer->get_id() ), $focus_url );
				$this->assertStringNotContainsString( 'user-edit.php?user_id=', $body );
			}
			$first = ( new JobStore() )->load( $ids[0] );
			$this->assertNotNull( $first );
			$this->assertStringStartsWith( 'de_DE_formal' === $locale ? 'Neuer Kunde:' : 'New customer:', $first['message']->subject );
			$this->decision( $customer, Approval::APPROVED );
			parse_str( (string) wp_parse_url( $focus_url, PHP_URL_QUERY ), $query );
			$request = new WP_REST_Request( 'GET', '/linker/v1/accounts' );
			$request->set_param( 'focus', $query['focus'] );
			$this->assertSame( Approval::APPROVED, rest_do_request( $request )->get_data()['accounts'][0]['status'], 'An old notification still resolves the processed account.' );
		}
	}

	/** The Digest\Block set, headline count and queued EN/DE report agree with the staff queue. */
	public function test_digest_counts_only_pending_customers_and_links_to_their_cards(): void {
		$this->internal_mail_options();
		$block    = new PendingApprovals();
		$counts   = $this->accounts->counts();
		$baseline = $counts[ Approval::PENDING ];
		$fixtures = array();
		foreach ( array( 'default', Approval::PENDING, Approval::APPROVED, Approval::RESTRICTED, Approval::REJECTED, 'staff' ) as $state ) {
			$customer = $this->customer();
			$customer->set_billing_company( 'A227 digest ' . $state . ' ' . self::tag() );
			$customer->save();
			$fixtures[ $state ] = $customer;
			if ( 'default' === $state ) {
				delete_user_meta( $customer->get_id(), Approval::STATUS_META );
			} else {
				update_user_meta( $customer->get_id(), Approval::STATUS_META, 'staff' === $state ? Approval::PENDING : $state );
			}
			if ( 'staff' === $state ) {
				( new WP_User( $customer->get_id() ) )->add_role( 'shop_manager' );
			}
		}
		$this->assertSame( $baseline + 2, $this->accounts->counts()[ Approval::PENDING ] );
		$this->as_user( 0 );
		$pending_rows = array_filter( $block->entries(), static fn ( array $entry ): bool => str_contains( $entry['url'], '&focus=' ) );
		$this->assertCount( $baseline + 2, $pending_rows, 'Cron does not need employee capabilities to count pending customers.' );
		foreach ( array( 'en_US', 'de_DE_formal' ) as $locale ) {
			update_option( 'WPLANG', $locale );
			$marker = self::newest_mail_job();
			( new DigestEmail( WP_PLUGIN_DIR . '/linker-commerce/linker-commerce.php', new Options() ) )->send_report( ( new Blocks( new JobStore() ) )->all() );
			$ids = self::mail_jobs_after( $marker );
			$this->assertCount( 1, $ids );
			$job = ( new JobStore() )->load( $ids[0] );
			$this->assertNotNull( $job );
			$this->assertSame( array( Options::DEFAULT_NOTIFY_TO ), $job['message']->to );
			$this->assertContains( 'Bcc: a227-copy@example.test', $job['message']->headers );
			$body  = html_entity_decode( $job['message']->body, ENT_QUOTES, 'UTF-8' );
			$title = 'de_DE_formal' === $locale ? 'Konten, die auf die Freigabe warten' : 'Accounts waiting for approval';
			$this->assertStringContainsString( $title . ' (' . ( $baseline + 2 ) . ')', $body );
			$restricted_label = 'de_DE_formal' === $locale ? 'Eingeschränkt, Angaben vom Kunden fehlen: ' : 'Restricted, awaiting customer information: ';
			$this->assertStringContainsString( $restricted_label . ( $counts[ Approval::RESTRICTED ] + 1 ), $body );
			$this->assertStringContainsString( add_query_arg( 'status', Approval::RESTRICTED, AccountsAdmin::url() ), $body );
			foreach ( $fixtures as $state => $customer ) {
				if ( in_array( $state, array( 'default', Approval::PENDING ), true ) ) {
					$this->assertStringContainsString( $customer->get_billing_company(), $body );
					$this->assertStringContainsString( AccountsAdmin::url( $customer->get_id() ), $body );
				} else {
					$this->assertStringNotContainsString( $customer->get_billing_company(), $body );
				}
			}
		}
	}

	/** Restrictions remain discoverable independently from the pending-only flag. */
	public function test_restricted_accounts_have_their_own_collection_and_page_section(): void {
		$customer = $this->customer();
		$this->decision( $customer, Approval::RESTRICTED, 'Please provide the missing company information.' );
		$request = new WP_REST_Request( 'GET', '/linker/v1/accounts' );
		$request->set_param( 'status', Approval::RESTRICTED );
		$restricted = rest_do_request( $request )->get_data()['accounts'];
		$this->assertContains( $customer->get_id(), array_column( $restricted, 'id' ) );
		$this->assertNotContains( $customer->get_id(), array_column( $this->accounts->items(), 'id' ) );
		require_once ABSPATH . 'wp-admin/includes/admin.php';
		$admin = new AccountsAdmin( dirname( __DIR__, 3 ) . '/linker-commerce.php', $this->accounts, new Approval() );
		ob_start();
		$admin->page();
		$html = (string) ob_get_clean();
		$this->assertStringContainsString( 'id="linker-accounts-restricted"', $html );
		$this->assertStringContainsString( 'Restricted, awaiting customer information', $html );
	}

	/** Settings used by queued internal mail, restored even after a failed assertion. */
	private function internal_mail_options(): void {
		$saved = array();
		foreach ( array( 'WPLANG', Options::NOTIFY_TO, Options::NOTIFY_BCC ) as $name ) {
			$saved[ $name ] = get_option( $name );
		}
		$this->later(
			static function () use ( $saved ): void {
				foreach ( $saved as $name => $value ) {
					if ( false === $value ) {
						delete_option( $name );
					} else {
						update_option( $name, $value );
					}
				}
			}
		);
		delete_option( Options::NOTIFY_TO );
		update_option( Options::NOTIFY_BCC, 'a227-copy@example.test' );
	}

	/**
	 * Sends an in-process staff request through WordPress's actual REST dispatcher.
	 *
	 * @param WC_Customer $customer Fixture.
	 * @param string      $status   Desired state.
	 * @param string      $reason   Customer explanation.
	 */
	private function decision( WC_Customer $customer, string $status, string $reason = '' ): WP_REST_Response {
		$request = new WP_REST_Request( 'POST', '/linker/v1/accounts/' . $customer->get_id() . '/approval' );
		$request->set_param( 'status', $status );
		$request->set_param( 'reason', $reason );
		return rest_do_request( $request );
	}

	/**
	 * IDs of queued messages, kept in deterministic order for assertions.
	 *
	 * @return list<int>
	 */
	private function job_ids(): array {
		return array_values(
			get_posts(
				array(
					'post_type'   => JobStore::POST_TYPE,
					'post_status' => 'any',
					'numberposts' => -1,
					'fields'      => 'ids',
					'orderby'     => 'ID',
					'order'       => 'ASC',
				)
			)
		);
	}
}
