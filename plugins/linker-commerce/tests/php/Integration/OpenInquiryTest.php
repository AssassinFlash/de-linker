<?php
/**
 * Public inquiries through the shared submission entry.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Tests\Fixtures\NormalMailAuthorizationFixture;

use Linker\Commerce\Contact\Submission;
use Linker\Commerce\Inquiry\Sender;
use Linker\Commerce\Inquiry\PublicGuard;
use Linker\Commerce\Mail\Throttle;
use WC_Order;

/**
 * Shared entry, account states, and queue routes on a real instance.
 *
 * @coversNothing
 */
final class OpenInquiryTest extends IntegrationTestCase {

	/** Install only this test's bound local service seam. */
	protected function setUp(): void {
		parent::setUp();
		require_once dirname( __DIR__, 2 ) . '/fixtures/NormalMailAuthorizationFixture.php';
		$this->authorization = NormalMailAuthorizationFixture::install(
			function ( callable $remove ): void {
				$this->later( $remove );
			}
		);
	}

	/** Typed local service with native consumers.
	 *
	 * @var NormalMailAuthorizationFixture
	 */
	private NormalMailAuthorizationFixture $authorization;

	/** Review exposes the native checkout fields and signs exactly the revision shown. */
	public function test_preliminary_review_form_binds_the_native_nonce(): void {
		wc_load_cart();
		WC()->cart->empty_cart();
		$id      = 'b94de53435f84797900b710f5b2a948a';
		$project = array(
			'project_id'    => $id,
			'revision'      => 3,
			'note_revision' => '3',
			'title'         => 'Storage inquiry fixture',
			'text'          => '',
			'inputs'        => array( 'brief' => array( 'system_scope' => 'storage_only' ) ),
		);
		$review  = apply_filters( 'linker_commerce_planning_inquiry_form', null, 'en', $project ); // phpcs:ignore WooCommerce.Commenting.CommentHooks.MissingHookComment -- Defined by the planner gateway.
		$this->assertIsArray( $review );
		$this->assertSame( 1, $review['schema_version'] );
		$this->assertSame( array(), $review['inquiry_lines'] );
		$html = $review['inquiry_form_html'];
		$this->assertIsString( $html );
		$this->assertStringContainsString( 'action="' . esc_url( admin_url( 'admin-post.php' ) ) . '"', $html );
		$this->assertStringContainsString( 'name="linker_preliminary_project" value="' . $id . ':3"', $html );
		$this->assertSame( 1, substr_count( $html, 'name="linker_draft_hash"' ) );
		$this->assertStringContainsString( 'id="inquiry-name" name="name"', $html );
		$this->assertStringContainsString( 'id="inquiry-email" name="email"', $html );
		$this->assertSame( 1, preg_match( '/name="linker_inquiry_nonce" value="([^"]+)"/', $html, $match ) );
		$nonce = $match[1] ?? '';
		$this->assertNotFalse( wp_verify_nonce( $nonce, 'linker_inquiry:' . $id . ':3' ) );
		$this->assertFalse( wp_verify_nonce( $nonce, 'linker_inquiry:' . $id . ':4' ) );
	}

	/** A retained-equipment report is previewed without changing the cart, then attached by Send. */
	public function test_guided_report_is_attached_by_the_native_send(): void {
		$this->as_user( $this->customer()->get_id() );
		wc_load_cart();
		WC()->cart->empty_cart();

		$handoff        = $this->planning_report();
		$id             = $handoff['snapshot']['project_id'];
		$report         = $handoff['snapshot']['report_run_id'];
		$project        = array(
			'project_id'    => $id,
			'revision'      => 1,
			'note_revision' => '1',
			'title'         => 'Existing inverter plan',
			'text'          => '',
			'inputs'        => array( 'brief' => array( 'system_scope' => 'storage_only' ) ),
		);
		$project_source = static fn () => $project;
		$handoff_source = static fn () => $handoff;
		$admit          = static fn (): bool => true;
		// phpcs:disable WooCommerce.Commenting.CommentHooks.MissingHookComment -- Simulated owned responses at the native Tools reader seam.
		add_filter( 'linker_tools_planning_inquiry_note', $project_source, 11 );
		add_filter( 'linker_tools_planning_inquiry_handoff', $handoff_source, 11 );
		add_filter( 'linker_tools_planning_admit_inquiry', $admit, 11 );
		$this->later(
			static function () use ( $project_source, $handoff_source, $admit ): void {
				remove_filter( 'linker_tools_planning_inquiry_note', $project_source, 11 );
				remove_filter( 'linker_tools_planning_inquiry_handoff', $handoff_source, 11 );
				remove_filter( 'linker_tools_planning_admit_inquiry', $admit, 11 );
			}
		);
		// phpcs:enable WooCommerce.Commenting.CommentHooks.MissingHookComment

		$review = ( new \Linker\Commerce\Planning\Module() )->inquiry_form(
			null,
			'en',
			$project,
			array(
				'command'  => array(
					'schema_version'    => 1,
					'project_id'        => $id,
					'report_run_id'     => $report,
					'expected_revision' => 1,
					'key'               => wp_generate_uuid4(),
				),
				'handoff'  => $handoff,
				'replay'   => null,
				'retained' => null,
			)
		);
		$this->assertIsArray( $review );
		$this->assertSame( array(), $review['inquiry_lines'] );
		$this->assertSame( array(), \Linker\Commerce\Planning\Context::report_only_contexts() );
		$this->assertSame( 1, preg_match( '/name="linker_report_transfer" value="([^"]+)"/', $review['inquiry_form_html'], $token ) );
		$this->assertSame( 1, preg_match( '/name="linker_inquiry_nonce" value="([^"]+)"/', $review['inquiry_form_html'], $nonce ) );
		$this->assertSame( 1, preg_match( '/name="linker_project_note_revisions\[' . $handoff['id'] . '\]" value="([^"]+)"/', $review['inquiry_form_html'], $note_revision ) );
		$stamp                             = (string) ( time() - 5 );
		$post                              = array(
			'linker_preliminary_project'    => $id . ':1',
			'linker_report_transfer'        => ( $token[1] ?? '' ),
			'linker_inquiry_nonce'          => ( $nonce[1] ?? '' ),
			'linker_started'                => $stamp,
			'linker_started_nonce'          => wp_create_nonce( 'linker_inquiry_started_' . $stamp ),
			'linker_draft_hash'             => WC()->cart->get_cart_hash(),
			'linker_project_notes_present'  => '1',
			'linker_include_project_notes'  => '1',
			'linker_project_note_revisions' => array( $handoff['id'] => ( $note_revision[1] ?? '' ) ),
			'name'                          => 'Guided Fixture',
			'email'                         => 'plan-' . self::tag() . '@example.test',
			'consent'                       => '1',
		);
		$handler                           = new \Linker\Commerce\Inquiry\Handler();
		$altered                           = $post;
		$altered['linker_report_transfer'] = substr_replace( ( $token[1] ?? '' ), str_repeat( '9', 32 ), 0, 32 );
		$refused                           = $handler->process( $altered );
		$this->assertInstanceOf( \WP_Error::class, $refused );
		$this->assertSame( 'linker_inquiry_invalid', $refused->get_error_code() );
		$this->assertSame( array(), \Linker\Commerce\Planning\Context::report_only_contexts() );
		$order = $handler->process( $post );
		$this->assertInstanceOf( WC_Order::class, $order, $order instanceof \WP_Error ? $order->get_error_code() . ': ' . $order->get_error_message() : '' );
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		$stored = \Linker\Commerce\Planning\Context::stored( $order );
		$this->assertSame( $report, $stored[ $handoff['id'] ]['reference']['report_run_id'] );
		$this->assertSame( 1, $stored[ $handoff['id'] ]['reference']['revision'] );
		$this->assertSame( array(), $stored[ $handoff['id'] ]['included_items'] );
	}

