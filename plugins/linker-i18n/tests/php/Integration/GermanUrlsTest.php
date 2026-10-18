<?php
/**
 * German addresses through the public CLI and HTTP interfaces.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Integration;

// phpcs:disable WordPress.WP.AlternativeFunctions, WordPress.PHP.DiscouragedPHPFunctions.system_calls_proc_open -- Integration driver runs outside WordPress.

/**
 * Exercises the owner-approved route migration on a snapshot instance.
 *
 * @coversNothing
 */
final class GermanUrlsTest extends SiteTestCase {

	/**
	 * Migration bookkeeping belongs to the test, never to its next run.
	 *
	 * @var mixed
	 */
	private mixed $migration_state = null;

	/** The journal's collection metadata names the document in its own language. */
	public function test_journal_collection_metadata_uses_its_own_language_url(): void {
		foreach ( array( '/blog/', '/de/blog/' ) as $path ) {
			$page = self::get( $path );
			self::assertSame( 200, $page['status'] );
			preg_match_all( '#<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>#s', $page['body'], $scripts );
			$collections = array();
			foreach ( $scripts[1] as $script ) {
				$data = json_decode( $script, true );
				if ( is_array( $data ) && in_array( 'CollectionPage', (array) ( $data['@type'] ?? array() ), true ) ) {
					$collections[] = $data['url'] ?? '';
				}
			}
			self::assertSame( array( self::$site . $path ), $collections );
		}
	}

	/** The topic navigation identifies the current topic through native category links. */
	public function test_journal_topics_identify_the_current_category_in_each_language(): void {
		$applied = false;
		try {
			self::wp( array( 'linker-i18n', 'german-urls', '--apply' ) );
			$applied = true;
			foreach ( array(
				'/category/system-design/'       => 'Journal topics',
				'/de/kategorie/systemauslegung/' => 'Themen im Journal',
			) as $path => $label ) {
				$page = self::get( $path );
				self::assertSame( 200, $page['status'] );
				$document = new \DOMDocument();
				$previous = libxml_use_internal_errors( true );
				try {
					self::assertTrue( $document->loadHTML( $page['body'], LIBXML_NONET ) );
				} finally {
					libxml_clear_errors();
					libxml_use_internal_errors( $previous );
				}
				$xpath = new \DOMXPath( $document );
				$nav   = $xpath->query( '//nav[contains(@class,"tv-blog-cat-nav-inner")]' );
				self::assertInstanceOf( \DOMNodeList::class, $nav );
				self::assertSame( 1, $nav->length, 'Topics must be a labelled navigation landmark.' );
				$navigation = $nav->item( 0 );
				self::assertInstanceOf( \DOMElement::class, $navigation );
				self::assertSame( $label, $navigation->getAttribute( 'aria-label' ) );
				$current = $xpath->query( './/a[@aria-current="page"]', $navigation );
				self::assertInstanceOf( \DOMNodeList::class, $current );
				self::assertSame( 1, $current->length, 'Only the current topic is selected.' );
				$link = $current->item( 0 );
				self::assertInstanceOf( \DOMElement::class, $link );
				self::assertSame( self::$site . $path, $link->getAttribute( 'href' ) );
				// phpcs:ignore WordPress.NamingConventions.ValidVariableName.UsedPropertyNotSnakeCase -- Native DOM API property.
				self::assertStringNotContainsString( 'article', strtolower( $navigation->textContent ) );
			}
		} finally {
			if ( $applied ) {
				self::wp( array( 'linker-i18n', 'german-urls', '--rollback', '--apply' ) );
			}
		}
	}

	/** SEOPress filters receive complete tags; endpoint URLs must remain inside them. */
	public function test_german_endpoint_metadata_is_valid_html_not_visible_url_text(): void {
		$applied = false;
		try {
			self::wp( array( 'linker-i18n', 'german-urls', '--apply' ) );
			$applied = true;
			foreach ( array( '/de/mein-konto/registrieren/', '/de/mein-konto/passwort-zuruecksetzen/' ) as $path ) {
				$page = self::get( $path );
				self::assertSame( 200, $page['status'] );
				$url = preg_quote( self::$site . $path, '#' );
				self::assertMatchesRegularExpression( '#<link rel="canonical" href="' . $url . '"\s*/?>#', $page['body'], $path );
				self::assertMatchesRegularExpression( '#<meta property="og:url" content="' . $url . '"\s*/?>#', $page['body'], $path );
				self::assertStringNotContainsString( "\n" . self::$site . $path . "\n", $page['body'], 'Head metadata cannot become visible body text.' );
			}
		} finally {
			if ( $applied ) {
				self::wp( array( 'linker-i18n', 'german-urls', '--rollback', '--apply' ) );
			}
		}
	}

	/** A first deployment must not overwrite independently edited German names or SEO copy. */
	public function test_first_apply_rejects_unreviewed_titles_before_writing(): void {
		$fixture = self::php( '$en = get_page_by_path( "faq-download" ); $id = (int) pll_get_post( $en->ID, "de" ); $term = get_term_by( "slug", "ems-monitoring", "product_cat" ); $term_id = (int) pll_get_term( $term->term_id, "de" ); delete_option( "linker_i18n_german_urls_backup" ); return array( "id" => $id, "title" => get_post_field( "post_title", $id ), "seo" => get_post_meta( $id, "_seopress_titles_title", true ), "seo_exists" => metadata_exists( "post", $id, "_seopress_titles_title" ), "term" => $term_id, "name" => get_term( $term_id )->name );' );
		$applied = false;
		try {
			foreach ( array( 'post_title', 'meta:_seopress_titles_title', 'name' ) as $field ) {
				self::php( 'if ( "name" === $input["field"] ) { wp_update_term( $input["term"], "product_cat", array( "name" => "Manuell benannte Kategorie" ) ); } elseif ( "post_title" === $input["field"] ) { wp_update_post( array( "ID" => $input["id"], "post_title" => "Manuell angepasster Seitentitel" ) ); } else { update_post_meta( $input["id"], "_seopress_titles_title", "Manuell verfasster SEO-Titel | Linker" ); }', $fixture + array( 'field' => $field ) );
				foreach ( array( '--dry-run', '--apply' ) as $flag ) {
					$result = self::command( array( $flag ) );
					self::assertNotSame( 0, $result['status'], 'First-run drift must be rejected: ' . $field . ' ' . $flag );
					self::assertStringContainsString( 'Unexpected German field', $result['output'] );
					self::assertNull( self::php( 'return get_option( "linker_i18n_german_urls_backup", null );' ) );
					self::assertSame( 200, self::get( '/de/warenkorb/' )['status'], 'No earlier field was applied.' );
				}
				self::php( 'wp_update_post( array( "ID" => $input["id"], "post_title" => $input["title"] ) ); if ( $input["seo_exists"] ) { update_post_meta( $input["id"], "_seopress_titles_title", $input["seo"] ); } else { delete_post_meta( $input["id"], "_seopress_titles_title" ); } wp_update_term( $input["term"], "product_cat", array( "name" => $input["name"] ) );', $fixture );
			}
			// A reviewed new post title with the reviewed old SEO value is resumable.
			self::php( 'wp_update_post( array( "ID" => $input["id"], "post_title" => "FAQ & Dokumente" ) );', $fixture );
			self::wp( array( 'linker-i18n', 'german-urls', '--apply' ) );
			$applied = true;
			self::assertSame( 0, self::command( array( '--verify' ) )['status'] );
			preg_match( '#<title>(.*?)</title>#s', self::get( '/de/faq-dokumente/' )['body'], $match );
			self::assertSame( 'FAQ & Dokumente | Linker', html_entity_decode( $match[1] ?? '', ENT_QUOTES | ENT_HTML5, 'UTF-8' ) );
		} finally {
			if ( $applied ) {
				self::wp( array( 'linker-i18n', 'german-urls', '--rollback', '--apply' ) );
			}
			self::php( 'wp_update_post( array( "ID" => $input["id"], "post_title" => $input["title"] ) ); if ( $input["seo_exists"] ) { update_post_meta( $input["id"], "_seopress_titles_title", $input["seo"] ); } else { delete_post_meta( $input["id"], "_seopress_titles_title" ); } wp_update_term( $input["term"], "product_cat", array( "name" => $input["name"] ) );', $fixture );
		}
	}

