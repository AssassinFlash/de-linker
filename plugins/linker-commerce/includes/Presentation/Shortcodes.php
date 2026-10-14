<?php
/**
 * Shortcodes that feed LiveCanvas templates with B2B data.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

use Linker\Commerce\Products\Faqs;
use Linker\Commerce\Registration\Approval;
use Linker\Commerce\Settings\Options;
use WC_Product;

/**
 * Price gating and the empty Proforma-request gate: the two shortcodes the
 * exported templates consume.
 */
final class Shortcodes {

	/**
	 * Sets up the shortcodes.
	 *
	 * @param LoginGate $gate     The empty Proforma-request page.
	 * @param Approval  $approval The account approval rule.
	 */
	public function __construct( private readonly LoginGate $gate, private readonly Approval $approval = new Approval() ) {}

	/**
	 * Registers the shortcodes.
	 */
	public function register(): void {
		add_shortcode( 'linker_price', array( $this, 'price' ) );
		add_shortcode( 'linker_checkout', array( $this, 'checkout' ) );
		add_shortcode( 'linker_draft_empty', array( $this, 'draft_empty' ) );
		add_shortcode( 'linker_faqs', array( $this, 'faqs' ) );
		add_shortcode( 'linker_contact_link', array( $this, 'contact_link' ) );
		add_shortcode( 'linker_contact_invitation', array( $this, 'contact_invitation' ) );
		// LiveCanvas's native condition tag. Both names stay true or false
		// together, so a template that lost one half still cannot print both.
		add_filter( 'lc_define_condition_linker_commerce_draft_empty', array( $this, 'draft_is_empty' ) );
		add_filter( 'lc_define_condition_linker_commerce_draft_filled', array( $this, 'draft_is_filled' ) );
	}

	/**
	 * The contact page in the page's language; every contact entry (the site
	 * chrome's, the product list's invitation) resolves its target here.
	 */
	public static function contact_page_url(): string {
		$page = get_page_by_path( 'contact' );
		$id   = $page instanceof \WP_Post ? (int) $page->ID : 0;
		if ( $id > 0 && function_exists( 'pll_get_post' ) && function_exists( 'pll_current_language' ) && 'de' === pll_current_language() ) {
			$twin = (int) pll_get_post( $id, 'de' );
			if ( $twin > 0 ) {
				$id = $twin;
			}
		}
		return $id > 0 ? (string) get_permalink( $id ) : home_url( '/contact/' );
	}