	/** A failed preliminary POST is rendered for this tab, not consumed by the next checkout visitor. */
	public function test_preliminary_retry_is_private_to_its_request(): void {
		wc_load_cart();
		$previous_post = $_POST; // phpcs:ignore WordPress.Security.NonceVerification.Missing -- Restore the test request.
		$tags          = $GLOBALS['shortcode_tags'];
		add_filter( 'woocommerce_is_checkout', '__return_true' );
		$this->later(
			static function () use ( $previous_post, $tags ): void {
				$_POST                     = $previous_post;
				$GLOBALS['shortcode_tags'] = $tags;
				remove_filter( 'woocommerce_is_checkout', '__return_true' );
			}
		);
		$id      = str_repeat( 'a', 32 );
		$_POST   = array(
			'action'                        => 'linker_inquiry',
			'linker_preliminary_project'    => $id . ':3',
			'linker_inquiry_nonce'          => wp_create_nonce( 'linker_inquiry:' . $id . ':3' ),
			'message'                       => 'Please call about my roof.',
			'linker_project_notes_present'  => '1',
			'linker_include_project_notes'  => '1',
			'linker_project_note_revisions' => array( 'project_' . $id => '3' ),
		);
		$form    = new \Linker\Commerce\Inquiry\Form();
		$handler = new \Linker\Commerce\Inquiry\Handler( $form );
		$form->register();
		$handler->checkout_post();
		$html = $form->render();
		$this->assertStringContainsString( 'Please call about my roof.</textarea>', $html );
		$this->assertStringContainsString( 'name="linker_preliminary_project" value="' . $id . ':3"', $html );
		$this->assertStringContainsString( 'name="linker_project_note_revisions[project_' . $id . ']" value="3"', $html );
		$this->assertStringNotContainsString( 'name="linker_without_project"', $html );
		$this->assertNull( WC()->session->get( 'linker_inquiry_fields' ) );
		$other = new \Linker\Commerce\Inquiry\Form();
		$other->register();
		$this->assertStringNotContainsString( 'Please call about my roof.', $other->render() );
	}

	/** Only an explicit revision refusal offers a new inquiry without that project. */
	public function test_unavailable_preliminary_requires_explicit_choice(): void {
		wc_load_cart();
		$this->as_user( $this->customer()->get_id() );
		WC()->cart->empty_cart();
		$previous_post = $_POST; // phpcs:ignore WordPress.Security.NonceVerification.Missing -- Restore the test request.
		$tags          = $GLOBALS['shortcode_tags'];
		$failure       = 'not_found';
		$missing       = static function () use ( &$failure ) {
			return new \WP_Error( 'linker_planner_' . $failure, '', array( 'status' => 404 ) );
		};
		add_filter( 'linker_tools_planning_inquiry_note', $missing, 11 );
		add_filter( 'woocommerce_is_checkout', '__return_true' );
		$this->later(
			static function () use ( $missing, $previous_post, $tags ): void {
				$_POST                     = $previous_post;
				$GLOBALS['shortcode_tags'] = $tags;
				remove_filter( 'linker_tools_planning_inquiry_note', $missing, 11 );
				remove_filter( 'woocommerce_is_checkout', '__return_true' );
			}
		);
		$email   = 'roof-' . self::tag() . '@example.test';
		$project = str_repeat( '7', 32 ) . ':3';
		$stamp   = (string) ( time() - 5 );
		$_POST   = array(
			'action'                     => 'linker_inquiry',
			'linker_preliminary_project' => $project,
			'linker_inquiry_nonce'       => wp_create_nonce( 'linker_inquiry:' . $project ),
			'linker_draft_hash'          => WC()->cart->get_cart_hash(),
			'linker_started'             => $stamp,
			'linker_started_nonce'       => wp_create_nonce( 'linker_inquiry_started_' . $stamp ),
			'name'                       => 'Maria Weber',
			'message'                    => 'Please call about my roof.',
			'email'                      => $email,
			'consent'                    => '1',
		);
		$form    = new \Linker\Commerce\Inquiry\Form();
		$handler = new \Linker\Commerce\Inquiry\Handler( $form );
		$form->register();
		$marker = self::newest_mail_job();
		$handler->checkout_post();
		$html = $form->render();
		$this->assertStringNotContainsString( 'name="linker_without_project"', $html );
		$this->assertStringContainsString( 'Please call about my roof.</textarea>', $html );
		$failure = 'project_revision_not_found';
		$handler->checkout_post();
		$html = $form->render();
		$this->assertStringContainsString( 'This project is unavailable.', $html );
		if ( 1 !== preg_match( '/type="checkbox" required name="linker_without_project" value="([^"]+)"/', $html, $choice ) ) {
			$this->fail( 'Expected the explicit choice to send without the project.' );
		}
		$this->assertStringContainsString( 'value="Maria Weber"', $html );
		$this->assertStringContainsString( 'Please call about my roof.</textarea>', $html );
		$this->assertSame(
			array(),
			wc_get_orders(
				array(
					'billing_email' => $email,
					'return'        => 'ids',
				)
			)
		);
		$this->assertSame( array(), self::mail_jobs_after( $marker ) );
		$_POST['linker_without_project'] = 'not-the-offered-choice';
		$handler->checkout_post();
		$this->assertStringNotContainsString( 'name="linker_without_project" checked', $form->render() );
		$_POST['linker_without_project'] = $choice[1];
		$_POST['email']                  = 'not-an-email';
		$handler->checkout_post();
		$this->assertStringContainsString( 'name="linker_without_project" checked', $form->render() );
		$_POST['email'] = $email;
		$order          = $handler->process( $_POST ); // phpcs:ignore WordPress.Security.NonceVerification.Missing -- The native handler verifies both nonces.
		$this->assertInstanceOf( WC_Order::class, $order );
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		$this->assertSame( '', $order->get_meta( '_linker_preliminary_project' ) );
		$this->assertSame( 'Please call about my roof.', $order->get_customer_note() );
	}