	/** Real owned inquiries and a native logout nonce survive the translated endpoints. */
	public function test_owned_inquiry_details_and_native_logout_keep_their_identity(): void {
		$fixture = self::php( '$id = wp_insert_user( array( "user_login" => "i254-detail-" . wp_generate_uuid4(), "user_pass" => wp_generate_password(), "user_email" => "i254-detail@example.test", "role" => "customer" ) ); if ( is_wp_error( $id ) ) { throw new RuntimeException( $id->get_error_message() ); } update_user_meta( $id, Linker\\Commerce\\Registration\\Approval::STATUS_META, "approved" ); $orders = array(); for ( $n = 0; $n < 2; ++$n ) { $order = new WC_Order(); $order->set_customer_id( $id ); $order->set_status( "inquiry-received" ); $order->update_meta_data( "_linker_locale", "de_DE_formal" ); $orders[] = $order->save(); } $cookie = wp_generate_auth_cookie( $id, time() + 600, "logged_in" ); $_COOKIE[LOGGED_IN_COOKIE] = $cookie; wp_set_current_user( $id ); return array( "id" => $id, "orders" => $orders, "cookie" => LOGGED_IN_COOKIE . "=" . $cookie, "nonce" => wp_create_nonce( "customer-logout" ) );' );
		$applied = false;
		try {
			self::wp( array( 'linker-i18n', 'german-urls', '--apply' ) );
			$applied = true;
			$headers = array( 'Cookie' => $fixture['cookie'] );
			$proof   = array();
			$titles  = array();
			foreach ( $fixture['orders'] as $id ) {
				$old   = '/de/mein-konto/inquiry/' . $id . '/';
				$new   = '/de/mein-konto/anfrage/' . $id . '/';
				$alias = self::get( $old, $headers );
				self::assertSame( 301, $alias['status'] );
				self::assertSame( self::$site . $new, $alias['headers']['location'] ?? '' );
				$page = self::get( $new, $headers );
				self::assertSame( 200, $page['status'] );
				preg_match( '#<title>(.*?)</title>#s', $page['body'], $match );
				$title = html_entity_decode( $match[1] ?? '', ENT_QUOTES | ENT_HTML5, 'UTF-8' );
				self::assertSame( 'Anfrage ' . $id . ' | Linker', $title );
				self::assertNotContains( $title, $titles );
				$titles[] = $title;
				$proof[]  = array(
					'old'   => $old,
					'new'   => $new,
					'first' => $alias['status'],
					'final' => $page['status'],
					'title' => $title,
				);
			}
			// Native Woo endpoint nonce for this owned session; the header keeps WordPress's one-click logout.
			$logout = '/de/mein-konto/abmelden/?_wpnonce=' . $fixture['nonce'];
			$old    = self::get( str_replace( '/abmelden/', '/customer-logout/', $logout ), $headers );
			self::assertSame( 301, $old['status'] );
			self::assertSame( self::$site . $logout, $old['headers']['location'] ?? '' );
			$transition = self::get( $logout, $headers );
			self::assertSame( 302, $transition['status'] );
			self::assertStringStartsWith( self::$site . '/de/mein-konto/', $transition['headers']['location'] ?? '' );
			$guest = self::get( '/de/mein-konto/', $headers );
			self::assertStringContainsString( '<title>Beim Partnerkonto anmelden | Linker</title>', $guest['body'], 'The original session is invalid after native logout.' );
			$proof[] = array(
				'old'        => '/de/mein-konto/customer-logout/?_wpnonce=LOCAL_NONCE',
				'new'        => '/de/mein-konto/abmelden/?_wpnonce=LOCAL_NONCE',
				'first'      => $old['status'],
				'transition' => $transition['status'],
				'final'      => $guest['status'],
			);
			self::evidence( 'functional-http.json', (string) json_encode( $proof, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) );
		} finally {
			if ( $applied ) {
				self::wp( array( 'linker-i18n', 'german-urls', '--rollback', '--apply' ) ); }
			self::php( 'foreach ( $input["orders"] as $id ) { wc_get_order( $id )->delete( true ); } require_once ABSPATH . "wp-admin/includes/user.php"; wp_delete_user( $input["id"] );', $fixture );
		}
	}

	/** Native paging and language alternates keep both the page number and language. */
	public function test_paginated_blog_and_category_addresses_have_german_paths_and_alternates(): void {
		$per_page = self::php( '$old = get_option( "posts_per_page" ); update_option( "posts_per_page", 1 ); return $old;' );
		$applied  = false;
		try {
			self::wp( array( 'linker-i18n', 'german-urls', '--apply' ) );
			$applied = true;
			foreach ( array(
				'/de/blog/page/2/'                     => array( '/de/blog/seite/2/', '/blog/page/2/' ),
				'/de/category/system-design/page/2/'   => array( '/de/kategorie/systemauslegung/seite/2/', '/category/system-design/page/2/' ),
				'/de/category/systemauslegung/page/2/' => array( '/de/kategorie/systemauslegung/seite/2/', '/category/system-design/page/2/' ),
			) as $old => $expected ) {
				$legacy = self::get( $old );
				self::assertSame( 301, $legacy['status'] );
				self::assertSame( self::$site . $expected[0], $legacy['headers']['location'] ?? '' );
				$page = self::get( $expected[0] );
				self::assertSame( 200, $page['status'], $expected[0] );
				preg_match( '#<title>(.*?)</title>#s', $page['body'], $title );
				self::assertStringContainsString( 'Seite 2', html_entity_decode( $title[1] ?? '', ENT_QUOTES | ENT_HTML5, 'UTF-8' ) );
				// Polylang deliberately omits hreflang on paged archives; its switcher must still retain the page.
				self::assertSame( array(), self::hreflangs( $page['body'] ) );
				self::assertStringContainsString( 'href="' . self::$site . $expected[1] . '"', $page['body'], 'The language switch retains page 2.' );
				self::assertStringNotContainsString( '/seite/2/page/', $page['body'] );
				self::assertStringContainsString( 'href="' . self::$site . str_replace( '/seite/2/', '/', $expected[0] ) . '"', $page['body'] );
				if ( '/de/blog/page/2/' === $old ) {
					self::assertStringContainsString( '/de/blog/seite/3/', $page['body'] );
				}
				self::assertSame( 200, self::get( $expected[1] )['status'] );
			}
		} finally {
			if ( $applied ) {
				self::wp( array( 'linker-i18n', 'german-urls', '--rollback', '--apply' ) ); }
			self::php( 'update_option( "posts_per_page", $input["value"] );', array( 'value' => $per_page ) );
		}
	}