	/**
	 * The site chrome's contact entry: the contact page in the page's
	 * language, carrying the product on display as the request's subject.
	 * Placement selects the chrome's own class (header, mobile header,
	 * footer).
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function contact_link( $atts = array() ): string {
		$attributes = shortcode_atts(
			array(
				'placement' => 'header',
				'class'     => '',
			),
			(array) $atts
		);
		$classes    = '' !== trim( (string) $attributes['class'] )
			? trim( (string) $attributes['class'] )
			: ( 'mobile' === $attributes['placement'] ? 'tv-header-cta tv-mobile-cta' : 'tv-header-cta' );
		$url        = self::contact_page_url();
		if ( function_exists( 'is_product' ) && is_product() ) {
			$product = wc_get_product( (int) get_the_ID() );
			if ( $product instanceof WC_Product ) {
				$url = (string) add_query_arg(
					array(
						'intent'     => 'product',
						'kind'       => 'product',
						'title'      => rawurlencode( $product->get_name() ),
						'source_id'  => $product->get_id(),
						'product_id' => $product->get_id(),
						'source'     => $product->get_permalink(),
					),
					$url
				);
			}
		}
		return '<a class="' . esc_attr( $classes ) . '" href="' . esc_url( $url ) . '">' . esc_html__( 'Contact Linker', 'linker-commerce' ) . '</a>';
	}

	/**
	 * The designed contact band the marketing pages and the article template
	 * print as `[linker_contact_invitation surface="…"]`.
	 *
	 * The words are the live band's, read off the old live pages (utility
	 * solution, EPC, the EPC intake, services, article; EN and DE,
	 * 2026-10-12/13 captures). An unknown surface prints nothing: it must
	 * not borrow another surface's words. `compact` is the intake's own
	 * shape (no card, a rule above). Styles stay in WindPress
	 * (content/windpress/contact-invitation.css).
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function contact_invitation( $atts = array() ): string {
		$attributes = shortcode_atts(
			array(
				'surface' => '',
				'compact' => '',
			),
			(array) $atts,
			'linker_contact_invitation'
		);
		// Decode before sanitize_html_class. An unregistered tag is
		// wptexturized to &#8221; (current /services-support/ and
		// /solution/utility-storage/ HTML, 2026-10-14). A stored entity is
		// not a quote to shortcode_parse_atts, so the value arrives as
		// &#8221;services&#8221; and sanitizes to 8221services8221, which
		// matches no surface and prints no band. WordPress's own
		// shortcode_parse_atts / sanitize_html_class.
		$surface = html_entity_decode( (string) $attributes['surface'], ENT_QUOTES, 'UTF-8' );
		$surface = trim( $surface, "\"\'\xE2\x80\x9C\xE2\x80\x9D" );
		$surface = sanitize_html_class( $surface );
		$copy    = self::invitation_copy();
		if ( ! isset( $copy[ $surface ] ) ) {
			return '';
		}
		$row     = $copy[ $surface ];
		$intent  = self::invitation_intent( $surface );
		$email   = ( new Options() )->team_to();
		$context = $this->invitation_context( $intent );
		$url     = (string) add_query_arg(
			array(
				'intent'    => $intent,
				'kind'      => (string) $context['kind'],
				'title'     => (string) $context['title'],
				'source'    => (string) $context['url'],
				'source_id' => (int) $context['source_id'],
			),
			self::contact_page_url()
		);
		$classes = 'linker-contact-invitation linker-contact-' . $surface;
		if ( '' !== $attributes['compact'] ) {
			$classes .= ' linker-contact-compact';
		}

		$html  = '<section class="' . esc_attr( $classes ) . '">';
		$html .= '<div>';
		if ( '' !== $row['eyebrow'] ) {
			$html .= '<span class="linker-contact-eyebrow">' . esc_html( $row['eyebrow'] ) . '</span>';
		}
		$html .= '<h2>' . esc_html( $row['heading'] ) . '</h2>';
		$html .= '<p>' . esc_html( $row['note'] ) . '</p>';
		$html .= '</div>';
		$html .= '<div class="linker-contact-invitation-actions">';
		$html .= '<a class="linker-contact-primary" href="' . esc_url( $url ) . '" data-linker-contact="' . esc_attr( (string) wp_json_encode( $context ) ) . '">' . esc_html( $row['button'] ) . '</a>';
		$html .= '<a class="linker-contact-email" href="mailto:' . esc_attr( $email ) . '">' . esc_html( $email ) . '</a>';
		$html .= '</div>';
		return $html . '</section>';
	}

	/**
	 * Which request the band opens. The article band is about the product
	 * the piece discusses; the others are about the project on the page.
	 *
	 * @param string $surface A known surface.
	 */
	private static function invitation_intent( string $surface ): string {
		return 'article' === $surface ? 'product' : 'project';
	}

	/**
	 * The page the band sits on, so the request keeps that page as context.
	 *
	 * @param string $intent `project` or `product`.
	 * @return array{kind: string, title: string, url: string, source_id: int, intent: string}
	 */
	private function invitation_context( string $intent ): array {
		$id    = function_exists( 'get_queried_object_id' ) ? (int) get_queried_object_id() : 0;
		$title = $id > 0 ? wp_strip_all_tags( (string) get_the_title( $id ) ) : '';
		$url   = $id > 0 ? (string) get_permalink( $id ) : '';
		$kind  = function_exists( 'is_singular' ) && is_singular( 'post' ) ? 'article' : 'page';
		if ( '' === $title ) {
			$title = 'Linker';
		}
		if ( '' === $url ) {
			$url = home_url( '/' );
		}
		return array(
			'kind'      => $kind,
			'title'     => $title,
			'url'       => $url,
			'source_id' => $id,
			'intent'    => $intent,
		);
	}

