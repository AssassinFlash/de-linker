<?php
/**
 * Tests for the contact form's markup.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Contact;

use Linker\Commerce\Contact\Form;
use Linker\Commerce\Contact\Submission;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Tests for Form: the card the live /contact/ pages showed — its blocks and
 * fields in their order, the two side cards, the protections of a public form
 * and the states the redirect leaves (ticket #68; the composition from the
 * 2026-10-12/13 captures, docs/acceptance/2026-10-14/contact-form/).
 *
 * @covers \Linker\Commerce\Contact\Form
 */
final class FormTest extends TestCase {


	/**
	 * The card carries the live card's blocks in their order — heading,
	 * question, topic, reply details, consent and the send row — and, inside
	 * them, the live card's fields and the protections of a public form.
	 */
	public function test_renders_the_card(): void {
		$this->plain_text();
		$this->form_environment();
		$this->english_site();

		$html = ( new Form() )->render();

		$this->assertStringContainsString( '<div class="linker-contact-card">', $html );
		$this->assertStringContainsString( '<form class="linker-contact-form', $html );
		$this->assertStringContainsString( 'action="http://site/wp-admin/admin-post.php"', $html );
		$this->assertStringContainsString( 'name="action" value="linker_contact"', $html );
		$this->assertStringContainsString( 'name="lang" value="en"', $html );
		$this->assertStringContainsString( 'name="linker_contact_back" value="http://site/contact/"', $html );
		$this->assertStringContainsString( 'name="linker_contact_nonce"', $html );

		// The heading block: eyebrow, heading, lead.
		$this->assertStringContainsString( 'linker-contact-head', $html );
		$this->assertStringContainsString( 'CONTACT LINKER', $html );
		$this->assertStringContainsString( '<h2>What can we help with?</h2>', $html );
		$this->assertStringContainsString( 'Tell us what you need. We’ll use the email below for your reply.', $html );

		// The question block: its label and the prompt as the placeholder.
		$this->assertStringContainsString( 'linker-contact-question', $html );
		$this->assertStringContainsString( 'Your question', $html );
		$this->assertStringContainsString( 'placeholder="What would you like to know?"', $html );

		// The topic block: its label and the select.
		$this->assertStringContainsString( 'linker-contact-topic', $html );
		$this->assertStringContainsString( 'This is about', $html );
		$this->assertStringContainsString( 'name="intent"', $html );

		// The reply block: its heading, the fields, the note.
		$this->assertStringContainsString( 'linker-contact-reply', $html );
		$this->assertStringContainsString( '<h3>Where can we reply?</h3>', $html );
		$this->assertStringContainsString( 'linker-form-fields', $html );
		$this->assertStringContainsString( 'No account or Project is needed to ask a question.', $html );

		// The end block: consent with the privacy link, the honeypot, the send row.
		$this->assertStringContainsString( 'linker-contact-end', $html );
		$this->assertStringContainsString( 'href="http://site/privacy-policy/"', $html );
		$this->assertStringContainsString( '<div hidden aria-hidden="true">', $html, 'The honeypot is hidden from people.' );
		$this->assertStringContainsString( 'name="website"', $html );
		$this->assertStringContainsString( 'type="submit"', $html );
		// The three strings the #68 review settled keep its wording
		// (docs/acceptance/2026-10-15/contact-card/copy-review.md §1).
		$this->assertStringContainsString( 'I agree that my details may be used to respond to this message.', $html );
		$this->assertStringContainsString( 'Send message', $html );
		$this->assertStringContainsString( 'Your message goes to the Linker team. We reply to the address you give here.', $html );

		foreach ( array( 'name="message"', 'name="name"', 'name="email"', 'name="company"', 'name="consent"' ) as $field ) {
			$this->assertStringContainsString( $field, $html );
		}
		$this->assertStringContainsString( 'maxlength="' . Submission::MAX_MESSAGE . '"', $html );

		// The blocks keep the live card's order, the side cards follow the form.
		$order = array(
			'linker-contact-head',
			'linker-contact-question',
			'linker-contact-topic',
			'linker-contact-reply',
			'linker-contact-end',
			'</form>',
			'linker-contact-rail',
		);
		$at    = -1;
		foreach ( $order as $block ) {
			$found = strpos( $html, $block );
			$this->assertIsInt( $found, $block . ' is in the card.' );
			$this->assertGreaterThan( $at, $found, $block . ' follows the block before it.' );
			$at = $found;
		}
	}