	/** The original bootstrap entry cannot overwrite the newer German data. */
	public function test_original_bootstrap_is_retired_after_the_german_url_migration(): void {
		$applied = false;
		try {
			self::wp( array( 'linker-i18n', 'german-urls', '--apply' ) );
			$applied = true;
			foreach ( array( array( 'plan' ), array( 'apply', '--write' ) ) as $mode ) {
				$process = proc_open(
					array_merge( array( 'python3', dirname( __DIR__, 5 ) . '/tools/migrate/9-i18n.py', '--wp', (string) getenv( 'LINKER_I18N_WP' ), '--user', '1' ), $mode ),
					array(
						1 => array( 'pipe', 'w' ),
						2 => array( 'pipe', 'w' ),
					),
					$pipes
				);
				self::assertIsResource( $process );
				$output = stream_get_contents( $pipes[1] ) . stream_get_contents( $pipes[2] );
				fclose( $pipes[1] );
				fclose( $pipes[2] );
				self::assertSame( 0, proc_close( $process ), $output );
				self::assertStringContainsString( 'bootstrap import retired', $output );
			}
			self::assertSame( 0, self::command( array( '--verify' ) )['status'] );
			self::assertSame( 200, self::get( '/de/faq-dokumente/' )['status'] );
			self::assertSame( 200, self::get( '/de/kategorie/systemauslegung/' )['status'] );
		} finally {
			if ( $applied ) {
				self::wp( array( 'linker-i18n', 'german-urls', '--rollback', '--apply' ) ); }
		}
	}

	/** A stale autoloaded rules cache cannot hide a deployed German endpoint. */
	public function test_repeat_apply_repairs_a_stale_native_rewrite_cache(): void {
		$old_rules = self::php( 'return get_option( "rewrite_rules" );' );
		$applied   = false;
		try {
			self::wp( array( 'linker-i18n', 'german-urls', '--apply' ) );
			$applied = true;
			self::php( '$all = wp_load_alloptions(); $all["rewrite_rules"] = maybe_serialize( $input["rules"] ); wp_cache_set( "alloptions", $all, "options" );', array( 'rules' => $old_rules ) );
			self::assertSame( 404, self::get( '/de/mein-konto/registrieren/' )['status'], 'Reproduce the stale runtime cache observed during acceptance.' );
			$verified = self::command( array( '--verify' ) );
			self::assertNotSame( 0, $verified['status'] );
			self::assertStringContainsString( 'German rewrite rule missing', $verified['output'] );
			self::assertStringContainsString( '0 changes', self::wp( array( 'linker-i18n', 'german-urls', '--apply' ) ) );
			self::assertSame( 200, self::get( '/de/mein-konto/registrieren/' )['status'] );
			self::assertSame( 0, self::command( array( '--verify' ) )['status'] );
		} finally {
			if ( $applied ) {
				self::wp( array( 'linker-i18n', 'german-urls', '--rollback', '--apply' ) ); }
		}
	}

	/**
	 * Saves optional local-only delivery evidence requested by the acceptance run.
	 *
	 * @param string $name Evidence filename.
	 * @param string $contents Public fixture output; no real recipients or credentials.
	 */
	private static function evidence( string $name, string $contents ): void {
		$directory = getenv( 'LINKER_254_EVIDENCE_DIR' );
		if ( is_string( $directory ) && '' !== $directory ) {
			self::assertDirectoryExists( $directory );
			file_put_contents( $directory . '/' . $name, $contents );
		}
	}

	/** A real frontend password request queues German mail and its key still opens the native form. */
	public function test_frontend_password_mail_and_valid_reset_key_follow_the_new_address(): void {
		$fixture = self::php( '$saved = get_option( "linker_commerce_mail_sends", null ); update_option( "linker_commerce_mail_sends", array_fill( 0, Linker\Commerce\Mail\Throttle::PER_DAY, time() ) ); $id = wp_insert_user( array( "user_login" => "i254-front-" . wp_generate_uuid4(), "user_pass" => wp_generate_password(), "user_email" => "tester@example.test", "role" => "customer", "locale" => "de_DE_formal" ) ); if ( is_wp_error( $id ) ) { throw new RuntimeException( $id->get_error_message() ); } return array( "id" => $id, "sends" => $saved, "jobs" => get_posts( array( "post_type" => "linker_mail_job", "post_status" => "any", "numberposts" => -1, "fields" => "ids" ) ) );' );
		$applied = false;
		try {
			self::wp( array( 'linker-i18n', 'german-urls', '--apply' ) );
			$applied   = true;
			$form      = self::get( '/de/mein-konto/passwort-zuruecksetzen/' );
			$nonce_tag = self::tag( $form['body'], 'input', 'woocommerce-lost-password-nonce' );
			self::assertNotNull( $nonce_tag );
			preg_match( '/value="([^"]+)"/', $nonce_tag, $nonce );
			$sent = self::request(
				'POST',
				'/de/mein-konto/passwort-zuruecksetzen/',
				array( 'Content-Type' => 'application/x-www-form-urlencoded' ),
				http_build_query(
					array(
						'user_login'                      => 'tester@example.test',
						'wc_reset_password'               => 'true',
						'woocommerce-lost-password-nonce' => $nonce[1] ?? '',
					)
				)
			);
			self::assertSame( 302, $sent['status'] );
			self::assertStringContainsString( '/de/mein-konto/passwort-zuruecksetzen/', $sent['headers']['location'] ?? '' );
			$messages = self::php( '$ids = array_diff( get_posts( array( "post_type" => "linker_mail_job", "post_status" => "any", "numberposts" => -1, "fields" => "ids" ) ), $input["jobs"] ); return array_values( array_map( static fn( $id ) => json_decode( get_post_meta( $id, "_linker_mail_message", true ), true ), $ids ) );', $fixture );
			self::assertCount( 1, $messages );
			self::evidence( 'frontend-password-queue.json', (string) preg_replace( '/key=[^&"\s]+/', 'key=LOCAL_FIXTURE_KEY', (string) json_encode( $messages, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) ) );
			preg_match( '#href="([^"]+/de/mein-konto/passwort-zuruecksetzen/\?key=[^"]+)"#', $messages[0]['body'], $match );
			self::assertNotEmpty( $match[1] ?? '', 'Native mail uses the final German reset address.' );
			$url  = html_entity_decode( $match[1], ENT_QUOTES | ENT_HTML5, 'UTF-8' );
			$path = substr( $url, strlen( self::$site ) );
			$old  = self::get( str_replace( '/passwort-zuruecksetzen/', '/lost-password/', $path ) );
			self::assertSame( 301, $old['status'] );
			self::assertSame( $url, $old['headers']['location'] ?? '' );
			$reset = self::get( $path );
			self::assertSame( 302, $reset['status'], 'Woo protects the key in its native reset cookie.' );
			$cookie = explode( ';', $reset['headers']['set-cookie'] ?? '' )[0];
			$target = substr( $reset['headers']['location'] ?? '', strlen( self::$site ) );
			$page   = self::get( $target, array( 'Cookie' => $cookie ) );
			self::assertSame( 200, $page['status'] );
			self::assertStringContainsString( 'id="password_1"', $page['body'], 'The original key reaches the new-password form.' );
		} finally {
			if ( $applied ) {
				self::wp( array( 'linker-i18n', 'german-urls', '--rollback', '--apply' ) ); }
			self::php( '$jobs = array_diff( get_posts( array( "post_type" => "linker_mail_job", "post_status" => "any", "numberposts" => -1, "fields" => "ids" ) ), $input["jobs"] ); foreach ( $jobs as $job ) { foreach ( as_get_scheduled_actions( array( "hook" => "linker_commerce_mail_attempt", "args" => array( $job ), "group" => "linker-commerce", "per_page" => -1 ), "ids" ) as $action ) { ActionScheduler::store()->delete_action( $action ); } wp_delete_post( $job, true ); } require_once ABSPATH . "wp-admin/includes/user.php"; wp_delete_user( $input["id"] ); if ( null === $input["sends"] ) { delete_option( "linker_commerce_mail_sends" ); } else { update_option( "linker_commerce_mail_sends", $input["sends"] ); }', $fixture );
		}
	}