	/**
	 * The live band's words, in the page's language.
	 *
	 * German is the page's own wording (Polylang `de`), not a translation of
	 * the English string. The intake band has no eyebrow.
	 *
	 * @return array<string, array{eyebrow: string, heading: string, note: string, button: string}>
	 */
	private static function invitation_copy(): array {
		if ( function_exists( 'pll_current_language' ) && 'de' === pll_current_language() ) {
			return array(
				'solution'   => array(
					'eyebrow' => __( 'LÖSUNGEN FÜR GROSSSPEICHER', 'linker-commerce' ),
					'heading' => __( 'Ihr Großspeicherprojekt als Gesamtlösung gedacht.', 'linker-commerce' ),
					'note'    => __( 'Gemeinsam mit Projektentwicklern und EPC-Teams richten wir Batteriespeicher an Energiezielen, Standort und Einbindung aus. Dabei verbinden wir die Systemauswahl mit einer umsetzbaren Planung für die Lieferung.', 'linker-commerce' ),
					'button'  => __( 'Ihr Projekt gemeinsam entwickeln', 'linker-commerce' ),
				),
				'epc'        => array(
					'eyebrow' => __( 'KONTAKT ZU LINKER', 'linker-commerce' ),
					'heading' => __( 'Das Projekt vor dem vollständigen Briefing besprechen.', 'linker-commerce' ),
					'note'    => __( 'Ihre Frage enthält den Bezug zu dieser Seite. Sie können ihn vor dem Senden entfernen.', 'linker-commerce' ),
					'button'  => __( 'EPC-Anforderung besprechen', 'linker-commerce' ),
				),
				'services'   => array(
					'eyebrow' => __( 'TECHNISCHE ZUSAMMENARBEIT', 'linker-commerce' ),
					'heading' => __( 'Ein technischer Partner in jeder Projektphase.', 'linker-commerce' ),
					'note'    => __( 'Unser Team arbeitet mit Ihrem Team an Systementscheidungen, Installationsfragen und der Inbetriebnahme. Auch nach der Lieferung bleiben wir bei technischen Fragen an Ihrer Seite.', 'linker-commerce' ),
					'button'  => __( 'Mit unserem Technikteam sprechen', 'linker-commerce' ),
				),
				'article'    => array(
					'eyebrow' => __( 'IHR PROJEKT IN DER PRAXIS', 'linker-commerce' ),
					'heading' => __( 'Was kann die passende Speicherlösung an Ihrem Standort leisten?', 'linker-commerce' ),
					'note'    => __( 'Gemeinsam betrachten wir, wie ein Hybrid- oder AC-gekoppelter Speicher zu Ihrer Anlage, Ihrem Energieverbrauch und Ihren Zielen passt.', 'linker-commerce' ),
					'button'  => __( 'Ihre Speicheroptionen besprechen', 'linker-commerce' ),
				),
				'epc-intake' => array(
					'eyebrow' => '',
					'heading' => __( 'Eine frühe Frage reicht aus.', 'linker-commerce' ),
					'note'    => __( 'Teilen Sie mit, was bereits feststeht. Projektstandort und Zeitraum sind im Kurzformular optional.', 'linker-commerce' ),
					'button'  => __( 'Projekt besprechen', 'linker-commerce' ),
				),
			);
		}
		return array(
			'solution'   => array(
				'eyebrow' => __( 'UTILITY-SCALE SOLUTIONS', 'linker-commerce' ),
				'heading' => __( 'A storage solution built around the whole project.', 'linker-commerce' ),
				'note'    => __( 'We work alongside developers and EPC teams to shape battery storage around the project’s energy goals, site conditions and integration needs. Together, we connect system choices with a practical plan for delivery.', 'linker-commerce' ),
				'button'  => __( 'Explore your project with us', 'linker-commerce' ),
			),
			'epc'        => array(
				'eyebrow' => __( 'CONTACT LINKER', 'linker-commerce' ),
				'heading' => __( 'Discuss the project before preparing the full brief.', 'linker-commerce' ),
				'note'    => __( 'Your question includes this page as context. You can remove it before sending.', 'linker-commerce' ),
				'button'  => __( 'Discuss an EPC requirement', 'linker-commerce' ),
			),
			'services'   => array(
				'eyebrow' => __( 'TECHNICAL PARTNERSHIP', 'linker-commerce' ),
				'heading' => __( 'A technical partner, wherever your project stands.', 'linker-commerce' ),
				'note'    => __( 'Our team works with yours on system choices, installation questions and commissioning, and stays involved when support is needed after delivery.', 'linker-commerce' ),
				'button'  => __( 'Talk to our technical team', 'linker-commerce' ),
			),
			'article'    => array(
				'eyebrow' => __( 'YOUR PROJECT, IN PRACTICE', 'linker-commerce' ),
				'heading' => __( 'What could the right storage solution do for your site?', 'linker-commerce' ),
				'note'    => __( 'We’ll explore how hybrid or AC-coupled storage could work with your installation, your energy use and the outcome you want to achieve.', 'linker-commerce' ),
				'button'  => __( 'Talk through your storage options', 'linker-commerce' ),
			),
			'epc-intake' => array(
				'eyebrow' => '',
				'heading' => __( 'An early question is enough.', 'linker-commerce' ),
				'note'    => __( 'Share what you already know. Project location and timing are optional in the short form.', 'linker-commerce' ),
				'button'  => __( 'Discuss your project', 'linker-commerce' ),
			),
		);
	}

