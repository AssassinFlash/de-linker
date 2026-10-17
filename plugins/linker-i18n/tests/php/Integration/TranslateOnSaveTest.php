<?php
/**
 * Translation on save, end to end.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Integration;

/**
 * An English product goes through the life of its German version: saved
 * without a key (pending), translated, saved unchanged (nothing sent),
 * edited in English (only the changed paragraph translated again), edited
 * in German by a person (kept, needs review, accepted), and given a
 * translation the validator rejects (nothing stored).
 *
 * The translator is the DeepSeek stand-in, which marks its German with
 * "[de]" and swaps in the glossary's terms.
 *
 * @coversNothing
 */
final class TranslateOnSaveTest extends SiteTestCase {

	private const SLUG = 'linker-i18n-test-inverter';

	private const SKU = 'LINKER-I18N-TEST-1';

	/**
	 * The English description, paragraph by paragraph.
	 */
	private const PARAGRAPHS = array(
		'<p>The <strong>GW10K-EHA-G20</strong> delivers 10.0 kW of AC power.</p>',
		'<p>Download the datasheet for the wiring diagram.</p>',
		'<p>The battery warranty covers ten years.</p>',
	);

	/**
	 * The English product.
	 *
	 * @var int
	 */
	private static int $english = 0;

	/**
	 * Removes what an earlier run left, then creates the English product.
	 */
	public static function setUpBeforeClass(): void {
		parent::setUpBeforeClass();
		self::stub();
		self::remove();
		$created = self::php(
			'
			$product = new WC_Product_Simple();
			$product->set_name( "Linker i18n test inverter" );
			$product->set_slug( $input["slug"] );
			$product->set_status( "publish" );
			$product->set_description( $input["description"] );
			$product->set_sku( $input["sku"] );
			$product->set_regular_price( "1234" );
			$product->set_manage_stock( true );
			$product->set_stock_quantity( 7 );
			return $product->save();
			',
			array(
				'slug'        => self::SLUG,
				'description' => implode( "\n", self::PARAGRAPHS ),
				'sku'         => self::SKU,
			)
		);
		self::assertIsInt( $created );
		self::$english = $created;
	}

	/**
	 * Deletes the test products.
	 */
	public static function tearDownAfterClass(): void {
		if ( '' !== self::$site ) {
			self::remove();
		}
		parent::tearDownAfterClass();
	}

	/**
	 * Deletes the English test product and its German version.
	 */
	private static function remove(): void {
		self::php(
			'
			foreach ( get_posts( array( "post_type" => "product", "post_status" => "any", "name" => $input["slug"], "lang" => "", "numberposts" => -1, "fields" => "ids" ) ) as $id ) {
				as_unschedule_all_actions( "linker_i18n_translate", array( "post", $id, false, 1 ), "linker-i18n" );
				as_unschedule_all_actions( "linker_i18n_translate", array( "post", $id, true, 1 ), "linker-i18n" );
				wp_delete_post( $id, true );
			}
			return true;
			',
			array( 'slug' => self::SLUG )
		);
	}

	/**
	 * The state of the pair: status and note of the English product, and
	 * the German product's ID, language, slug, description and commerce fields.
	 *
	 * @return array<string, mixed>
	 */
	private static function state(): array {
		$state = self::php(
			'
			$id     = $input["id"];
			$german = (int) pll_get_post( $id, "de" );
			$twin   = $german ? wc_get_product( $german ) : null;
			ob_start();
			do_action( "manage_product_posts_custom_column", "linker_i18n", $id );
			$cell = ob_get_clean();
			ob_start();
			if ( $german ) { do_action( "manage_product_posts_custom_column", "linker_i18n", $german ); }
			$german_cell = ob_get_clean();
			return array(
				"status"       => (string) get_post_meta( $id, "_linker_i18n_status", true ),
				"note"         => (string) get_post_meta( $id, "_linker_i18n_note", true ),
				"queued"       => as_has_scheduled_action( "linker_i18n_translate", array( "post", $id, false, 1 ), "linker-i18n" ),
				"german"       => $german,
				"language"     => $german ? (string) pll_get_post_language( $german ) : "",
				"slug"         => $german ? get_post_field( "post_name", $german ) : "",
				"content"      => $german ? get_post_field( "post_content", $german ) : "",
				"sku"          => $german ? (string) get_post_meta( $german, "_sku", true ) : "",
				"manage_stock" => $twin ? $twin->get_manage_stock() : false,
				"price"        => $twin ? $twin->get_regular_price() : "",
				"stock_status" => $twin ? $twin->get_stock_status() : "",
				"reviewed"     => $german ? json_decode( (string) get_post_meta( $german, "_linker_i18n_reviewed", true ), true ) : null,
				"cell"         => wp_strip_all_tags( $cell ),
				"german_cell"  => wp_strip_all_tags( $german_cell ),
			);
			',
			array( 'id' => self::$english )
		);
		self::assertIsArray( $state );
		return $state;
	}