	/** A reused historical slug stops rollback before any original is restored. */
	public function test_rollback_preflights_occupied_original_addresses(): void {
		$blocker = 0;
		try {
			self::wp( array( 'linker-i18n', 'german-urls', '--apply' ) );
			$blocker = self::php( '$id = wp_insert_post( array( "post_type" => "page", "post_status" => "publish", "post_name" => "i254-blocker", "post_title" => "Adressprüfung" ) ); pll_set_post_language( $id, "de" ); wp_update_post( array( "ID" => $id, "post_name" => "faq-download" ) ); return $id;' );
			foreach ( array( '--dry-run', '--apply' ) as $flag ) {
				$result = self::command( array( '--rollback', $flag ) );
				self::assertNotSame( 0, $result['status'], 'A reused original must be a conflict.' );
				self::assertStringContainsString( 'Target slug occupied', $result['output'] );
			}
			self::assertSame( 200, self::get( '/de/loesungsentwurf/' )['status'] );
		} finally {
			if ( $blocker > 0 ) {
				self::php( 'wp_delete_post( $input["id"], true );', array( 'id' => $blocker ) ); }
			self::wp( array( 'linker-i18n', 'german-urls', '--rollback', '--apply' ) );
		}
	}

	/** Native Woo password mail also follows the stored recipient language in cron. */
	public function test_native_password_email_uses_german_links_in_background_context(): void {
		$applied = false;
		try {
			self::wp( array( 'linker-i18n', 'german-urls', '--apply' ) );
			$applied = true;
			$result  = self::php(
				'$saved = get_option( "linker_commerce_mail_sends", null ); $before = get_posts( array( "post_type" => "linker_mail_job", "post_status" => "any", "numberposts" => -1, "fields" => "ids" ) ); $id = 0; $jobs = array();
				try {
					update_option( "linker_commerce_mail_sends", array_fill( 0, Linker\Commerce\Mail\Throttle::PER_DAY, time() ) );
					$id = wp_insert_user( array( "user_login" => "i254-password-" . wp_generate_uuid4(), "user_pass" => wp_generate_password(), "user_email" => "tester@example.test", "role" => "customer", "locale" => "de_DE_formal" ) );
					if ( is_wp_error( $id ) ) { throw new RuntimeException( $id->get_error_message() ); }
					$login = get_userdata( $id )->user_login; $language = pll_current_language(); $locale = determine_locale();
					$email = WC()->mailer()->get_emails()["WC_Email_Customer_Reset_Password"];
					$email->trigger( $login, "i254-reset-key" );
					$after_admin = array( pll_current_language(), determine_locale() );
					wp_set_current_user( 0 ); if ( ! defined( "DOING_CRON" ) ) { define( "DOING_CRON", true ); }
					$email->trigger( $login, "i254-cron-key" );
					$jobs = array_values( array_diff( get_posts( array( "post_type" => "linker_mail_job", "post_status" => "any", "numberposts" => -1, "fields" => "ids" ) ), $before ) );
					return array( "before" => array( $language, $locale ), "after_admin" => $after_admin, "after_cron" => array( pll_current_language(), determine_locale() ), "messages" => array_map( static fn( $job ) => json_decode( get_post_meta( $job, "_linker_mail_message", true ), true ), $jobs ) );
				} finally {
					foreach ( $jobs as $job ) { as_unschedule_all_actions( "linker_commerce_mail_attempt", array( $job ), "linker-commerce" ); wp_delete_post( $job, true ); }
					if ( $id > 0 ) { require_once ABSPATH . "wp-admin/includes/user.php"; wp_delete_user( $id ); }
					if ( null === $saved ) { delete_option( "linker_commerce_mail_sends" ); } else { update_option( "linker_commerce_mail_sends", $saved ); }
				}'
			);
			self::assertCount( 2, $result['messages'] );
			self::evidence( 'staff-cron-password-queue.json', (string) json_encode( $result, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) );
			foreach ( $result['messages'] as $message ) {
				self::assertStringContainsString( '/de/mein-konto/passwort-zuruecksetzen/', $message['body'] );
				self::assertStringNotContainsString( '/my-account/', $message['body'] );
				self::assertStringContainsString( 'i254-', $message['body'] );
			}
			self::assertSame( $result['before'], $result['after_admin'] );
			self::assertSame( $result['before'], $result['after_cron'] );
		} finally {
			if ( $applied ) {
				self::wp( array( 'linker-i18n', 'german-urls', '--rollback', '--apply' ) ); }
		}
	}

	/** Every reviewed live/historical address and actual canonical title is checked. */
	public function test_all_reviewed_addresses_redirect_once_and_titles_are_distinct(): void {
		$rows = json_decode( (string) file_get_contents( dirname( __DIR__, 2 ) . '/fixtures/german-routes.json' ), true );
		self::assertIsArray( $rows );
		$applied = false;
		$account = null;
		try {
			self::wp( array( 'linker-i18n', 'german-urls', '--apply' ) );
			$applied = true;
			$account = self::php( '$id = wp_insert_user( array( "user_login" => "i254-routes-" . wp_generate_uuid4(), "user_pass" => wp_generate_password(), "user_email" => "i254-routes@example.test", "role" => "customer" ) ); if ( is_wp_error( $id ) ) { throw new RuntimeException( $id->get_error_message() ); } update_user_meta( $id, Linker\Commerce\Registration\Approval::STATUS_META, "approved" ); return array( "id" => $id, "cookie" => LOGGED_IN_COOKIE . "=" . wp_generate_auth_cookie( $id, time() + 600, "logged_in" ) );' );
			$titles  = array();
			$seen    = array();
			foreach ( $rows as $row ) {
				$headers = in_array( $row['kind'], array( 'native Woo endpoint', 'native Woo address child' ), true ) ? array( 'Cookie' => $account['cookie'] ) : array();
				if ( $row['old'] !== $row['new'] ) {
					$response = self::get( $row['old'], $headers );
					self::assertSame( 301, $response['status'], $row['old'] );
					self::assertSame( self::$site . $row['new'], $response['headers']['location'] ?? '', $row['old'] );
				}
				if ( 'native Woo action' === $row['kind'] ) {
					$response = self::get( $row['new'] );
					self::assertSame( 302, $response['status'], 'Woo keeps its native logout transition.' );
					self::assertStringStartsWith( self::$site . $row['terminal'], $response['headers']['location'] ?? '' );
					continue;
				}
				if ( isset( $seen[ $row['new'] ] ) ) {
					continue; }
				$seen[ $row['new'] ] = true;
				$page                = self::get( $row['new'], $headers );
				self::assertSame( 200, $page['status'], $row['new'] );
				preg_match( '#<title>(.*?)</title>#s', $page['body'], $match );
				$title = trim( (string) preg_replace( '/\s+/u', ' ', html_entity_decode( $match[1] ?? '', ENT_QUOTES | ENT_HTML5, 'UTF-8' ) ) );
				self::assertNotSame( '', $title, $row['new'] );
				self::assertArrayNotHasKey( $title, $titles, 'Independent title: ' . $row['new'] );
				self::assertDoesNotMatchRegularExpression( '/\b(?:Warenkorb|Basket|Catalogue|Article|Battery Stack Bridge|Battery Base)\b/iu', $title );
				$titles[ $title ] = $row['new'];
				foreach ( $rows as $alias ) {
					if ( $alias['old'] === $alias['new'] ) {
						continue; }
					self::assertStringNotContainsString( 'href="' . self::$site . $alias['old'] . '"', $page['body'], $row['new'] );
					self::assertStringNotContainsString( 'href="' . $alias['old'] . '"', $page['body'], $row['new'] );
				}
			}
		} finally {
			if ( is_array( $account ) ) {
				self::php( 'require_once ABSPATH . "wp-admin/includes/user.php"; wp_delete_user( $input["id"] );', array( 'id' => $account['id'] ) );
			}
			if ( $applied ) {
				self::wp( array( 'linker-i18n', 'german-urls', '--rollback', '--apply' ) ); }
		}
	}