	/**
	 * The current product's gated price HTML.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function price( $atts = array() ): string {
		unset( $atts );
		$product = $GLOBALS['product'] ?? null;
		if ( ! $product instanceof WC_Product ) {
			return '';
		}
		return '<div class="linker-price font-semibold text-[#0c7f73]">' . $product->get_price_html() . '</div>';
	}

	/**
	 * The Proforma request: the gate when the draft is empty or the account
	 * may not send, otherwise WooCommerce's checkout.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function checkout( $atts = array() ): string {
		unset( $atts );
		$user_id = get_current_user_id();
		if ( $this->is_empty_request() || ( $user_id > 0 && ! $this->approval->sees_prices( $user_id ) ) ) {
			return $this->gate->html();
		}
		return do_shortcode( '[woocommerce_checkout]' );
	}

		/**
		 * The empty solution draft: icon, title, the review note, and the two
		 * ways back that still have a page. The LiveCanvas cart template
		 * prints this when the draft is empty; a filled draft keeps
		 * WooCommerce's cart.
		 *
		 * @param array<string, string>|string $atts Shortcode attributes.
		 */
	public function draft_empty( $atts = array() ): string {
		unset( $atts );
		return $this->empty_draft_html();
	}

	/**
	 * Whether the solution draft has no lines. A confirmation or pay page is
	 * not an empty draft: those pages share the cart's template family only
	 * by accident, and the condition must not hide a receipt.
	 */
	public function draft_is_empty(): bool {
		return $this->is_empty_request();
	}

	/**
	 * The other half of the cart template's condition. Never true together
	 * with draft_is_empty().
	 */
	public function draft_is_filled(): bool {
		return ! $this->draft_is_empty();
	}

		/**
		 * Markup of the empty solution draft.
		 *
		 * The live empty cart had three actions. The middle one opened a
		 * batch item-number import the owner later ruled out (surface
		 * inventory, 2026-10-11: not built). This page keeps the two
		 * actions that still have a page: browse products, and sign in.
		 * The heading names the solution draft. Classes only; the look
		 * lives in the storefront volume.
		 */
	private function empty_draft_html(): string {
		$products = (string) get_permalink( wc_get_page_id( 'shop' ) );
		$account  = (string) wc_get_page_permalink( 'myaccount' );
		$icon     = '<svg class="sf-cart-empty__icon" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="9" cy="20" r="1"/><circle cx="18" cy="20" r="1"/><path d="M3 4h2l2.2 11.2a1 1 0 0 0 1 .8h9.6a1 1 0 0 0 1-.8L21 8H7"/></svg>';
		return sprintf(
			'<section class="sf-cart-empty" aria-label="%1$s">%2$s<h1>%3$s</h1><p>%4$s</p><div class="sf-cart-empty__actions"><a class="sf-cart-btn" href="%5$s">%6$s</a><a class="sf-cart-btn sf-cart-btn--ghost" href="%7$s">%8$s</a></div></section>',
			esc_attr__( 'Empty solution draft', 'linker-commerce' ),
			$icon,
			esc_html__( 'Your solution draft is empty.', 'linker-commerce' ),
			esc_html__( 'You can browse the products and match an item-number list now. Adding to the solution draft is possible only after your account has been reviewed.', 'linker-commerce' ),
			esc_url( $products ),
			esc_html__( 'Browse products', 'linker-commerce' ),
			esc_url( $account ),
			esc_html__( 'Sign in or register', 'linker-commerce' )
		);
	}

	/**
	 * Whether this is an empty Proforma request (not a confirmation or pay page).
	 */
	private function is_empty_request(): bool {
		if ( is_wc_endpoint_url( 'order-received' ) || is_wc_endpoint_url( 'order-pay' ) ) {
			return false;
		}
		return WC()->cart->is_empty();
	}

	/**
	 * The current product's FAQ rows from `_linker_faqs` (docs/specs/15-faq.md),
	 * as the live page's accordion rows. German requests (Polylang `de`) use
	 * question_de / answer_de. The section frame and its title live in the
	 * template; this carries the rows.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function faqs( $atts = array() ): string {
		unset( $atts );
		$product = $GLOBALS['product'] ?? null;
		if ( ! $product instanceof WC_Product ) {
			$product = wc_get_product( (int) get_the_ID() );
		}
		if ( ! $product instanceof WC_Product ) {
			return '';
		}
		$items = Faqs::of( $product->get_id() );
		if ( array() === $items ) {
			return '';
		}
		$german = function_exists( 'pll_current_language' ) && 'de' === pll_current_language();
		$html   = '';
		foreach ( $items as $item ) {
			$question = $german && '' !== $item['question_de'] ? $item['question_de'] : $item['question'];
			$answer   = $german && '' !== $item['answer_de'] ? $item['answer_de'] : $item['answer'];
			$html    .= '<details class="pdp-disclose"><summary>' . esc_html( $question ) . ProductShortcodes::icon( 'chevron' ) . '</summary>'
				. '<div class="pdp-disclose-body pdp-reading">' . wp_kses_post( wpautop( $answer ) ) . '</div></details>';
		}
		return $html;
	}
}