	/**
	 * Sets the English description, saved as an editor saves it.
	 *
	 * @param array<int, string> $paragraphs Paragraphs.
	 */
	private static function write_english( array $paragraphs ): void {
		self::php(
			'$product = wc_get_product( $input["id"] ); $product->set_description( $input["description"] ); return $product->save();',
			array(
				'id'          => self::$english,
				'description' => implode( "\n", $paragraphs ),
			)
		);
	}

	/**
	 * Saves a post with new fields, as a person saves it in the editor.
	 *
	 * @param int                  $id     Post ID.
	 * @param array<string, mixed> $fields Fields to change.
	 */
	private static function save_post( int $id, array $fields = array() ): void {
		self::php(
			'return wp_update_post( array( "ID" => $input["id"] ) + $input["fields"] );',
			array(
				'id'     => $id,
				'fields' => $fields,
			)
		);
	}

	/**
	 * The paragraphs of a description.
	 *
	 * @param string $html Description.
	 * @return list<string>
	 */
	private static function paragraphs( string $html ): array {
		preg_match_all( '#<p>.*?</p>#s', $html, $matches );
		return $matches[0];
	}

	/**
	 * Saved without DEEPSEEK_API_KEY: the product is English, the job is
	 * queued, and running it leaves the German version pending.
	 */
	public function test_without_key_the_translation_is_pending(): void {
		$state = self::state();
		$this->assertSame( 'pending', $state['status'] );
		$this->assertSame( 'queued', $state['note'] );
		$this->assertTrue( $state['queued'] );
		$this->assertSame( 'Missing, translation pending', $state['cell'] );

		$this->assertSame( 1, self::run_jobs( 'post', self::$english, false ) );

		$state = self::state();
		$this->assertSame( 'failed', $state['status'] );
		$this->assertSame( 'DEEPSEEK_API_KEY is not set', $state['note'] );
		$this->assertSame( 0, $state['german'] );
	}

	/**
	 * Translated: a German product with the same slug, every paragraph in
	 * the translator's German with the markup kept, the glossary's term, and
	 * the English product's commerce fields without SKU and stock.
	 *
	 * @depends test_without_key_the_translation_is_pending
	 */
	public function test_translation_makes_the_german_product(): void {
		self::wp( array( 'linker-i18n', 'translate', (string) self::$english ) );
		$this->assertSame( 1, self::run_jobs( 'post', self::$english, true ) );

		$state = self::state();
		$this->assertSame( 'synced', $state['status'] );
		$this->assertSame( 'de', $state['language'] );
		$this->assertSame( self::SLUG, $state['slug'] );
		$this->assertSame( 'Synced', $state['cell'] );
		$this->assertSame( $state['cell'], $state['german_cell'] );
		$paragraphs = self::paragraphs( $state['content'] );
		$this->assertCount( 3, $paragraphs );
		$this->assertSame( '<p>[de] The <strong>GW10K-EHA-G20</strong> delivers 10.0 kW of AC power.</p>', $paragraphs[0] );
		$this->assertSame( '<p>[de] Download the Datenblatt for the wiring diagram.</p>', $paragraphs[1] );
		$this->assertSame( '', $state['sku'] );
		$this->assertFalse( $state['manage_stock'] );
		$this->assertSame( '1234', $state['price'] );
		$this->assertSame( 'instock', $state['stock_status'] );

		$page = self::get( '/de/produkt/' . self::SLUG . '/' );
		$this->assertSame( 200, $page['status'] );
		$this->assertStringContainsString( '[de] Download the Datenblatt for the wiring diagram.', $page['body'] );
	}