	/** Preview, repeat application and rollback preserve the first native values. */
	public function test_migration_dry_run_repeat_and_rollback_restore_native_data(): void {
		$snapshot    = ' $out = array(); foreach ( get_posts( array( "post_type" => array( "page", "post", "product" ), "post_status" => "publish", "numberposts" => -1, "lang" => "de", "orderby" => "ID", "order" => "ASC" ) ) as $p ) { $out[] = array( $p->ID, $p->post_name, $p->post_title, $p->post_content, $p->post_excerpt, get_post_meta( $p->ID, "_seopress_titles_title", false ), get_post_meta( $p->ID, "_wp_old_slug", false ) ); } foreach ( get_terms( array( "taxonomy" => array( "category", "product_cat" ), "lang" => "de", "hide_empty" => false ) ) as $t ) { $out[] = array( $t->term_id, $t->slug, $t->name, $t->description ); } return hash( "sha256", wp_json_encode( $out ) );';
		$before      = self::php( $snapshot );
		$bookkeeping = self::php( 'return array( get_option( "linker_i18n_german_urls_backup", null ), get_option( "linker_i18n_german_urls_active", null ) );' );
		self::wp( array( 'linker-i18n', 'german-urls', '--dry-run' ) );
		self::assertSame( $before, self::php( $snapshot ) );
		self::assertSame( $bookkeeping, self::php( 'return array( get_option( "linker_i18n_german_urls_backup", null ), get_option( "linker_i18n_german_urls_active", null ) );' ) );
		try {
			self::wp( array( 'linker-i18n', 'german-urls', '--apply' ) );
			$applied = self::php( $snapshot );
			$backup  = self::php( 'return get_option( "linker_i18n_german_urls_backup" );' );
			self::assertStringContainsString( '0 changes', self::wp( array( 'linker-i18n', 'german-urls', '--apply' ) ) );
			self::assertSame( $applied, self::php( $snapshot ) );
			self::assertSame( $backup, self::php( 'return get_option( "linker_i18n_german_urls_backup" );' ) );
			self::wp( array( 'linker-i18n', 'german-urls', '--rollback', '--dry-run' ) );
			self::assertSame( $applied, self::php( $snapshot ) );
		} finally {
			self::wp( array( 'linker-i18n', 'german-urls', '--rollback', '--apply' ) );
		}
		self::assertSame( $before, self::php( $snapshot ), 'Owned fields, metadata presence and native slug history all restored.' );
	}

	/** Confirmation and detail URLs retain their inquiry identity and opaque key. */
	public function test_inquiry_confirmation_has_a_german_url_and_its_own_title(): void {
		$id      = self::php( '$order = new WC_Order(); $order->set_status( "inquiry-received" ); $order->set_billing_email( "i254@example.test" ); $order->update_meta_data( "_linker_locale", "de_DE_formal" ); return $order->save();' );
		$applied = false;
		try {
			self::wp( array( 'linker-i18n', 'german-urls', '--apply' ) );
			$applied = true;
			$url     = self::php( '$languages = new Linker\I18n\Languages(); $scope = $languages->enter( "de" ); try { return wc_get_order( $input["id"] )->get_checkout_order_received_url(); } finally { $languages->leave( $scope ); }', array( 'id' => $id ) );
			self::assertStringContainsString( '/de/proforma-anfrage/anfrage-eingegangen/' . $id . '/', $url );
			$staff_url = self::php( 'return wc_get_order( $input["id"] )->get_checkout_order_received_url();', array( 'id' => $id ) );
			self::assertSame( $url, $staff_url, 'The stored inquiry language also controls URLs built by staff.' );
			$path   = substr( $url, strlen( self::$site ) );
			$legacy = self::get( str_replace( '/anfrage-eingegangen/', '/inquiry-received/', $path ) );
			self::assertSame( 301, $legacy['status'] );
			self::assertSame( $url, $legacy['headers']['location'] ?? '' );
			$page = self::get( $path );
			self::assertSame( 200, $page['status'] );
			preg_match( '#<title>(.*?)</title>#s', $page['body'], $match );
			self::assertSame( 'Anfrage eingegangen – ' . $id . ' | Linker', html_entity_decode( $match[1] ?? '', ENT_QUOTES | ENT_HTML5, 'UTF-8' ) );
			self::evidence(
				'confirmation-http.json',
				(string) json_encode(
					array(
						'old'           => '/de/proforma-anfrage/inquiry-received/' . $id . '/',
						'new'           => strtok( $path, '?' ),
						'first'         => $legacy['status'],
						'final'         => $page['status'],
						'title'         => html_entity_decode( $match[1] ?? '', ENT_QUOTES | ENT_HTML5, 'UTF-8' ),
						'key_preserved' => true,
					),
					JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES
				)
			);
		} finally {
			if ( $applied ) {
				self::wp( array( 'linker-i18n', 'german-urls', '--rollback', '--apply' ) ); }
			self::php( '$order = wc_get_order( $input["id"] ); if ( $order ) { $order->delete( true ); }', array( 'id' => $id ) );
		}
	}

	/** Unreviewed source data fails the complete preflight before a first backup. */
	public function test_unexpected_existing_slug_is_a_read_only_conflict(): void {
		// This case is the first deployment; other cases exercise retained-backup conflicts.
		self::php( 'delete_option( "linker_i18n_german_urls_backup" );' );
		$fixture = self::php( '$en = get_page_by_path( "faq-download" ); $id = pll_get_post( $en->ID, "de" ); $old = get_post_field( "post_name", $id ); wp_update_post( array( "ID" => $id, "post_name" => "i254-unreviewed-faq" ) ); return array( "id" => $id, "old" => $old, "backup" => get_option( "linker_i18n_german_urls_backup", null ) );' );
		try {
			foreach ( array( '--dry-run', '--apply' ) as $flag ) {
				$result = self::command( array( $flag ) );
				self::assertNotSame( 0, $result['status'], $result['output'] );
				self::assertStringContainsString( 'Unexpected German slug', $result['output'] );
			}
			self::assertSame( $fixture['backup'], self::php( 'return get_option( "linker_i18n_german_urls_backup", null );' ) );
			self::assertSame( 200, self::get( '/de/warenkorb/' )['status'], 'No other migration write happened.' );
		} finally {
			self::php( 'wp_update_post( array( "ID" => $input["id"], "post_name" => $input["old"] ) );', $fixture );
		}
	}