	/**
	 * The topic select offers the live card's topics, the general one selected
	 * when the request brought none.
	 */
	public function test_renders_the_topic_select(): void {
		$this->plain_text();
		$this->form_environment();
		$this->english_site();

		$html = ( new Form() )->render();

		$this->assertStringContainsString( '<select class="linker-form-input" id="linker-contact-intent" name="intent">', $html );
		$this->assertStringContainsString( '<option value="general" selected>A question</option>', $html );
		foreach ( array(
			'product'     => 'Product guidance',
			'offer'       => 'Price & availability',
			'document'    => 'Product documents',
			'project'     => 'Discuss a project',
			'support'     => 'Support for an order',
			'partnership' => 'Work with Linker',
		) as $value => $label ) {
			$this->assertStringContainsString( '<option value="' . $value . '">' . $label . '</option>', $html );
		}
		$this->assertSame( 1, preg_match_all( '/<option\b[^>]* selected/', $html ), 'One topic is selected.' );
		$this->assertSame( \count( Form::INTENTS ), substr_count( $html, '<option value="' ) );
	}

	/**
	 * A visitor who arrived through a contact link that carries a topic —
	 * `?intent=project`, the address the site's own invitation band builds —
	 * finds that topic selected; an unknown value is the general one.
	 */
	public function test_selects_the_topic_of_the_address(): void {
		$this->plain_text();
		$this->form_environment();
		$this->english_site();

		$_GET    = array( Submission::INTENT_FIELD => 'project' );
		$project = ( new Form() )->render();
		$this->assertStringContainsString( '<option value="project" selected>Discuss a project</option>', $project );
		$this->assertStringNotContainsString( '<option value="general" selected>', $project );

		$_GET  = array( Submission::INTENT_FIELD => 'anything-else' );
		$other = ( new Form() )->render();
		$this->assertStringContainsString( '<option value="general" selected>A question</option>', $other );
		$_GET = array();
	}

	/**
	 * The side cards: the direct address of the team mailbox this form writes
	 * to, and the way into Genie — both under the card, as on the live page.
	 */
	public function test_renders_the_side_cards(): void {
		$this->plain_text();
		$this->form_environment();
		$this->english_site();

		$html = ( new Form() )->render();

		$this->assertStringContainsString( '<aside class="linker-contact-rail">', $html );
		$this->assertStringContainsString( 'linker-contact-email', $html );
		$this->assertStringContainsString( 'Prefer email?', $html );
		$this->assertStringContainsString( 'href="mailto:sales@de-linker.com"', $html );
		$this->assertStringContainsString( 'Send your question directly to our team. Opening your email app does not send a message.', $html );
		$this->assertStringContainsString( 'linker-contact-explore', $html );
		$this->assertStringContainsString( 'Still exploring?', $html );
		$this->assertStringContainsString( 'Take your time.', $html );
		$this->assertStringContainsString( 'Use Genie to explore the options, then return to your question.', $html );
		$this->assertStringContainsString( 'href="http://site/genie/"', $html );
		$this->assertStringContainsString( 'Explore with Genie', $html );
	}