	/** The retry can be rendered later under the same browser context only. */
	public function test_preliminary_retry_survives_checkout_navigation(): void {
		wc_load_cart();
		$previous_get = $_GET; // phpcs:ignore WordPress.Security.NonceVerification.Recommended -- Restore the test request.
		$tags         = $GLOBALS['shortcode_tags'];
		$this->later(
			static function () use ( $previous_get, $tags ): void {
				$_GET                      = $previous_get;
				$GLOBALS['shortcode_tags'] = $tags;
				WC()->session->set( 'linker_inquiry_checkout_retries', null );
			}
		);
		$project = str_repeat( 'b', 32 );
		$uuid    = wp_generate_uuid4();
		$form    = new \Linker\Commerce\Inquiry\Form();
		$form->register();
		$form->retry(
			array(
				'linker_preliminary_project'       => $project . ':5',
				'linker_request_id'                => $uuid,
				'linker_inquiry_original_language' => 'en',
				'linker_recovery_available'        => '1',
				'linker_draft_hash'                => 'original-draft',
				'linker_project_notes_present'     => '1',
				'linker_include_project_notes'     => '1',
				'linker_project_note_revisions'    => array( 'project_' . $project => '5' ),
				'message'                          => 'Keep this reply with my project.',
			),
			new \WP_Error( 'linker_inquiry_pending', 'Waiting for the earlier inquiry.' ),
			'en_US',
			''
		);
		$this->assertSame( 1, preg_match( '/name="linker_inquiry_retry" value="([^"]+)"/', $form->render(), $matches ) );
		$handle = $matches[1] ?? '';
		$this->assertNotSame( $uuid, $handle );
		$this->assertStringNotContainsString( 'Keep this reply with my project.', $form->render() );
		$_GET['linker_inquiry_retry'] = $handle;
		$retry                        = $form->render();
		$this->assertStringContainsString( 'Keep this reply with my project.', $retry );
		$this->assertStringContainsString( 'name="linker_preliminary_project" value="' . $project . ':5"', $retry );
		$this->assertStringContainsString( 'name="lang" value="en"', $retry );
		$this->assertStringContainsString( 'name="linker_draft_hash" value="original-draft"', $retry );
		$this->assertStringContainsString( 'name="linker_project_note_revisions[project_' . $project . ']" value="5"', $retry );
		if ( \Linker\Commerce\Protection\Business::enabled() ) {
			$this->assertStringContainsString( 'name="linker_request_id" value="' . $uuid . '"', $retry );
		}
		$other = $project . ':6';
		$stamp = (string) ( time() - 5 );
		$error = ( new \Linker\Commerce\Inquiry\Handler() )->process(
			array(
				'linker_inquiry_retry'       => $handle,
				'linker_preliminary_project' => $other,
				'linker_request_id'          => $uuid,
				'linker_inquiry_nonce'       => wp_create_nonce( 'linker_inquiry:' . $other ),
				'linker_started'             => $stamp,
				'linker_started_nonce'       => wp_create_nonce( 'linker_inquiry_started_' . $stamp ),
				'name'                       => 'Separate Customer Action',
				'email'                      => 'wrong-retry@example.test',
				'consent'                    => '1',
			)
		);
		$this->assertInstanceOf( \WP_Error::class, $error );
		$this->assertSame( 'linker_inquiry_invalid', $error->get_error_code() );
		$this->assertStringContainsString( 'Keep this reply with my project.', $form->render() );

		$this->as_user( $this->customer()->get_id() );
		$unbound = $form->render();
		$this->assertStringNotContainsString( 'Keep this reply with my project.', $unbound );
		$this->assertStringNotContainsString( 'class="linker-inquiry-form"', $unbound );
	}

	/** A bound project may not fall back to today's cart in a non-enforcing receiver. */
	public function test_preliminary_refuses_a_changed_draft_without_enforcement(): void {
		if ( defined( 'LINKER_PUBLIC_PROTECTION_MODE' ) ) {
			self::markTestSkipped( 'This fixture switches the native admission mode in its PHP process.' );
		}
		$previous_mode = getenv( 'LINKER_PUBLIC_PROTECTION_MODE' );
		$this->later(
			static function () use ( $previous_mode ): void {
				putenv( false === $previous_mode ? 'LINKER_PUBLIC_PROTECTION_MODE' : 'LINKER_PUBLIC_PROTECTION_MODE=' . $previous_mode ); // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.runtime_configuration_putenv -- Restore the isolated PHP fixture environment.
			}
		);
		wc_load_cart();
		WC()->cart->empty_cart();
		$this->later( static fn () => WC()->cart->empty_cart() );
		$reviewed = WC()->cart->get_cart_hash();
		$product  = $this->product( '20' );
		WC()->cart->add_to_cart( $product->get_id() );
		$this->assertNotSame( $reviewed, WC()->cart->get_cart_hash() );
		$project = str_repeat( 'c', 32 ) . ':9';
		$stamp   = (string) ( time() - 5 );
		$post    = array(
			'linker_preliminary_project' => $project,
			'linker_inquiry_nonce'       => wp_create_nonce( 'linker_inquiry:' . $project ),
			'linker_draft_hash'          => $reviewed,
			'linker_started'             => $stamp,
			'linker_started_nonce'       => wp_create_nonce( 'linker_inquiry_started_' . $stamp ),
			'name'                       => 'Marta Becker',
			'email'                      => 'reviewed-project@example.test',
			'consent'                    => '1',
		);
		foreach ( array( 'off', 'observe' ) as $mode ) {
			putenv( 'LINKER_PUBLIC_PROTECTION_MODE=' . $mode ); // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.runtime_configuration_putenv -- Restore the isolated PHP fixture environment.
			$result = ( new \Linker\Commerce\Inquiry\Handler() )->process( $post );
			$this->assertInstanceOf( \WP_Error::class, $result );
			$this->assertSame( 'linker_draft_changed', $result->get_error_code(), $mode );
		}
	}