	/** Native address children are German and have independent document titles. */
	public function test_company_address_children_use_native_german_slugs(): void {
		$fixture = self::php( '$id = wp_insert_user( array( "user_login" => "i254-address-" . wp_generate_uuid4(), "user_pass" => wp_generate_password(), "user_email" => "i254-address@example.test", "role" => "customer" ) ); if ( is_wp_error( $id ) ) { throw new RuntimeException( $id->get_error_message() ); } update_user_meta( $id, Linker\Commerce\Registration\Approval::STATUS_META, "approved" ); return array( "id" => $id, "cookie" => LOGGED_IN_COOKIE . "=" . wp_generate_auth_cookie( $id, time() + 600, "logged_in" ) );' );
		$applied = false;
		try {
			self::wp( array( 'linker-i18n', 'german-urls', '--apply' ) );
			$applied = true;
			$titles  = array();
			foreach ( array(
				'billing'  => 'rechnungsadresse',
				'shipping' => 'lieferadresse',
			) as $old => $new ) {
				$legacy = self::get( '/de/mein-konto/company/' . $old . '/', array( 'Cookie' => $fixture['cookie'] ) );
				self::assertSame( 301, $legacy['status'] );
				self::assertSame( self::$site . '/de/mein-konto/unternehmen/' . $new . '/', $legacy['headers']['location'] ?? '' );
				$page = self::get( '/de/mein-konto/unternehmen/' . $new . '/', array( 'Cookie' => $fixture['cookie'] ) );
				self::assertSame( 200, $page['status'], (string) json_encode( $page['headers'] ) );
				preg_match( '#<title>(.*?)</title>#s', $page['body'], $match );
				$titles[] = $match[1] ?? '';
			}
			self::assertCount( 2, array_unique( $titles ), 'Address subpages have independent German titles.' );
		} finally {
			if ( $applied ) {
				self::wp( array( 'linker-i18n', 'german-urls', '--rollback', '--apply' ) ); }
			self::php( 'require_once ABSPATH . "wp-admin/includes/user.php"; wp_delete_user( $input["id"] );', array( 'id' => $fixture['id'] ) );
		}
	}

	/** The live audit's remaining descriptive product names become German too. */
	public function test_battery_accessory_addresses_and_titles_are_german(): void {
		$applied = false;
		try {
			self::wp( array( 'linker-i18n', 'german-urls', '--apply' ) );
			$applied = true;
			foreach ( array(
				'ecoflow-battery-stack-bridge'     => array( 'ecoflow-verbinder-fuer-batteriestapel', 'EcoFlow Verbinder für Batteriestapel | Linker' ),
				'ecoflow-ocean-2-lfp-battery-base' => array( 'ecoflow-ocean-2-lfp-batteriesockel', 'EcoFlow OCEAN 2 LFP-Batteriesockel | Linker' ),
			) as $old => $expected ) {
				$response = self::get( '/de/produkt/' . $old . '/' );
				self::assertSame( 301, $response['status'] );
				self::assertSame( self::$site . '/de/produkt/' . $expected[0] . '/', $response['headers']['location'] ?? '' );
				$page = self::get( '/de/produkt/' . $expected[0] . '/' );
				self::assertSame( 200, $page['status'] );
				self::assertStringContainsString( $expected[1], html_entity_decode( $page['body'], ENT_QUOTES | ENT_HTML5, 'UTF-8' ) );
			}
		} finally {
			if ( $applied ) {
				self::wp( array( 'linker-i18n', 'german-urls', '--rollback', '--apply' ) );
			}
		}
	}

	/** A German customer's approval email uses German account links when sent by staff. */
	public function test_customer_mail_uses_the_recipient_language_and_restores_the_callers_language(): void {
		$applied = false;
		try {
			self::wp( array( 'linker-i18n', 'german-urls', '--apply' ) );
			$applied = true;
			$result  = self::php(
				'$keys = array( "linker_commerce_mail_sends", "linker_commerce_test_mail_to" ); $saved = array(); foreach ( $keys as $key ) { $saved[$key] = get_option( $key, null ); }
				$before = glob( LINKER_LOCAL_MAIL_DIR . "/*.eml" ) ?: array(); $id = 0; $files = array();
				try {
					update_option( "linker_commerce_mail_sends", array() ); update_option( "linker_commerce_test_mail_to", "tester@example.test" );
					$id = wp_insert_user( array( "user_login" => "i254-mail-" . wp_generate_uuid4(), "user_pass" => wp_generate_password(), "user_email" => "i254@example.test", "role" => "customer", "locale" => "de_DE_formal" ) );
					if ( is_wp_error( $id ) ) { throw new RuntimeException( $id->get_error_message() ); }
					$original = pll_current_language();
					$email = new Linker\Commerce\Registration\Emails\ApprovedEmail( WP_PLUGIN_DIR . "/linker-commerce/linker-commerce.php" );
					$email->trigger( $id, "pending", "approved", "" );
					$files = array_values( array_diff( glob( LINKER_LOCAL_MAIL_DIR . "/*.eml" ) ?: array(), $before ) );
					return array( "before_language" => $original, "after_language" => pll_current_language(), "mails" => array_map( static fn( $file ) => file_get_contents( $file ), $files ) );
				} finally {
					if ( is_int( $id ) && $id > 0 ) { require_once ABSPATH . "wp-admin/includes/user.php"; wp_delete_user( $id ); }
					foreach ( $files as $file ) { unlink( $file ); }
					foreach ( $saved as $key => $value ) { if ( null === $value ) { delete_option( $key ); } else { update_option( $key, $value ); } }
				}'
			);
			self::assertCount( 1, $result['mails'], 'Exactly one delivery, captured in a local file.' );
			$mail = quoted_printable_decode( $result['mails'][0] );
			self::evidence( 'approval.eml', $mail );
			self::assertStringContainsString( 'To: tester@example.test', $mail );
			self::assertStringContainsString( 'href="' . self::$site . '/de/mein-konto/"', $mail );
			self::assertStringNotContainsString( 'href="' . self::$site . '/my-account/"', $mail );
			self::assertSame( $result['before_language'], $result['after_language'] );
		} finally {
			if ( $applied ) {
				self::wp( array( 'linker-i18n', 'german-urls', '--rollback', '--apply' ) );
			}
		}
	}

	/** Present keeps its German template assignments after the pages are renamed. */
	public function test_present_finds_the_german_pages_by_their_english_pairs(): void {
		$presentation = self::php( 'return get_option( "linker_commerce_present_backup", null );' );
		$applied      = false;
		try {
			self::wp( array( 'linker-i18n', 'german-urls', '--apply' ) );
			$applied = true;
			self::wp( array( 'linker-commerce', 'present', '--allow-stale' ) );
			self::assertStringContainsString( 'presentation in sync', self::wp( array( 'linker-commerce', 'check' ) ) );
			self::assertStringContainsString( 'linker-library-tabbar', self::get( '/de/faq-dokumente/' )['body'] );
		} finally {
			if ( $applied ) {
				self::wp( array( 'linker-i18n', 'german-urls', '--rollback', '--apply' ) );
			}
			self::php( 'if ( null === $input["backup"] ) { delete_option( "linker_commerce_present_backup" ); } else { update_option( "linker_commerce_present_backup", $input["backup"] ); }', array( 'backup' => $presentation ) );
		}
	}