	/**
	 * Saved again unchanged (Update without an edit): the job runs without a
	 * translator and needs none; the German stays as it is.
	 *
	 * @depends test_translation_makes_the_german_product
	 */
	public function test_unchanged_english_is_not_translated_again(): void {
		$before = self::state()['content'];
		self::save_post( self::$english );
		$this->assertSame( 1, self::run_jobs( 'post', self::$english, false ) );
		self::wp( array( 'linker-i18n', 'translate', (string) self::$english, '--now' ) );

		$state = self::state();
		$this->assertSame( 'synced', $state['status'] );
		$this->assertSame( $before, $state['content'] );
	}

	/**
	 * One English paragraph changed: only that paragraph is translated again.
	 *
	 * @depends test_unchanged_english_is_not_translated_again
	 */
	public function test_changed_paragraph_alone_is_translated_again(): void {
		$before        = self::paragraphs( self::state()['content'] );
		$paragraphs    = self::PARAGRAPHS;
		$paragraphs[2] = '<p>The battery warranty covers twelve years.</p>';
		self::write_english( $paragraphs );
		$this->assertSame( 1, self::run_jobs( 'post', self::$english, true ) );

		$after = self::paragraphs( self::state()['content'] );
		$this->assertSame( array_slice( $before, 0, 2 ), array_slice( $after, 0, 2 ) );
		$this->assertSame( '<p>[de] The battery warranty covers twelve years.</p>', $after[2] );
		$this->assertSame( 'synced', self::state()['status'] );
	}

	/**
	 * Legacy manual locks do not block a new English update.
	 *
	 * @depends test_changed_paragraph_alone_is_translated_again
	 */
	public function test_edited_german_is_updated_automatically(): void {
		$state     = self::state();
		$german    = self::paragraphs( $state['content'] );
		$german[1] = '<p>Laden Sie das Datenblatt mit dem Schaltplan herunter.</p>';
		self::save_post( $state['german'], array( 'post_content' => implode( "\n", $german ) ) );
		self::php( 'update_post_meta( $input["id"], "_linker_i18n_reviewed", wp_json_encode( array( "post_content" => "*" ) ) ); return true;', array( 'id' => $state['german'] ) );
		$english    = self::PARAGRAPHS;
		$english[1] = '<p>Download the datasheet and the manual for the wiring diagram.</p>';
		$english[2] = '<p>The battery warranty covers twelve years in Germany.</p>';
		self::write_english( $english );
		$this->assertSame( 1, self::run_jobs( 'post', self::$english, true ) );
		$state = self::state();
		$after = self::paragraphs( $state['content'] );
		$this->assertSame( 'synced', $state['status'] );
		$this->assertSame( '', $state['note'] );
		$this->assertSame( 'Synced', $state['cell'] );
		$this->assertSame( '<p>[de] Download the Datenblatt and the manual for the wiring diagram.</p>', $after[1] );
		$this->assertSame( '<p>[de] The battery warranty covers twelve years in Germany.</p>', $after[2] );
		$this->assertSame( array( 'post_content' => '*' ), $state['reviewed'] );
	}

	/**
	 * A translation that loses its protected model placeholder is rejected twice and nothing is
	 * stored: the German stays as it was and the product is failed.
	 *
	 * @depends test_edited_german_is_updated_automatically
	 */
	public function test_rejected_translation_stores_nothing(): void {
		$before     = self::state()['content'];
		$english    = self::PARAGRAPHS;
		$english[1] = '<p>Download the datasheet and the manual for the wiring diagram.</p>';
		$english[2] = '<p>BREAK-PLACEHOLDERS: the IP65 warranty covers twelve years.</p>';
		self::write_english( $english );
		$this->assertSame( 1, self::run_jobs( 'post', self::$english, true ) );

		$state = self::state();
		$this->assertSame( 'failed', $state['status'] );
		$this->assertStringStartsWith( 'translation rejected (placeholders changed): BREAK-PLACEHOLDERS', $state['note'] );
		$this->assertSame( $before, $state['content'] );
		$this->assertSame( 'Translation failed', $state['cell'] );
	}
}
