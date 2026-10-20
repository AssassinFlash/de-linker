<?php
/**
 * The translate command reports every failed object.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Unit\Cli;

use Linker\I18n\Cli\Command;
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
use ReflectionClass;
use WP_CLI;
use WP_CLI\ExitException;
use WP_Mock;
use WP_Mock\Tools\TestCase;

require_once dirname( __DIR__, 2 ) . '/Doubles/wp-cli.php';

/**
 * Exit 1 carries the object and the reason for each failure.
 *
 * @covers \Linker\I18n\Cli\Command
 */
final class TranslateCommandTest extends TestCase {

	private const EXCERPT = '<p>First sentence stays. Second sentence stays.</p>';

	private const CONTENT = '<p>Only one sentence here.</p>';

	/**
	 * Metadata written during the test, keyed by kind, id and meta key.
	 *
	 * @var array<string, array<int, array<string, string>>>
	 */
	private array $meta = array();

	/**
	 * Two failures exit 1 and name both reasons.
	 */
	public function test_failing_objects_exit_with_every_reason(): void {
		$this->wordpress();
		$stderr = fopen( 'php://memory', 'w+' ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_fopen -- a memory stream standing in for stderr; unit tests have no WP_Filesystem.
		if ( ! is_resource( $stderr ) ) {
			$this->fail( 'Could not capture stderr.' );
		}
		WP_CLI::$stderr = $stderr;

		$exit = null;
		ob_start();
		try {
			$this->command()->translate( array( '8', '5' ), array( 'now' => '' ) );
		} catch ( ExitException $caught ) {
			$exit = $caught;
		}
		$stdout = (string) ob_get_clean();
		rewind( $stderr );
		$error = stream_get_contents( $stderr );
		fclose( $stderr ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_fclose -- closes the memory stream opened above.
		WP_CLI::$stderr = null;

		if ( ! $exit instanceof ExitException ) {
			$this->fail( 'A failing object exits 1.' );
		}
		if ( ! is_string( $error ) ) {
			$this->fail( 'stderr was not captured.' );
		}
		$this->assertSame( 1, $exit->getCode() );
		$this->assertSame(
			"Error: 2 of 2 objects failed; previous German retained. post 8: structure_mismatch; post 5: failed: stand-in refused\n",
			$error
		);
		$this->assertSame( "post 8: structure_mismatch\npost 5: failed: stand-in refused\n", $stdout );
		$this->assertSame( State::STRUCTURE_MISMATCH, $this->meta['post'][8][ State::STATUS ] );
		$this->assertSame( State::FAILED, $this->meta['post'][5][ State::STATUS ] );
		$this->assertSame( 'stand-in refused', $this->meta['post'][5][ State::NOTE ] );
	}

	/**
	 * The command with the translator under test.
	 */
	private function command(): Command {
		$class   = new ReflectionClass( Command::class );
		$command = $class->newInstanceWithoutConstructor();
		$class->getProperty( 'translator' )->setValue( $command, $this->translator() );
		$class->getProperty( 'state' )->setValue( $command, new State() );
		return $command;
	}

	/**
	 * English products: 8 cannot be aligned, 5 asks the translator and is refused.
	 */
	private function wordpress(): void {
		$segmenter = new Segmenter( new HtmlTokenizer() );
		$fields    = static function ( string $title, string $excerpt, string $content ): array {
			return array(
				'post_type'      => 'product',
				'post_status'    => 'publish',
				'post_title'     => $title,
				'post_excerpt'   => $excerpt,
				'post_content'   => $content,
				'post_author'    => 1,
				'post_parent'    => 0,
				'menu_order'     => 0,
				'comment_status' => 'open',
				'ping_status'    => 'closed',
				'post_password'  => '',
			);
		};
		PolylangDouble::mock(
			array(
				5 => 'en',
				6 => 'de',
				8 => 'en',
				9 => 'de',
			),
			array(
				5 => 6,
				8 => 9,
			),
			array(),
			array(),
			'en',
			array(),
			array(
				5 => $fields( 'Workshop meter C406', self::EXCERPT, '' ),
				6 => $fields( 'Werkstattzähler', '<p>Erster Satz bleibt. Zweiter Satz bleibt.</p>', '' ),
				8 => $fields( 'Same title', '', self::CONTENT ),
				9 => $fields( 'Gleicher Titel', '', '<p>Nur ein Satz hier.</p>' ),
			)
		);
		$this->meta = array(
			'post' => array(
				6 => array(
					State::SOURCE_HASH => 'stale',
					State::UNITS       => (string) json_encode( // phpcs:ignore WordPress.WP.AlternativeFunctions.json_encode_json_encode -- stored before wp_json_encode() is mocked.
						array(
							'post_title'   => array(
								'src'      => $segmenter->text( 'Workshop meter' )->hashes(),
								'out'      => $segmenter->text( 'Werkstattzähler' )->hashes(),
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
				9 => array(
					State::SOURCE_HASH => 'stale',
					State::UNITS       => (string) json_encode( // phpcs:ignore WordPress.WP.AlternativeFunctions.json_encode_json_encode -- stored before wp_json_encode() is mocked.
						array(
							'post_title'   => array(
								'src'      => $segmenter->text( 'Same title' )->hashes(),
								'out'      => $segmenter->text( 'Gleicher Titel' )->hashes(),
								'conflict' => false,
							),
							'post_content' => array(
								'src'      => array( 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb' ),
								'out'      => array( 'cccccccccccccccccccccccccccccccccccccccc', 'dddddddddddddddddddddddddddddddddddddddd' ),
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
	}

	/**
	 * A translator whose client refuses every request.
	 */
	private function translator(): Translator {
		$languages = new Languages();
		$tokenizer = new HtmlTokenizer();
		return new Translator(
			$languages,
			new Planner( new Segmenter( $tokenizer ), new Aligner() ),
			new Fields(),
			new State(),
			$this->client(),
			new Validator( Rules::load( dirname( __DIR__, 4 ) . '/data' ) ),
			new Twins( $languages, new LinkLocalizer( $languages, $tokenizer ), new Projection( $languages ) ),
			new LinkLocalizer( $languages, $tokenizer )
		);
	}

	/**
	 * A client that refuses every batch.
	 */
	private function client(): Client {
		return new class() implements Client {

			/**
			 * The key is present.
			 */
			public function available(): bool {
				return true;
			}

			/**
			 * Refuses the batch.
			 *
			 * @param array<int, string> $texts    English texts.
			 * @param string             $feedback Earlier reasons.
			 * @return list<string>
			 * @throws TranslationFailed This client always refuses.
			 */
			public function translate( array $texts, string $feedback = '' ): array {
				unset( $feedback );
				if ( array() !== $texts ) {
					throw new TranslationFailed( 'stand-in refused', false );
				}
				return array();
			}
		};
	}
}