	/** Retired Woo checkout transports cannot bypass the shared public inquiry sender. */
	public function test_alternate_checkout_transports_cannot_create_an_inquiry(): void {
		$this->as_user( 0 );
		$marker = self::newest_mail_job();
		$errors = new \WP_Error();
		do_action( 'woocommerce_after_checkout_validation', array(), $errors ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound, WooCommerce.Commenting.CommentHooks.MissingHookComment -- Woo's validation boundary.
		$this->assertTrue( $errors->has_errors() );
		foreach ( array( 'GET', 'POST' ) as $method ) {
			$response = rest_do_request( new \WP_REST_Request( $method, '/wc/store/v1/checkout' ) );
			$this->assertSame( 403, $response->get_status() );
			$this->assertSame( 'linker_inquiry_form_required', $response->get_data()['code'] );
		}
		$this->assertSame( array(), self::mail_jobs_after( $marker ) );
	}

	/** The public product button must reach the draft rather than require sign-in. */
	public function test_guest_product_action_adds_to_the_draft_without_opening_prices(): void {
		$this->as_user( 0 );
		$product = $this->product( '125' );
		$fields  = ( new \Linker\Commerce\Storefront\ProductView() )->fields( $product->get_id() );
		$this->assertSame( 'Add to solution draft', $fields['cta_label'] );
		$this->assertStringContainsString( 'add-to-cart=' . $product->get_id(), $fields['cta_url'] );
		$this->assertStringNotContainsString( '125', $fields['price']['html'] );
	}

	/**
	 * The actual LC request pages expand the form and localize the browser title.
	 *
	 * @dataProvider request_languages
	 * @param string $path Request page.
	 * @param string $title Localized title.
	 * @param string $message Message field label.
	 */
	public function test_public_request_page_in_both_languages( string $path, string $title, string $message ): void {
		$query    = array(
			'post_type'     => 'linker_conversation',
			'post_status'   => 'private',
			'numberposts'   => -1,
			'fields'        => 'ids',
			'cache_results' => false,
		);
		$existing = get_posts( $query );
		$response = wp_remote_get( home_url( $path ) );
		$created  = array_diff( get_posts( $query ), $existing );
		$this->later(
			static function () use ( $created ): void {
				foreach ( $created as $id ) {
					wp_delete_post( $id, true );
				}
			}
		);
		$this->assertSame( array(), $created, 'Reading the inquiry form must not create a Genie conversation.' );
		$this->assertIsArray( $response );
		$this->assertSame( 200, wp_remote_retrieve_response_code( $response ) );
		$html = wp_remote_retrieve_body( $response );
		$this->assertStringContainsString( '<title>' . $title . ' | Linker</title>', $html );
		$this->assertSame( 1, preg_match( '/<form class="linker-inquiry-form".*?<\/form>/s', $html, $matches ) );
		$form = $matches[0] ?? '';
		$this->assertStringContainsString( $message, $form );
		$this->assertStringContainsString( 'action="' . admin_url( 'admin-post.php' ) . '"', $form );
		$this->assertStringNotContainsString( '[linker_', $form );
		$this->assertStringNotContainsString( 'name="billing_country"', $form );
		$this->assertStringNotContainsString( 'name="billing_address_1"', $form );
	}

	/**
	 * The two public request URLs and independently written labels.
	 *
	 * @return array<string, array{string, string, string}>
	 */
	public static function request_languages(): array {
		return array(
			'en' => array( '/proforma-request/', 'Send an inquiry', 'Message (optional)' ),
			'de' => array( '/de/proforma-anfrage/', 'Anfrage senden', 'Nachricht (optional)' ),
		);
	}

	/** Blank guest fields must be real empty values rather than unevaluated template tags. */
	public function test_guest_form_renders_empty_fields_and_real_transport_attributes(): void {
		$this->as_user( 0 );
		wc_load_cart();
		$summary_calls = 0;
		$old_summary   = static function () use ( &$summary_calls ): array {
			++$summary_calls;
			return array( 'note' => 'Previous unrelated project question.' );
		};
		add_filter( 'linker_genie_inquiry_summary', $old_summary, 999 );
		$this->later(
			static function () use ( $old_summary ): void {
				remove_filter( 'linker_genie_inquiry_summary', $old_summary, 999 );
			}
		);
		$tags = $GLOBALS['shortcode_tags'];
		$this->later(
			static function () use ( $tags ): void {
				$GLOBALS['shortcode_tags'] = $tags;
			}
		);
		( new \Linker\Commerce\Inquiry\Form() )->register();
		$html = do_shortcode( '[linker_inquiry_form]' );
		$this->assertStringNotContainsString( '[linker_inquiry_', $html );
		$this->assertStringContainsString( 'id="inquiry-name" name="name"', $html );
		// The native draft form submits to the current request route and retains its real form class.
		$this->assertStringContainsString( '<form class="woocommerce-cart-form" method="post" action="' . wc_get_checkout_url() . '">', $html );
		$this->assertStringContainsString( 'value="" required', $html );
		$this->assertStringContainsString( 'action="' . admin_url( 'admin-post.php' ) . '"', $html );
		$this->assertStringNotContainsString( 'Previous unrelated project question.', $html );
		$this->assertSame( 0, $summary_calls, 'Opening the native form does not request a conversation summary.' );
		$this->assertStringContainsString( 'name="linker_inquiry_retained" value="0"', $html );
		$fields = WC()->session->get( 'linker_inquiry_fields' );
		$this->later(
			static function () use ( $fields ): void {
				WC()->session->set( 'linker_inquiry_fields', $fields );
			}
		);
		$literal = '[linker_inquiry_text key=title]';
		WC()->session->set( 'linker_inquiry_fields', array( 'message' => $literal ) );
		$retained = do_shortcode( '[linker_inquiry_form]' );
		$this->assertStringContainsString( '>' . esc_attr( $literal ) . '</textarea>', $retained );
		$this->assertStringContainsString( 'name="linker_inquiry_retained" value="1"', $retained );
		$this->assertNull( WC()->session->get( 'linker_inquiry_fields' ), 'The next render consumes the guest PII.' );
		$this->assertStringNotContainsString( esc_attr( $literal ), do_shortcode( '[linker_inquiry_form]' ), 'PII is never refilled a second time.' );
		WC()->session->set( 'linker_inquiry_fields', array( 'message' => '' ) );
		$cleared = do_shortcode( '[linker_inquiry_form]' );
		$this->assertStringContainsString( 'name="linker_inquiry_retained" value="1"', $cleared, 'An intentionally cleared failed submission is still customer input.' );
	}

	/** Retained validation feedback follows the language when the customer switches pages. */
	public function test_retained_error_changes_language_with_the_request_page(): void {
		wc_load_cart();
		$error  = WC()->session->get( 'linker_inquiry_error' );
		$locale = WC()->session->get( 'linker_inquiry_error_locale' );
		$this->later(
			static function () use ( $error, $locale ): void {
				WC()->session->set( 'linker_inquiry_error', $error );
				WC()->session->set( 'linker_inquiry_error_locale', $locale );
			}
		);
		WC()->session->set( 'linker_inquiry_error', 'Please add a product or write a message.' );
		WC()->session->set( 'linker_inquiry_error_locale', 'en_US' );
		$language = new \Linker\Commerce\Mail\LocaleSwitch();
		$language->to( 'de_DE_formal' );
		try {
			$this->assertStringContainsString( 'Bitte prüfen Sie Ihre Angaben und senden Sie das Formular erneut.', ( new \Linker\Commerce\Inquiry\Form() )->render() );
			$this->assertNull( WC()->session->get( 'linker_inquiry_error' ) );
		} finally {
			$language->back();
		}
	}

	/** A German form's validation does not send the customer back with English text. */
	public function test_german_form_validation_is_german(): void {
		$error = ( new \Linker\Commerce\Inquiry\Handler() )->process( array( 'lang' => 'de' ) );
		$this->assertInstanceOf( \WP_Error::class, $error );
		$this->assertSame( 'Bitte prüfen Sie Ihre Angaben und senden Sie das Formular erneut.', $error->get_error_message() );
	}


	/**
	 * The shared browser adapter honors its language field without global POST state.
	 */
	public function test_german_message_without_products_uses_the_german_receipt_and_url(): void {
		$this->as_user( 0 );
		wc_load_cart();
		WC()->cart->empty_cart();
		$summary_calls = 0;
		$old_summary   = static function () use ( &$summary_calls ): array {
			++$summary_calls;
			return array(
				'summary' => 'Previous unrelated project.',
				'note'    => 'Old customer question.',
			);
		};
		add_filter( 'linker_genie_inquiry_summary', $old_summary, 999 );
		$this->later(
			static function () use ( $old_summary ): void {
				remove_filter( 'linker_genie_inquiry_summary', $old_summary, 999 );
			}
		);
		$stamp = (string) ( time() - 5 );
		$order = ( new \Linker\Commerce\Inquiry\Handler() )->process(
			array(
				'name'                 => 'Maria Weber',
				'email'                => 'guest@example.test',
				'message'              => 'Bitte kontaktieren Sie mich.',
				'consent'              => '1',
				'lang'                 => 'de',
				'linker_inquiry_nonce' => wp_create_nonce( 'linker_inquiry' ),
				'linker_started'       => $stamp,
				'linker_started_nonce' => wp_create_nonce( 'linker_inquiry_started_' . $stamp ),
			)
		);
		$this->assertInstanceOf( WC_Order::class, $order );
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		$this->assertSame( 'de_DE_formal', $order->get_meta( '_linker_locale' ) );
		$this->assertStringContainsString( '/de/proforma-anfrage/', $order->get_checkout_order_received_url() );
		$this->assertSame( 0, $order->get_item_count() );
		$this->assertSame( array(), $order->get_order_item_totals(), 'A message alone has no monetary total.' );
		$this->assertSame( 'Bitte kontaktieren Sie mich.', $order->get_customer_note() );
		$this->assertSame( '', $order->get_meta( Sender::SUMMARY_META ) );
		$this->assertSame( 0, $summary_calls, 'The ordinary form does not silently attach an old Genie conversation.' );
	}

	/** Admin-post is an admin request; the stored product line must still use the form's language. */
	public function test_german_product_inquiry_keeps_canonical_product_and_translated_line(): void {
		$this->as_user( 0 );
		wc_load_cart();
		WC()->cart->empty_cart();
		$this->later( static fn () => WC()->cart->empty_cart() );
		$english = $this->product( '125' );
		$german  = $this->product( '125' );
		$german->set_name( 'Testprodukt für eine Anfrage' );
		$german->save();
		pll_set_post_language( $english->get_id(), 'en' );
		pll_set_post_language( $german->get_id(), 'de' );
		pll_save_post_translations(
			array(
				'en' => $english->get_id(),
				'de' => $german->get_id(),
			)
		);
		WC()->cart->add_to_cart( $english->get_id(), 2 );
		$details = Submission::from_post(
			array(
				'name'    => 'Maria Test',
				'email'   => 'guest@example.test',
				'consent' => '1',
				'lang'    => 'de',
			),
			false
		);
		$this->assertInstanceOf( Submission::class, $details );
		$order = ( new Sender() )->request( $details );
		$this->assertInstanceOf( WC_Order::class, $order );
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		$item = current( $order->get_items() );
		$this->assertInstanceOf( \WC_Order_Item_Product::class, $item );
		$this->assertSame( $english->get_id(), $item->get_product_id() );
		$this->assertSame( 'Testprodukt für eine Anfrage', $item->get_name() );
	}

	/**
	 * All invalid public attempts stop before records or notifications exist.
	 */
	public function test_bots_and_invalid_details_cannot_create_an_inquiry_or_mail(): void {
		$this->as_user( 0 );
		$marker = self::newest_mail_job();
		$stamp  = (string) ( time() - 5 );
		$post   = array(
			'name'                 => 'Maria Weber',
			'email'                => 'bot-' . self::tag() . '@example.test',
			'message'              => 'A question.',
			'consent'              => '1',
			'linker_inquiry_nonce' => wp_create_nonce( 'linker_inquiry' ),
			'linker_started'       => $stamp,
			'linker_started_nonce' => wp_create_nonce( 'linker_inquiry_started_' . $stamp ),
		);
		$now    = (string) time();
		foreach ( array(
			array( 'website' => 'spam' ),
			array(
				'linker_started'       => $now,
				'linker_started_nonce' => wp_create_nonce( 'linker_inquiry_started_' . $now ),
			),
			array( 'linker_started_nonce' => 'forged' ),
			array( 'linker_inquiry_nonce' => 'forged' ),
			array( 'name' => '' ),
			array( 'email' => 'invalid' ),
			array( 'consent' => '' ),
		) as $invalid ) {
			$this->assertInstanceOf( \WP_Error::class, ( new \Linker\Commerce\Inquiry\Handler() )->process( array_replace( $post, $invalid ) ) );
		}
		$this->assertSame(
			array(),
			wc_get_orders(
				array(
					'billing_email' => $post['email'],
					'return'        => 'ids',
				)
			)
		);
		$this->assertSame( array(), self::mail_jobs_after( $marker ) );
	}

	/**
	 * The receipt key is needed to attach an inquiry to an optional new account.
	 */
	public function test_account_link_claim_requires_both_the_key_and_the_same_email(): void {
		$customer = $this->customer();
		$order    = new WC_Order();
		$order->set_billing_email( $customer->get_billing_email() );
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		$order->set_customer_id( 0 );
		$order->save();
		$saved = $_GET; // phpcs:ignore WordPress.Security.NonceVerification.Recommended -- Saving test request state.
		$this->later(
			static function () use ( $saved ): void {
				$_GET = $saved;
			}
		);
		$_GET = array(
			'linker_inquiry' => $order->get_id(),
			'linker_key'     => 'forged',
		);
		$link = new \Linker\Commerce\Inquiry\AccountLink();
		$link->claim( $customer->get_id() );
		$this->assertSame( '', $link::email() );
		$loaded = wc_get_order( $order->get_id() );
		$this->assertInstanceOf( WC_Order::class, $loaded );
		$this->assertSame( 0, $loaded->get_customer_id() );
		$_GET['linker_key'] = $order->get_order_key();
		$this->assertSame( $customer->get_billing_email(), $link::email() );
		$link->claim( $customer->get_id() );
		$loaded = wc_get_order( $order->get_id() );
		$this->assertInstanceOf( WC_Order::class, $loaded );
		$this->assertSame( $customer->get_id(), $loaded->get_customer_id() );
	}

	/**
	 * A guest can send products without an account or an address.
	 */
	public function test_guest_sends_the_solution_draft_and_receives_a_receipt(): void {
		$this->as_user( 0 );
		wc_load_cart();
		WC()->cart->empty_cart();
		$this->later( static fn () => WC()->cart->empty_cart() );
		$product = $this->product( '125' );
		WC()->cart->add_to_cart( $product->get_id(), 2 );
		WC()->cart->calculate_totals();
		delete_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION );
		update_option( Throttle::OPTION, array_fill( 0, Throttle::PER_MINUTE, time() ), false );
		$details = Submission::from_post(
			array(
				'name'    => 'Maria Weber',
				'email'   => 'guest@example.test',
				'consent' => '1',
			),
			false
		);
		$this->assertInstanceOf( Submission::class, $details );
		$order = ( new Sender() )->request( $details );
		$this->assertInstanceOf( WC_Order::class, $order );
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		$this->assertSame( 'inquiry-received', $order->get_status() );
		$this->assertSame( 0, $order->get_customer_id() );
		$this->assertSame( 'guest@example.test', $order->get_billing_email() );
		$this->assertSame( '', $order->get_billing_country() );
		$this->assertSame( 2, $order->get_item_count() );
		$this->assertSame( array(), $order->get_order_item_totals(), 'Unpriced inquiries must not present zero as a quoted total.' );
		$product = wc_get_product( $product->get_id() );
		$this->assertInstanceOf( \WC_Product::class, $product );
		$this->assertSame( '10', (string) $product->get_stock_quantity() );
	}
	/**
	 * Bots must be stopped before a record or email can be created.
	 */
	public function test_public_guard_requires_a_signed_time_and_an_empty_honeypot(): void {
		$stamp  = (string) ( time() - 5 );
		$post   = array(
			'linker_started'       => $stamp,
			'linker_started_nonce' => wp_create_nonce( 'linker_inquiry_started_' . $stamp ),
			'website'              => '',
		);
		$fields = ( new PublicGuard() )->fields();
		$this->assertStringContainsString( 'name="website"', $fields, 'Both doors receive the trap from the shared guard.' );
		$this->assertStringContainsString( 'aria-label="Website"', $fields );
		$this->assertTrue( ( new PublicGuard() )->allows( $post ) );
		$this->assertFalse( ( new PublicGuard() )->allows( array_replace( $post, array( 'website' => 'spam' ) ) ) );
		$this->assertFalse( ( new PublicGuard() )->allows( array_replace( $post, array( 'linker_started' => (string) time() ) ) ) );
		$this->assertFalse( ( new PublicGuard() )->allows( array_replace( $post, array( 'linker_started_nonce' => 'forged' ) ) ) );
	}
	/**
	 * Contact submissions must be visible in the same native inquiry list.
	 */
	public function test_contact_message_creates_one_inquiry_without_consuming_the_draft(): void {
		$this->as_user( 0 );
		wc_load_cart();
		WC()->cart->empty_cart();
		$this->later( static fn () => WC()->cart->empty_cart() );
		$product = $this->product( '100' );
		WC()->cart->add_to_cart( $product->get_id(), 1 );
		$stamp = (string) ( time() - 5 );
		$email = 'contact-' . self::tag() . '@example.test';
		$post  = array(
			'name'                 => 'Maria Weber',
			'email'                => $email,
			'message'              => 'A contact question.',
			'consent'              => '1',
			'linker_contact_nonce' => wp_create_nonce( 'linker_contact_form' ),
			'linker_started'       => $stamp,
			'linker_started_nonce' => wp_create_nonce( 'linker_inquiry_started_' . $stamp ),
		);
		WC()->mailer();
		$address                = $_SERVER['REMOTE_ADDR'] ?? null; // phpcs:ignore WordPress.Security.ValidatedSanitizedInput -- Preserve the exact test runner value for restoration.
		$_SERVER['REMOTE_ADDR'] = '127.246.0.1';
		$limit_key              = 'linker_contact_' . md5( '127.246.0.1' );
		$recent                 = get_transient( $limit_key );
		delete_transient( $limit_key );
		$this->later(
			static function () use ( $limit_key, $recent, $address ): void {
				delete_transient( $limit_key );
				if ( false !== $recent ) {
					set_transient( $limit_key, $recent, HOUR_IN_SECONDS );
				} if ( null === $address ) {
					unset( $_SERVER['REMOTE_ADDR'] );
				} else {
					$_SERVER['REMOTE_ADDR'] = $address;
				}
			}
		);
		$handler = new \Linker\Commerce\Contact\Handler();
		$this->assertSame( 'receipt_pending', $handler->process( $post ) );
		$orders = wc_get_orders(
			array(
				'billing_email' => $email,
				'limit'         => -1,
			)
		);
		$this->assertIsArray( $orders );
		foreach ( $orders as $order ) {
			$this->later(
				static function () use ( $order ): void {
					$order->delete( true );
				}
			);
		}
		$this->assertCount( 1, $orders );
		$orders[0]->read_meta_data( true );
		$this->assertSame( 'assessment_pending', (string) $orders[0]->get_meta( \Linker\Commerce\Inquiry\ReceiptLimit::SKIPPED_META ) );
		$this->assertSame( 'inquiry-received', $orders[0]->get_status() );
		$this->assertSame( 0, $orders[0]->get_item_count() );
		$this->assertSame( 'A contact question.', $orders[0]->get_customer_note() );
		$this->assertSame( 1, WC()->cart->get_cart_contents_count() );
	}
	/**
	 * Approval controls price visibility, never whether an inquiry may be sent.
	 *
	 * @dataProvider account_states
	 * @param        string $status Account status.
	 */
	public function test_every_account_state_sends_with_its_saved_details( string $status ): void {
		$customer = $this->customer();
		update_user_meta( $customer->get_id(), 'billing_vat_id', 'DE123456789' );
		update_user_meta( $customer->get_id(), 'linker_vat_status', 'valid' );
		update_user_meta( $customer->get_id(), 'linker_vat_checked_number', 'DE123456789' );
		update_user_meta( $customer->get_id(), \Linker\Commerce\Registration\Approval::STATUS_META, $status );
		$this->as_user( $customer->get_id() );
		wc_load_cart();
		WC()->cart->empty_cart();
		$this->later( static fn () => WC()->cart->empty_cart() );
		$product = $this->product( '125' );
		WC()->cart->add_to_cart( $product->get_id(), 2 );
		$stamp  = (string) ( time() - 5 );
		$post   = array(
			'name'                 => 'Maria Beispiel',
			'email'                => $customer->get_billing_email(),
			'consent'              => '1',
			'linker_inquiry_nonce' => wp_create_nonce( 'linker_inquiry' ),
			'linker_started'       => $stamp,
			'linker_started_nonce' => wp_create_nonce( 'linker_inquiry_started_' . $stamp ),
		);
		$result = ( new \Linker\Commerce\Inquiry\Handler() )->process( $post );
		$this->assertInstanceOf( WC_Order::class, $result );
		$this->later(
			static function () use ( $result ): void {
				$result->delete( true );
			}
		);
		$this->assertSame( 'inquiry-received', $result->get_status() );
		$this->assertSame( $customer->get_id(), $result->get_customer_id() );
		$this->assertSame( 'Teststraße 1', $result->get_billing_address_1() );
		$this->assertSame( 'DE123456789', $result->get_meta( '_billing_vat_id' ) );
		$this->assertSame( 'valid', get_user_meta( $customer->get_id(), 'linker_vat_status', true ) );
		$this->assertSame( 2, $result->get_item_count() );
		foreach ( $result->get_items() as $line ) {
			$this->assertInstanceOf( \WC_Order_Item_Product::class, $line );
			$this->assertSame( 'approved' === $status ? '' : ( 'pending' === $status ? 'approval' : 'unavailable' ), $line->get_meta( '_linker_price_reason' ) );
		}
	}