	/**
	 * The German page renders the same card — its blocks, fields and side
	 * cards — posts `de` as the language, and links the German Genie page
	 * (Polylang twin). The German words themselves are the catalog's
	 * (languages/linker-commerce-de_DE_formal.po, gated by `just
	 * i18n-coverage`); the renderer answers the page language for every
	 * string it prints.
	 */
	public function test_renders_in_the_page_language(): void {
		$this->plain_text();
		$this->form_environment( 'de_DE_formal' );
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'de' ) );
		WP_Mock::userFunction( 'get_page_by_path', array( 'return' => new \WP_Post( (object) array( 'ID' => 40 ) ) ) );
		WP_Mock::userFunction( 'pll_get_post', array( 'return' => 41 ) );
		$this->settings_environment();
		WP_Mock::userFunction( 'home_url', array( 'return' => static fn ( string $path = '/' ): string => 'http://site' . $path ) );

		$html = ( new Form() )->render();
		$this->assertStringContainsString( 'name="lang" value="de"', $html );
		foreach ( array( 'linker-contact-head', 'linker-contact-question', 'linker-contact-topic', 'linker-contact-reply', 'linker-contact-end', 'linker-contact-rail' ) as $block ) {
			$this->assertStringContainsString( $block, $html );
		}
		$this->assertStringContainsString( 'href="http://site/de/genie/"', $html );
	}

	/**
	 * The redirect's state shows above the fields; a fresh visit shows nothing.
	 * A sent message keeps the card and its side cards, without another form.
	 */
	public function test_state_messages(): void {
		$this->plain_text();
		$this->form_environment();
		$this->english_site();

		$_GET = array();
		$this->assertStringNotContainsString( 'role="status"', ( new Form() )->render() );

		$_GET = array( Form::STATE_PARAM => 'sent' );
		$sent = ( new Form() )->render();
		$this->assertStringContainsString( 'role="status"', $sent );
		$this->assertStringContainsString( 'linker-form-success woocommerce-message', $sent );
		$this->assertStringContainsString( 'Send another message', $sent );
		$this->assertStringContainsString( '<div class="linker-contact-card"><div class="linker-contact-form linker-contact-receipt">', $sent, 'The receipt keeps the card, as the panel itself.' );
		$this->assertStringContainsString( 'linker-contact-rail', $sent );
		$this->assertStringNotContainsString( 'type="submit"', $sent, 'A sent message has one follow-up action, not another form.' );

		$_GET    = array( Form::STATE_PARAM => 'invalid' );
		$invalid = ( new Form() )->render();
		$this->assertStringContainsString( 'linker-form-error woocommerce-error', $invalid );
		$this->assertStringContainsString( 'role="alert"', $invalid );
		$this->assertStringContainsString( 'type="submit"', $invalid, 'An invalid submission keeps the form available.' );

		$_GET = array( Form::STATE_PARAM => 'throttled' );
		$this->assertStringContainsString( 'You can try again later', ( new Form() )->render() );

		$_GET = array( Form::STATE_PARAM => 'something-else' );
		$this->assertStringNotContainsString( 'role="status"', ( new Form() )->render() );
		$_GET = array();
	}

	/** Read-only selection arrives visibly, and a failed native POST retains the removal choice and message. */
	public function test_selection_is_visible_and_native_recovery_preserves_the_original_message_and_exclusion(): void {
		$this->plain_text();
		WP_Mock::userFunction(
			'pll_get_post',
			array(
				'args'   => array( 12, 'en' ),
				'return' => 12,
			)
		);
		WP_Mock::userFunction( 'wp_parse_url', array( 'return' => static fn ( string $url, int $component = -1 ) => parse_url( $url, $component ) ) );
		WP_Mock::userFunction( 'url_to_postid', array( 'return' => 12 ) );
		WP_Mock::userFunction(
			'get_post',
			array(
				'return' => new \WP_Post(
					(object) array(
						'ID'            => 12,
						'post_type'     => 'page',
						'post_title'    => 'Products',
						'post_password' => '',
					)
				),
			)
		);
		WP_Mock::userFunction(
			'get_permalink',
			array(
				'return' => static function ( $post = null ): string {
					$id = $post instanceof \WP_Post ? (int) $post->ID : (int) $post;
					return 12 === $id ? 'http://site/products/%c3%a4/' : ( 60 === $id ? 'http://site/genie/' : 'http://site/contact/' );
				},
			)
		);
		WP_Mock::userFunction( 'get_the_title', array( 'return' => 'Products' ) );
		WP_Mock::userFunction( 'sanitize_text_field', array( 'return' => static fn ( string $value ): string => $value ) );
		WP_Mock::userFunction( 'sanitize_textarea_field', array( 'return' => static fn ( string $value ): string => preg_replace( '/%[a-f0-9]{2}/i', '', $value ) ?? '' ) );
		WP_Mock::userFunction( 'wp_json_encode', array( 'return' => static fn ( $value ) => json_encode( $value ) ) );
		WP_Mock::userFunction( 'add_query_arg', array( 'return' => static fn ( array $query, string $url ): string => $url . '?' . http_build_query( $query ) ) );
		WP_Mock::passthruFunction( 'esc_textarea' );
		$this->form_environment();
		$this->english_site();
		$raw  = json_encode(
			array(
				'source'    => 'http://site/products/%c3%a4/',
				'selection' => array(
					'q'    => 'SAJ with no match',
					'sort' => 'name',
				),
			)
		);
		$_GET = array( \Linker\Commerce\Contact\SelectionContext::FIELD => $raw );
		$html = ( new Form() )->render();
		$this->assertSame( 1, preg_match( '/data-linker-contact-draft-context="([a-f0-9]+)"/', $html, $context_attribute ) );
		$navigation_context = $context_attribute[1] ?? '';
		$this->assertStringContainsString( 'Include this selection with my message', $html );
		$this->assertStringContainsString( 'SAJ with no match', $html );
		$this->assertStringContainsString( ' checked /><span>', $html );
		$this->assertStringContainsString( 'required></textarea>', $html, 'Context never pre-fills the message.' );

		$store   = array();
		$session = \Mockery::mock( \WC_Session_Handler::class );
		$session->shouldReceive( 'has_session' )->andReturn( true );
		$session->shouldReceive( 'get_customer_id' )->andReturn( 'guest-fixture' );
		$session->shouldReceive( 'set' )->andReturnUsing(
			static function ( string $key, $value ) use ( &$store ): void {
				$store[ $key ] = $value;
			}
		);
		$session->shouldReceive( 'get' )->andReturnUsing(
			static function ( string $key ) use ( &$store ) {
				return $store[ $key ] ?? null;
			}
		);
		$session->shouldReceive( 'set_customer_session_cookie' )->twice()->with( true );
		WP_Mock::userFunction( 'WC', array( 'return' => (object) array( 'session' => $session ) ) );
		WP_Mock::userFunction( 'wc_load_cart' );
		$old_cookies                               = $_COOKIE;
		$_COOKIE['wp_woocommerce_session_fixture'] = 'native-presence';
		try {
			$post = array(
				'message'           => 'My unchanged question.',
				'intent'            => 'product',
				'linker_request_id' => 'original-logical-request',
				\Linker\Commerce\Contact\SelectionContext::FIELD => $raw,
				\Linker\Commerce\Contact\SelectionContext::INCLUDE_FIELD => '0',
				'linker_proof'      => 'not-recovered',
			);
			\Linker\Commerce\Protection\FormRecovery::save( 'contact', $post );
			$this->assertSame( 'original-logical-request', $store['linker_form_recovery_contact']['fields']['linker_request_id'] );
			$this->assertArrayNotHasKey( 'linker_proof', $store['linker_form_recovery_contact']['fields'] );
			$html = ( new Form() )->render();
			$this->assertStringContainsString( 'required>My unchanged question.</textarea>', $html );
			$this->assertStringContainsString( 'http://site/products/%c3%a4/', $html, 'Native percent-encoded canonical paths survive recovery.' );
			$this->assertStringContainsString( ' checked /><span>', $html );
			unset( $post[ \Linker\Commerce\Contact\SelectionContext::FIELD ] );
			\Linker\Commerce\Protection\FormRecovery::save( 'contact', $post );
			$html = ( new Form() )->render();
			$this->assertStringContainsString( 'required>My unchanged question.</textarea>', $html );
			$this->assertStringContainsString( 'This selection will not be sent.', $html );
			$this->assertStringContainsString( 'data-linker-contact-draft-context="' . $navigation_context . '"', $html, 'The native language URL keeps the public source identity after explicit exclusion.' );
			$this->assertStringContainsString( 'data-linker-contact-recovered="1"', $html );
			$this->assertStringNotContainsString( 'SAJ with no match', $html );
			$this->assertStringNotContainsString( 'name="' . \Linker\Commerce\Contact\SelectionContext::FIELD . '"', $html );
			$this->assertNull( $store['linker_form_recovery_contact'] );

		} finally {
			$_COOKIE = $old_cookies;
			$_GET    = array();
		}
	}

	/**
	 * The WordPress reads every render makes. The locale is registered first:
	 * WP_Mock answers with the first matching registration.
	 *
	 * @param string $locale The locale the page is rendered in.
	 */
	private function form_environment( string $locale = 'en_US' ): void {
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 5 ) );
		WP_Mock::userFunction( 'wp_json_encode', array( 'return' => static fn ( mixed $value ): string => (string) json_encode( $value ) ) );
		WP_Mock::userFunction( 'wp_get_session_token', array( 'return' => 'test-session' ) );
		WP_Mock::userFunction( 'wp_hash', array( 'return' => static fn ( string $value ): string => hash( 'sha256', $value ) ) );
		WP_Mock::userFunction( 'wp_enqueue_script', array( 'return' => null ) );
		WP_Mock::userFunction( 'plugins_url', array( 'return' => 'http://site/wp-content/plugins/linker-commerce/build/contact-language.js' ) );
		WP_Mock::userFunction( 'wp_create_nonce', array( 'return' => 'signed-time' ) );
		WP_Mock::userFunction( 'determine_locale', array( 'return' => $locale ) );
		WP_Mock::userFunction(
			'get_queried_object',
			array(
				'return' => new \WP_Post(
					(object) array(
						'ID'         => 28,
						'post_type'  => 'page',
						'post_title' => 'Contact',
					)
				),
			)
		);
		WP_Mock::userFunction(
			'get_permalink',
			array(
				'return' => static function ( $post = null ): string {
					$id = $post instanceof \WP_Post ? (int) $post->ID : (int) $post;
					if ( 41 === $id ) {
						return 'http://site/de/genie/';
					}
					return 60 === $id ? 'http://site/genie/' : 'http://site/contact/';
				},
			)
		);
		WP_Mock::userFunction( 'sanitize_key', array( 'return' => static fn ( string $key ): string => strtolower( preg_replace( '/[^a-z0-9_-]/i', '', $key ) ?? '' ) ) );
		WP_Mock::userFunction( 'wp_unslash', array( 'return' => static fn ( $value ) => $value ) );
	}

	/**
	 * The English site: no language layer answers, the Genie page is /genie/.
	 */
	private function english_site(): void {
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => false ) );
		WP_Mock::userFunction( 'home_url', array( 'return' => static fn ( string $path = '/' ): string => 'http://site' . $path ) );
		WP_Mock::userFunction(
			'get_page_by_path',
			array(
				'args'   => array( 'genie' ),
				'return' => new \WP_Post( (object) array( 'ID' => 60 ) ),
			)
		);
		$this->settings_environment();
	}

	/**
	 * The reads the side cards add: the team mailbox of the settings.
	 */
	private function settings_environment(): void {
		WP_Mock::userFunction( 'get_option', array( 'return' => '' ) );
		WP_Mock::userFunction( 'sanitize_email', array( 'return' => static fn ( string $email ): string => $email ) );
		WP_Mock::userFunction( 'admin_url', array( 'return' => 'http://site/wp-admin/admin-post.php' ) );
		WP_Mock::userFunction( 'wp_nonce_field', array( 'return' => '<input type="hidden" name="linker_contact_nonce" value="nonce" />' ) );
		WP_Mock::userFunction( 'get_privacy_policy_url', array( 'return' => 'http://site/privacy-policy/' ) );
	}
}