	/** Imported German product copy determines its first address and later imports preserve it. */
	public function test_new_german_product_uses_its_german_title_and_import_keeps_migrated_urls(): void {
		$source = self::php( '$id = wp_insert_post( array( "post_type" => "product", "post_status" => "publish", "post_name" => "i254-ev-charger", "post_title" => "I254 EV charger" ) ); pll_set_post_language( $id, "en" ); return $id;' );
		$file   = tempnam( sys_get_temp_dir(), 'i254-import-' );
		self::assertIsString( $file );
		try {
			file_put_contents(
				$file,
				(string) json_encode(
					array(
						array(
							'kind'   => 'post',
							'source' => $source,
							'fields' => array( 'post_title' => 'I254 grüne Ladestation' ),
						),
					)
				)
			);
			self::wp( array( 'linker-i18n', 'import', '--input=' . $file ) );
			self::assertSame( 200, self::get( '/de/produkt/i254-gruene-ladestation/' )['status'] );
			self::php( 'wp_update_post( array( "ID" => $input["id"], "post_excerpt" => "Updated English description." ) );', array( 'id' => $source ) );
			file_put_contents(
				$file,
				(string) json_encode(
					array(
						array(
							'kind'   => 'post',
							'source' => $source,
							'slug'   => 'i254-ev-charger',
							'fields' => array( 'post_title' => 'I254 grüne Ladestation' ),
						),
					)
				)
			);
			self::wp( array( 'linker-i18n', 'import', '--input=' . $file ) );
			self::assertSame( 200, self::get( '/de/produkt/i254-gruene-ladestation/' )['status'] );
			self::assertSame( 200, self::get( '/product/i254-ev-charger/' )['status'] );
		} finally {
			unlink( $file );
			self::php( 'foreach ( as_get_scheduled_actions( array( "hook" => "linker_i18n_translate", "group" => "linker-i18n", "per_page" => -1 ), "ids" ) as $action ) { $args = ActionScheduler::store()->fetch_action( $action )->get_args(); if ( "post" === $args[0] && $input["source"] === (int) $args[1] ) { ActionScheduler::store()->delete_action( $action ); } } $de = pll_get_post( $input["source"], "de" ); if ( $de ) { wp_delete_post( $de, true ); } wp_delete_post( $input["source"], true );', array( 'source' => $source ) );
		}
	}

	/** Saves the instance's pre-test migration state. */
	protected function setUp(): void {
		parent::setUp();
		$this->migration_state = self::php( 'return array( "backup" => get_option( "linker_i18n_german_urls_backup", null ), "active" => get_option( "linker_i18n_german_urls_active", null ) );' );
		if ( $this->migration_state['active'] ) {
			self::wp( array( 'linker-i18n', 'german-urls', '--rollback', '--apply' ) );
		}
	}

	/** Restores bookkeeping after each test's public rollback. */
	protected function tearDown(): void {
		self::php( 'foreach ( array( "backup", "active" ) as $key ) { $option = "linker_i18n_german_urls_" . $key; if ( null === $input[$key] ) { delete_option( $option ); } else { update_option( $option, $input[$key], false ); } } flush_rewrite_rules( false );', $this->migration_state );
		if ( is_array( $this->migration_state ) && $this->migration_state['active'] ) {
			self::wp( array( 'linker-i18n', 'german-urls', '--apply' ) );
		}
		parent::tearDown();
	}

	/** Verification fails before migration and succeeds only after the stored data agrees. */
	public function test_verify_reports_pending_changes_and_accepts_a_repeatable_migration(): void {
		$before = self::command( array( '--verify' ) );
		self::assertNotSame( 0, $before['status'], 'Verification must reject pending German addresses and titles.' );
		$applied = false;
		try {
			self::wp( array( 'linker-i18n', 'german-urls', '--apply' ) );
			$applied  = true;
			$verified = self::command( array( '--verify' ) );
			self::assertSame( 0, $verified['status'], $verified['output'] );
			self::assertStringContainsString( 'Verified', $verified['output'] );
		} finally {
			if ( $applied ) {
				self::wp( array( 'linker-i18n', 'german-urls', '--rollback', '--apply' ) );
			}
		}
	}

	/**
	 * Runs the public command when a nonzero exit is part of its contract.
	 *
	 * @param array $options Public flags.
	 * @phpstan-param list<string> $options
	 * @return array{status:int,output:string}
	 */
	private static function command( array $options ): array {
		$process = proc_open(
			array_merge( array( (string) getenv( 'LINKER_I18N_WP' ), 'linker-i18n', 'german-urls' ), $options, array( '--user=1' ) ),
			array(
				1 => array( 'pipe', 'w' ),
				2 => array( 'pipe', 'w' ),
			),
			$pipes
		);
		self::assertIsResource( $process );
		$output = (string) stream_get_contents( $pipes[1] ) . (string) stream_get_contents( $pipes[2] );
		fclose( $pipes[1] );
		fclose( $pipes[2] );
		return array(
			'status' => proc_close( $process ),
			'output' => $output,
		);
	}

	/** Stored titles and links migrate along with their public addresses. */
	public function test_apply_updates_stored_titles_and_content_links(): void {
		$ids = self::php(
			'$en = wp_insert_post( array( "post_type" => "page", "post_status" => "publish", "post_name" => "i254-links-en", "post_title" => "Link fixture" ) );
			$de = wp_insert_post( array( "post_type" => "page", "post_status" => "publish", "post_name" => "i254-links", "post_title" => "Link-Prüfung", "post_content" => "<a href=\"/de/faq-download/\">Dokumente</a>" ) );
			pll_set_post_language( $en, "en" ); pll_set_post_language( $de, "de" ); pll_save_post_translations( array( "en" => $en, "de" => $de ) ); return array( $en, $de );'
		);
		self::php( '$post = get_post( $input["id"] ); wp_update_post( array( "ID" => $post->ID, "post_content" => $post->post_content . "<a href=\"/de/faq-download/?origin=/de/warenkorb/\">Prüfung</a><a href=\"https://example.test/de/faq-download/\">Extern</a>" ) );', array( 'id' => $ids[1] ) );
		$applied = false;
		try {
			self::wp( array( 'linker-i18n', 'german-urls', '--apply' ) );
			$applied = true;
			self::assertStringContainsString( 'href="/de/faq-dokumente/"', self::get( '/de/i254-links/' )['body'] );
			self::assertStringContainsString( 'href="/de/faq-dokumente/?origin=/de/warenkorb/"', self::get( '/de/i254-links/' )['body'] );
			self::assertStringContainsString( 'href="https://example.test/de/faq-download/"', self::get( '/de/i254-links/' )['body'] );
			self::assertSame( "Lösungsentwurf\n", self::wp( array( 'post', 'list', '--post_type=page', '--name=loesungsentwurf', '--lang=de', '--field=post_title' ) ) );
		} finally {
			if ( $applied ) {
				self::wp( array( 'linker-i18n', 'german-urls', '--rollback', '--apply' ) );
			}
			self::php( 'foreach ( $input["ids"] as $id ) { wp_delete_post( $id, true ); }', array( 'ids' => $ids ) );
		}
	}