	/** An account without any stored name still prefills the required reply name. */
	public function test_signed_in_form_prefills_the_display_name_when_no_name_is_saved(): void {
		$customer = $this->customer();
		foreach ( array( 'billing_first_name', 'billing_last_name', 'first_name', 'last_name' ) as $meta ) {
			delete_user_meta( $customer->get_id(), $meta );
		}
		$this->as_user( $customer->get_id() );
		wc_load_cart();
		$tags = $GLOBALS['shortcode_tags'];
		$this->later(
			static function () use ( $tags ): void {
				$GLOBALS['shortcode_tags'] = $tags;
			}
		);
		( new \Linker\Commerce\Inquiry\Form() )->register();
		$html = do_shortcode( '[linker_inquiry_form]' );
		$user = get_userdata( $customer->get_id() );
		$this->assertInstanceOf( \WP_User::class, $user );
		$display = (string) $user->display_name;
		$this->assertNotSame( '', $display );
		// The required name input carries the account identity instead of an
		// empty value whose native validation would block the submit silently.
		$this->assertStringContainsString( 'id="inquiry-name" name="name"', $html );
		$this->assertSame( 1, preg_match( '/id="inquiry-name"[^>]*value="([^"]*)"/', $html, $input ), 'The reply-name input is rendered with a value.' );
		$value = $input[1] ?? '';
		$this->assertSame( $display, html_entity_decode( $value, ENT_QUOTES ) );
	}

