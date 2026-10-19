<?php
/**
 * A product title change with a paragraph-level excerpt baseline.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Unit\Translation;

use Linker\I18n\Jobs;
use Linker\I18n\Languages;
use Linker\I18n\LinkLocalizer;
use Linker\I18n\Tests\Unit\PolylangDouble;
use Linker\I18n\Translation\Aligner;
use Linker\I18n\Translation\Client;
use Linker\I18n\Translation\Fields;
use Linker\I18n\Translation\HtmlTokenizer;
use Linker\I18n\Translation\Planner;
use Linker\I18n\Translation\Rules;
use Linker\I18n\Translation\Segmenter;
use Linker\I18n\Translation\State;
use Linker\I18n\Translation\TranslationFailed;
use Linker\I18n\Translation\Translator;
use Linker\I18n\Translation\Validator;
use Linker\I18n\Twins;
use Linker\I18n\Woo\Projection;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * The live failure: a title edit was refused because the excerpt baseline
 * was still one paragraph, and the next save replaced the failure with pending.
 *
 * @covers \Linker\I18n\Translation\Translator
 * @covers \Linker\I18n\Jobs
 */
final class TitleChangeTest extends TestCase {

	private const EXCERPT = '<p>First sentence stays. Second sentence stays.</p>';

	private const GERMAN_EXCERPT = '<p>Erster Satz bleibt. Zweiter Satz bleibt.</p>';

	private const OLD_TITLE = 'Workshop meter';

	private const NEW_TITLE = 'Workshop meter C406';

	private const GERMAN_TITLE = 'Werkstattzähler';

	/**
	 * Metadata written during the test, keyed by kind, id and meta key.
	 *
	 * @var array<string, array<int, array<string, string>>>
	 */
	private array $meta = array();

	/**
	 * The changed title is translated and the untouched excerpt stays German.
	 */
	public function test_a_title_change_writes_german_and_keeps_the_excerpt(): void {
		$written = $this->translate( false );
		$this->assertIsArray( $written );
		$this->assertSame( '[de] Workshop meter C406', $written['post_title'] );
		$this->assertSame( self::GERMAN_EXCERPT, $written['post_excerpt'] );
		$this->assertSame( State::SYNCED, $this->meta['post'][5][ State::STATUS ] );
		$this->assertArrayNotHasKey( State::NOTE, $this->meta['post'][5] );
	}

	/**
	 * A refused translation leaves the previous German in place and stays failed.
	 */
	public function test_a_forced_failure_keeps_the_previous_german_and_the_failure(): void {
		$written = $this->translate( true );
		$this->assertNull( $written );
		$this->assertSame( State::FAILED, $this->meta['post'][5][ State::STATUS ] );
		$this->assertSame( 'stand-in refused', $this->meta['post'][5][ State::NOTE ] );

		$jobs = $this->jobs( $this->client( true ) );
		$this->assertTrue( $jobs->queue( State::POST, 5 ) );
		$this->assertSame( State::FAILED, $this->meta['post'][5][ State::STATUS ] );
		$this->assertSame( 'stand-in refused', $this->meta['post'][5][ State::NOTE ] );

		$this->meta['post'][5][ State::STATUS ] = State::STRUCTURE_MISMATCH;
		$this->meta['post'][5][ State::NOTE ]   = 'German out of date: structure differs';
		$this->assertTrue( $jobs->queue( State::POST, 5 ) );
		$this->assertSame( State::STRUCTURE_MISMATCH, $this->meta['post'][5][ State::STATUS ] );
		$this->assertSame( 'German out of date: structure differs', $this->meta['post'][5][ State::NOTE ] );
	}

	/**
	 * Runs one translation of the changed title.
	 *
	 * @param bool $fail Whether the client refuses.
	 * @return array<string, string>|null German values written, or null when nothing was written.
	 */
	private function translate( bool $fail ): ?array {
		$written = null;
		$this->wordpress( $written );
		$languages  = new Languages();
		$tokenizer  = new HtmlTokenizer();
		$twins      = new Twins( $languages, new LinkLocalizer( $languages, $tokenizer ), new Projection( $languages ) );
		$translator = $this->translator( $this->client( $fail ), $twins );
		if ( $fail ) {
			( new Jobs( $languages, $translator, $twins, new State() ) )->run( State::POST, 5 );
		} else {
			$translator->post( 5 );
		}
		$this->assertConditionsMet();
		return $written;
	}