	/** Each German authentication page has its own actual document title. */
	public function test_authentication_titles_are_independent_and_german(): void {
		$applied = false;
		try {
			self::wp( array( 'linker-i18n', 'german-urls', '--apply' ) );
			$applied = true;
			foreach ( array(
				'/de/mein-konto/'                        => 'Beim Partnerkonto anmelden | Linker',
				'/de/mein-konto/registrieren/'           => 'Partnerkonto erstellen | Linker',
				'/de/mein-konto/passwort-zuruecksetzen/' => 'Passwort zurücksetzen | Linker',
			) as $path => $title ) {
				$page = self::get( $path );
				preg_match( '#<title>(.*?)</title>#s', $page['body'], $match );
				self::assertSame( $title, trim( html_entity_decode( $match[1] ?? '', ENT_QUOTES | ENT_HTML5, 'UTF-8' ) ), $path );
			}
			self::assertStringContainsString( 'Partner Account: Sign In or Register | Linker', self::get( '/my-account/' )['body'] );
		} finally {
			if ( $applied ) {
				self::wp( array( 'linker-i18n', 'german-urls', '--rollback', '--apply' ) );
			}
		}
	}

	/** Woo endpoint keys stay native while German endpoint addresses change. */
	public function test_account_endpoint_aliases_preserve_queries_and_forms(): void {
		$applied = false;
		try {
			self::wp( array( 'linker-i18n', 'german-urls', '--apply' ) );
			$applied = true;
			foreach ( array(
				'register'      => 'registrieren',
				'lost-password' => 'passwort-zuruecksetzen',
			) as $old => $new ) {
				$query    = '?key=a%2Fb&source=https%3A%2F%2Fexample.test%2Fde%2F';
				$response = self::get( '/de/mein-konto/' . $old . '/' . $query );
				self::assertSame( 301, $response['status'] );
				self::assertSame( self::$site . '/de/mein-konto/' . $new . '/' . $query, $response['headers']['location'] ?? '' );
				self::assertSame( 200, self::get( '/de/mein-konto/' . $new . '/' )['status'] );
			}
			self::assertStringContainsString( '/de/mein-konto/registrieren/', self::get( '/de/mein-konto/' )['body'] );
			self::assertSame( 200, self::get( '/my-account/register/' )['status'] );
		} finally {
			if ( $applied ) {
				self::wp( array( 'linker-i18n', 'german-urls', '--rollback', '--apply' ) );
			}
		}
	}

	/** Both the current English category path and historical German alias survive. */
	public function test_blog_category_history_reaches_the_german_archive(): void {
		$applied = false;
		try {
			self::wp( array( 'linker-i18n', 'german-urls', '--apply' ) );
			$applied = true;
			foreach ( array( '/de/category/system-design/', '/de/category/systemauslegung/' ) as $path ) {
				$old = self::get( $path );
				self::assertSame( 301, $old['status'], $path );
				self::assertSame( self::$site . '/de/kategorie/systemauslegung/', $old['headers']['location'] ?? '' );
			}
			self::assertSame( 200, self::get( '/de/kategorie/systemauslegung/' )['status'] );
			self::assertSame( 200, self::get( '/category/system-design/' )['status'] );
		} finally {
			if ( $applied ) {
				self::wp( array( 'linker-i18n', 'german-urls', '--rollback', '--apply' ) );
			}
		}
	}

	/** Hierarchical pages need explicit history rather than core's product history. */
	public function test_a_renamed_page_has_a_single_german_redirect(): void {
		$applied = false;
		try {
			self::wp( array( 'linker-i18n', 'german-urls', '--apply' ) );
			$applied = true;
			$old     = self::get( '/de/faq-download/?ref=254' );
			self::assertSame( 301, $old['status'] );
			self::assertSame( self::$site . '/de/faq-dokumente/?ref=254', $old['headers']['location'] ?? '' );
			self::assertSame( 200, self::get( '/de/faq-dokumente/' )['status'] );
			self::assertSame( 200, self::get( '/faq-download/' )['status'] );
		} finally {
			if ( $applied ) {
				self::wp( array( 'linker-i18n', 'german-urls', '--rollback', '--apply' ) );
			}
		}
	}

	/** Applying a renamed product preserves the English URL and redirects German. */
	public function test_apply_redirects_the_old_product_and_keeps_english(): void {
		$ids = self::php(
			'$en = wp_insert_post( array( "post_type" => "product", "post_status" => "publish", "post_name" => "i254-ev-charger", "post_title" => "I254 EV charger" ) );
			$de = wp_insert_post( array( "post_type" => "product", "post_status" => "publish", "post_name" => "i254-ev-charger", "post_title" => "I254 Ladestation" ) );
			pll_set_post_language( $en, "en" ); pll_set_post_language( $de, "de" );
			pll_save_post_translations( array( "en" => $en, "de" => $de ) );
			wp_update_post( array( "ID" => $de, "post_name" => "i254-ev-charger" ) );
			return array( $en, $de );'
		);
		self::php( 'add_post_meta( $input["id"], "_wp_old_slug", "i254-ev-charger" );', array( 'id' => $ids[0] ) );
		$applied = false;
		try {
			self::wp( array( 'linker-i18n', 'german-urls', '--apply' ) );
			$applied = true;
			$old     = self::get( '/de/produkt/i254-ev-charger/?ref=254' );
			self::assertSame( 301, $old['status'] );
			self::assertSame( self::$site . '/de/produkt/i254-ladestation/?ref=254', $old['headers']['location'] ?? '' );
			self::assertSame( 200, self::get( '/de/produkt/i254-ladestation/' )['status'] );
			self::assertSame( 200, self::get( '/product/i254-ev-charger/' )['status'] );
			self::assertStringContainsString( '0 changes', self::wp( array( 'linker-i18n', 'german-urls', '--apply' ) ) );
		} finally {
			if ( $applied ) {
				self::wp( array( 'linker-i18n', 'german-urls', '--rollback', '--apply' ) );
			}
			self::php( 'foreach ( $input["ids"] as $id ) { wp_delete_post( $id, true ); }', array( 'ids' => $ids ) );
		}
	}

	/** A preview names the change without changing the public page. */
	public function test_a_dry_run_preserves_the_existing_address(): void {
		$ids = self::php(
			'$en = wp_insert_post( array( "post_type" => "product", "post_status" => "publish", "post_name" => "i254-ev-charger", "post_title" => "I254 EV charger" ) );
			$de = wp_insert_post( array( "post_type" => "product", "post_status" => "publish", "post_name" => "i254-ev-charger", "post_title" => "I254 Ladestation" ) );
			pll_set_post_language( $en, "en" ); pll_set_post_language( $de, "de" );
			pll_save_post_translations( array( "en" => $en, "de" => $de ) );
			wp_update_post( array( "ID" => $de, "post_name" => "i254-ev-charger" ) );
			return array( $en, $de );'
		);
		try {
			$before = self::get( '/de/produkt/i254-ev-charger/' );
			$plan   = self::wp( array( 'linker-i18n', 'german-urls', '--dry-run' ) );
			self::assertStringContainsString( 'i254-ladestation', $plan );
			$after = self::get( '/de/produkt/i254-ev-charger/' );
			self::assertSame( 200, $before['status'] );
			self::assertSame( $before['status'], $after['status'] );
			self::assertSame( $before['headers']['location'] ?? '', $after['headers']['location'] ?? '' );
		} finally {
			self::php( 'foreach ( $input["ids"] as $id ) { wp_delete_post( $id, true ); }', array( 'ids' => $ids ) );
		}
	}
}