	/** The signed-in inquiry is attributed to the account and confirms on the native receipt. */
	public function test_signed_in_inquiry_without_saved_name_is_attributed_and_confirms(): void {
		$customer = $this->customer();
		foreach ( array( 'billing_first_name', 'billing_last_name', 'first_name', 'last_name' ) as $meta ) {
			delete_user_meta( $customer->get_id(), $meta );
		}
		$this->as_user( $customer->get_id() );
		wc_load_cart();
		WC()->cart->empty_cart();
		$this->later( static fn () => WC()->cart->empty_cart() );
		$product = $this->product( '125' );
		WC()->cart->add_to_cart( $product->get_id(), 1 );
		$user = get_userdata( $customer->get_id() );
		$this->assertInstanceOf( \WP_User::class, $user );
		$stamp  = (string) ( time() - 5 );
		$post   = array(
			'name'                 => (string) $user->display_name,
			'email'                => $customer->get_billing_email(),
			'consent'              => '1',
			'linker_inquiry_nonce' => wp_create_nonce( 'linker_inquiry' ),
			'linker_started'       => $stamp,
			'linker_started_nonce' => wp_create_nonce( 'linker_inquiry_started_' . $stamp ),
		);
		$result = ( new \Linker\Commerce\Inquiry\Handler() )->process( $post );
		$this->assertInstanceOf( WC_Order::class, $result );
		$this->later(
			static function () use ( $result ): void {
				$result->delete( true );
			}
		);
		$this->assertSame( 'inquiry-received', $result->get_status() );
		$this->assertSame( $customer->get_id(), $result->get_customer_id(), 'The signed-in account owns its inquiry, never customer 0.' );
		$received = $result->get_checkout_order_received_url();
		$this->assertMatchesRegularExpression( '#inquiry-received/' . $result->get_id() . '/\?key=' . $result->get_order_key() . '#', $received );
	}