	/**
	 * The English product, its German twin and the paragraph-level excerpt baseline.
	 *
	 * @param array<string, mixed>|null $written German post fields passed to wp_update_post().
	 */
	private function wordpress( ?array &$written ): void {
		$segmenter = new Segmenter( new HtmlTokenizer() );
		PolylangDouble::mock(
			array(
				5 => 'en',
				6 => 'de',
			),
			array( 5 => 6 ),
			array(),
			array(),
			'en',
			array(),
			array(
				5 => $this->post_fields( self::NEW_TITLE, self::EXCERPT ),
				6 => $this->post_fields( self::GERMAN_TITLE, self::GERMAN_EXCERPT ),
			)
		);
		$this->meta = array(
			'post' => array(
				6 => array(
					State::SOURCE_HASH => 'stale',
					State::UNITS       => (string) json_encode( // phpcs:ignore WordPress.WP.AlternativeFunctions.json_encode_json_encode -- stored before wp_json_encode() is mocked.
						array(
							'post_title'   => array(
								'src'      => $segmenter->text( self::OLD_TITLE )->hashes(),
								'out'      => $segmenter->text( self::GERMAN_TITLE )->hashes(),
								'conflict' => false,
							),
							'post_excerpt' => array(
								'src'      => $segmenter->block_hashes( self::EXCERPT, true ),
								'out'      => array( 'old-paragraph' ),
								'conflict' => false,
							),
						)
					),
				),
			),
		);
		// @phpstan-ignore-next-line WP_Mock's responder types are not in its stubs.
		WP_Mock::onFilter( 'linker_i18n_translatable_meta' )->withAnyArgs()->reply( Fields::SEO_META );
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'return' => static fn( int $id, string $key = '', bool $single = false ): mixed => $single ? '' : array(),
			)
		);
		WP_Mock::userFunction( 'has_filter', array( 'return' => false ) );
		WP_Mock::userFunction( 'remove_action', array( 'return' => false ) );
		WP_Mock::userFunction( 'get_the_terms', array( 'return' => array( 1 ) ) );
		WP_Mock::userFunction( 'get_object_taxonomies', array( 'return' => array() ) );
		WP_Mock::userFunction( 'is_post_type_hierarchical', array( 'return' => false ) );
		WP_Mock::userFunction( 'wc_get_product', array( 'return' => null ) );
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => false ) );
		WP_Mock::passthruFunction( '__' );
		WP_Mock::userFunction(
			'wp_update_post',
			array(
				'return' => static function ( array $postarr ) use ( &$written ): int {
					$written = $postarr;
					return (int) $postarr['ID'];
				},
			)
		);
		WP_Mock::userFunction(
			'get_metadata',
			array(
				'return' => function ( string $kind, int $id, string $key ): string {
					return $this->meta[ $kind ][ $id ][ $key ] ?? '';
				},
			)
		);
		WP_Mock::userFunction(
			'update_metadata',
			array(
				'return' => function ( string $kind, int $id, string $key, string $value ): bool {
					$this->meta[ $kind ][ $id ][ $key ] = $value;
					return true;
				},
			)
		);
		WP_Mock::userFunction(
			'delete_metadata',
			array(
				'return' => function ( string $kind, int $id, string $key ): bool {
					unset( $this->meta[ $kind ][ $id ][ $key ] );
					return true;
				},
			)
		);
		WP_Mock::passthruFunction( 'wp_slash' );
		WP_Mock::userFunction(
			'wp_json_encode',
			array(
				// phpcs:ignore WordPress.WP.AlternativeFunctions.json_encode_json_encode -- wp_json_encode() itself is mocked.
				'return' => static fn( $value ): string|false => json_encode( $value ),
			)
		);
		WP_Mock::userFunction(
			'as_get_scheduled_actions',
			array(
				'return' => array(),
			)
		);
		WP_Mock::userFunction(
			'as_enqueue_async_action',
			array(
				'return' => 1,
			)
		);
	}

	/**
	 * Post fields the writer reads while copying a product.
	 *
	 * @param string $title   Title.
	 * @param string $excerpt Excerpt.
	 * @return array<string, mixed>
	 */
	private function post_fields( string $title, string $excerpt ): array {
		return array(
			'post_type'      => 'product',
			'post_status'    => 'publish',
			'post_title'     => $title,
			'post_excerpt'   => $excerpt,
			'post_content'   => '',
			'post_author'    => 1,
			'post_parent'    => 0,
			'menu_order'     => 0,
			'comment_status' => 'open',
			'ping_status'    => 'closed',
			'post_password'  => '',
		);
	}

	/**
	 * A client that either marks the segment or refuses it.
	 *
	 * @param bool $fail Whether translate() fails.
	 */
	private function client( bool $fail ): Client {
		return new class( $fail ) implements Client {

			/**
			 * Sets up the client.
			 *
			 * @param bool $fail Whether translate() fails.
			 */
			public function __construct( private readonly bool $fail ) {}

			/**
			 * The key is present.
			 */
			public function available(): bool {
				return true;
			}

			/**
			 * Marks each segment, or refuses.
			 *
			 * @param array<int, string> $texts    English texts.
			 * @param string             $feedback Earlier reasons.
			 * @return list<string>
			 * @throws TranslationFailed When this client is the failing one.
			 */
			public function translate( array $texts, string $feedback = '' ): array {
				unset( $feedback );
				if ( $this->fail ) {
					throw new TranslationFailed( 'stand-in refused', false );
				}
				return array_map( static fn( string $text ): string => '[de] ' . $text, array_values( $texts ) );
			}
		};
	}

	/**
	 * The translator under test.
	 *
	 * @param Client $client The machine translator.
	 * @param Twins  $twins  Records German writes.
	 */
	private function translator( Client $client, Twins $twins ): Translator {
		$languages = new Languages();
		$tokenizer = new HtmlTokenizer();
		return new Translator(
			$languages,
			new Planner( new Segmenter( $tokenizer ), new Aligner() ),
			new Fields(),
			new State(),
			$client,
			new Validator( Rules::load( dirname( __DIR__, 4 ) . '/data' ) ),
			$twins,
			new LinkLocalizer( $languages, $tokenizer )
		);
	}

	/**
	 * Jobs over the same translator, so a later save uses the stored failure.
	 *
	 * @param Client $client The machine translator.
	 */
	private function jobs( Client $client ): Jobs {
		$languages = new Languages();
		$tokenizer = new HtmlTokenizer();
		$twins     = new Twins( $languages, new LinkLocalizer( $languages, $tokenizer ), new Projection( $languages ) );
		return new Jobs( $languages, $this->translator( $client, $twins ), $twins, new State() );
	}
}