	/**
	 * Billing edits apply only to this inquiry, including clearing or changing VAT.
	 *
	 * @testWith ["", "none"]
	 *           ["CHE123456789", "unverified"]
	 * @param string $vat Inquiry-specific VAT.
	 * @param string $verdict Expected inquiry verdict.
	 */
	public function test_account_billing_fields_prefill_and_send_the_edited_address( string $vat, string $verdict ): void {
		$customer = $this->customer();
		$customer->update_meta_data( 'billing_vat_id', 'DE123456789' );
		$customer->save();
		update_user_meta( $customer->get_id(), 'linker_vat_checked_number', 'DE123456789' );
		update_user_meta( $customer->get_id(), 'linker_vat_status', 'valid' );
		$account_vat = array();
		foreach ( array( 'billing_vat_id', 'linker_vat_status', 'linker_vat_detail', 'linker_vat_checked_number', 'linker_vat_checked_at' ) as $key ) {
			$account_vat[ $key ] = get_user_meta( $customer->get_id(), $key, true );
		}
		$this->as_user( $customer->get_id() );
		wc_load_cart();
		WC()->cart->empty_cart();
		$fields = \Linker\Commerce\Inquiry\BillingFields::render();
		$this->assertStringContainsString( 'name="billing_address_1"', $fields );
		$this->assertStringContainsString( 'value="Teststraße 1"', $fields );
		$this->assertStringContainsString( 'name="billing_vat_id"', $fields );
		$this->assertStringContainsString( 'value="DE123456789"', $fields );
		$stamp  = (string) ( time() - 5 );
		$result = ( new \Linker\Commerce\Inquiry\Handler() )->process(
			array(
				'name'                 => 'Maria Beispiel',
				'email'                => $customer->get_billing_email(),
				'message'              => 'Please send a Proforma for this address.',
				'consent'              => '1',
				'billing_address_1'    => 'Teststraße 246',
				'billing_vat_id'       => $vat,
				'linker_inquiry_nonce' => wp_create_nonce( 'linker_inquiry' ),
				'linker_started'       => $stamp,
				'linker_started_nonce' => wp_create_nonce( 'linker_inquiry_started_' . $stamp ),
			)
		);
		$this->assertInstanceOf( WC_Order::class, $result );
		$this->later(
			static function () use ( $result ): void {
				$result->delete( true );
			}
		);
		$this->assertSame( 'Teststraße 246', $result->get_billing_address_1() );
		$this->assertSame( $vat, $result->get_meta( '_billing_vat_id' ) );
		$this->assertSame( $verdict, $result->get_meta( '_linker_vat_status' ) );
		foreach ( $account_vat as $key => $saved ) {
			$this->assertSame( $saved, get_user_meta( $customer->get_id(), $key, true ), 'Inquiry edits preserve account VAT metadata: ' . $key );
		}
		$this->as_user( 0 );
		$this->assertSame( '', \Linker\Commerce\Inquiry\BillingFields::render(), 'Guests are never asked for billing fields.' );
		$this->assertSame( array(), \Linker\Commerce\Inquiry\BillingFields::values( array( 'billing_country' => 'DE' ) ), 'Guest billing input is ignored.' );
	}

	/** Restricted accounts read the reason above a usable form in both languages. */
	public function test_restricted_reason_does_not_close_the_request_form(): void {
		$customer = $this->customer();
		update_user_meta( $customer->get_id(), \Linker\Commerce\Registration\Approval::STATUS_META, 'restricted' );
		update_user_meta( $customer->get_id(), \Linker\Commerce\Registration\Approval::REASON_META, 'Please add your company VAT ID.' );
		$this->as_user( $customer->get_id() );
		wc_load_cart();
		$tags = $GLOBALS['shortcode_tags'];
		$this->later(
			static function () use ( $tags ): void {
				$GLOBALS['shortcode_tags'] = $tags;
			}
		);
		( new \Linker\Commerce\Inquiry\Form() )->register();
		$language = new \Linker\Commerce\Mail\LocaleSwitch();
		foreach ( array(
			'en_US'        => 'You can send inquiries.',
			'de_DE_formal' => 'Sie können Anfragen senden.',
		) as $locale => $notice ) {
			$language->to( $locale );
			try {
				$html = do_shortcode( '[linker_inquiry_form]' );
				$this->assertStringContainsString( $notice, $html );
				$this->assertStringContainsString( 'Please add your company VAT ID.', $html );
				$this->assertLessThan( strpos( $html, '<form ' ), strpos( $html, 'Please add your company VAT ID.' ) );
				$this->assertStringContainsString( 'type="submit"', $html );
				$this->assertStringNotContainsString( 'paused', $html );
			} finally {
				$language->back();
			}
		}
	}

	/**
	 * Account states from the owner ruling.
	 *
	 * @return array<string, array{string}>
	 */
	public static function account_states(): array {
		return array(
			'pending'    => array( 'pending' ),
			'restricted' => array( 'restricted' ),
			'approved'   => array( 'approved' ),
		);
	}

	/**
	 * The actual sender queues one team notification and one receipt.
	 */
	public function test_sender_routes_the_team_mail_and_receipt_through_outbox(): void {
		$this->as_user( 0 );
		wc_load_cart();
		WC()->cart->empty_cart();
		$saved = array();
		foreach ( array( 'linker_commerce_notify_to', 'linker_commerce_team_bcc', 'woocommerce_linker_new_inquiry_settings', 'woocommerce_linker_inquiry_received_settings' ) as $option ) {
			$saved[ $option ] = get_option( $option );
			delete_option( $option );
		}
		$this->later(
			static function () use ( $saved ): void {
				foreach ( $saved as $option => $value ) {
					if ( false === $value ) {
						delete_option( $option );
					} else {
						update_option( $option, $value );
					}
				}
			}
		);
		delete_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION );
		update_option( Throttle::OPTION, array_fill( 0, Throttle::PER_MINUTE, time() ), false );
		$marker  = self::newest_mail_job();
		$details = Submission::from_post(
			array(
				'name'    => 'Maria Weber',
				'email'   => 'guest@example.test',
				'message' => 'Please help with my project.',
				'consent' => '1',
			)
		);
		$this->assertInstanceOf( Submission::class, $details );
		$order = ( new Sender() )->message( $details );
		$this->assertInstanceOf( WC_Order::class, $order );
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		$this->authorization->drain();
		$rows = array_map( static fn ( int $id ) => json_decode( (string) get_post_meta( $id, '_linker_mail_message', true ), true ), self::mail_jobs_after( $marker ) );
		$this->assertCount( 2, $rows );
		$recipients = array_column( $rows, 'to' );
		$this->assertContains( array( 'sales@sunriverinverter.com' ), $recipients );
		$this->assertContains( array( 'guest@example.test' ), $recipients );
		$this->assertNotContains( array( 'sales@de-linker.com' ), $recipients );
	}
}
