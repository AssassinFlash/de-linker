<?php
/**
 * Tests for the translation jobs.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Unit;

use Linker\I18n\Jobs;
use Linker\I18n\Languages;
use Linker\I18n\LinkLocalizer;
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
use Mockery;
use WP_Mock;
use WP_Mock\Tools\TestCase;

// WordPress's own minute, the value of MINUTE_IN_SECONDS
// (wp-includes/functions.php); WP_Mock defines no constants, and Jobs
// multiplies the retry minutes with it.
if ( ! defined( 'MINUTE_IN_SECONDS' ) ) {
	// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedConstantFound -- WordPress's own constant.
	define( 'MINUTE_IN_SECONDS', 60 );
}

/**
 * Tests for Jobs.
 *
 * @covers \Linker\I18n\Jobs
 */
final class JobsTest extends TestCase {

	/**
	 * The minutes WordPress's MINUTE_IN_SECONDS counts (wp-includes/functions.php);
	 * WP_Mock defines no constants.
	 */
	private const MINUTE = 60;

	/**
	 * The jobs of the test, over a real Translator whose client is a stub.
	 *
	 * @param bool $available Whether the stub client has its key.
	 * @param bool $transient Whether the stub client fails for a passing reason.
	 */
	private function jobs( bool $available, bool $transient ): Jobs {
		$data       = dirname( __DIR__, 3 ) . '/data';
		$languages  = new Languages();
		$tokenizer  = new HtmlTokenizer();
		$translator = new Translator(
			$languages,
			new Planner( new Segmenter( $tokenizer ), new Aligner() ),
			new Fields(),
			new State(),
			new class( $available, $transient ) implements Client {

				/**
				 * Sets up the stub.
				 *
				 * @param bool $available Whether it has its key.
				 * @param bool $transient Whether it fails for a passing reason.
				 */
				public function __construct(
					private readonly bool $available,
					private readonly bool $transient,
				) {}

				/**
				 * Whether the translator can be called.
				 */
				public function available(): bool {
					return $this->available;
				}

				/**
				 * Fails the way the test wants.
				 *
				 * @param array<int, string> $texts    English texts.
				 * @param string             $feedback Earlier reasons.
				 * @return list<string>
				 * @throws TranslationFailed Always.
				 */
				public function translate( array $texts, string $feedback = '' ): array {
					if ( $this->transient || $this->available ) {
						// phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- test text, never shown.
						throw new TranslationFailed( $this->transient ? 'DeepSeek unreachable: stand-in down' : 'translation rejected', $this->transient );
					}
					return array();
				}
			},
			new Validator( Rules::load( $data ) ),
			new Twins( $languages, new LinkLocalizer( $languages, $tokenizer ), new Projection( $languages ) )
		);
		return new Jobs( $languages, $translator, new Twins( $languages, new LinkLocalizer( $languages, $tokenizer ), new Projection( $languages ) ), new State() );
	}

	/**
	 * The WordPress functions a failing translation run touches. time() is
	 * PHP's own and stays real, so the scheduled moment is matched as a window.
	 */
	private function wordpress(): void {
		// @phpstan-ignore-next-line WP_Mock's responder types are not in its stubs.
		WP_Mock::onFilter( 'linker_i18n_translatable_meta' )
			->withAnyArgs()
			->reply( Fields::SEO_META );
		WP_Mock::userFunction( 'get_post_meta', array( 'return' => '' ) );
		WP_Mock::userFunction( 'get_metadata', array( 'return' => '' ) );
		WP_Mock::userFunction( 'update_metadata', array( 'return' => true ) );
		WP_Mock::userFunction( 'delete_metadata', array( 'return' => true ) );
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
	 * An English post with text to translate.
	 */
	private function english_post(): void {
		PolylangDouble::mock(
			array( 5 => 'en' ),
			array(),
			array(),
			array(),
			'en',
			array(),
			array(
				5 => array(
					'post_type'    => 'product',
					'post_title'   => 'Power meter',
					'post_excerpt' => 'A meter for the grid connection.',
					'post_content' => '<p>A three-phase power meter with a display.</p>',
				),
			)
		);
	}

	/**
	 * Every entry point refuses present-owned templates, including stale jobs.
	 *
	 * @dataProvider present_types
	 * @param string $type LiveCanvas post type.
	 */
	public function test_present_templates_are_never_machine_translated( string $type ): void {
		PolylangDouble::mock(
			array(
				17 => 'en',
				18 => 'de',
			),
			array( 17 => 18 ),
			array(),
			array(),
			'en',
			array( $type => true ),
			array(
				17 => array(
					'post_type' => $type,
					'post_name' => 'footer',
				),
				18 => array( 'post_type' => $type ),
			)
		);
		WP_Mock::userFunction( 'wp_is_post_revision', array( 'return' => false ) );
		WP_Mock::userFunction( 'wp_is_post_autosave', array( 'return' => false ) );
		WP_Mock::userFunction( 'as_enqueue_async_action', array( 'times' => 0 ) );
		WP_Mock::userFunction( 'as_schedule_single_action', array( 'times' => 0 ) );
		WP_Mock::userFunction( 'update_metadata', array( 'times' => 0 ) );
		WP_Mock::userFunction( 'wp_update_post', array( 'times' => 0 ) );
		$jobs = $this->jobs( true, false );
		$jobs->post_saved(
			17,
			PolylangDouble::post(
				17,
				array(
					'post_type'   => $type,
					'post_status' => 'publish',
				)
			)
		);
		$this->assertFalse( $jobs->queue( 'post', 17, true ) );
		$jobs->run( 'post', 17, true );
		$jobs->run( 'post', 17, false, 3 );
		$this->assertSame( array(), PolylangDouble::$saved_post_translations );
	}

	/**
	 * The two repository-owned types, regardless of their slugs.
	 *
	 * @return array<string, array{string}>
	 */
	public function present_types(): array {
		return array(
			'partial' => array( 'lc_partial' ),
			'dynamic' => array( 'lc_dynamic_template' ),
		);
	}

	/**
	 * A failure for a passing reason is scheduled again with the next
	 * attempt, after the retry minutes (15, Jobs::RETRY_MINUTES, private).
	 */
	public function test_a_transient_failure_is_scheduled_again_with_the_next_attempt(): void {
		$this->english_post();
		$this->wordpress();
		WP_Mock::userFunction(
			'as_schedule_single_action',
			array(
				'times'  => 1,
				'args'   => array(
					Mockery::on( static fn( int $when ): bool => $when > time() && $when <= time() + 15 * self::MINUTE + 5 ),
					Jobs::HOOK,
					array( 'post', 5, false, 2 ),
					Jobs::GROUP,
				),
				'return' => 7,
			)
		);

		$this->jobs( true, true )->run( 'post', 5 );

		$this->assertConditionsMet();
	}

	/**
	 * The last attempt is not scheduled again.
	 */
	public function test_the_last_attempt_is_not_scheduled_again(): void {
		$this->english_post();
		$this->wordpress();
		WP_Mock::userFunction( 'as_schedule_single_action', array( 'times' => 0 ) );

		$this->jobs( true, true )->run( 'post', 5, false, 3 );

		$this->assertConditionsMet();
	}

		/**
		 * Saving the English header partial does not queue a translation.
		 * present writes the curated German export itself; a queued job would
		 * replace kopfzeile with a machine translation of header.
		 */
	public function test_saving_the_english_header_partial_does_not_queue_a_translation(): void {
		PolylangDouble::mock(
			array( 17 => 'en' ),
			array( 17 => 6919 ),
			array(),
			array(),
			'en',
			array( 'lc_partial' => true ),
			array(
				17 => array(
					'post_type'   => 'lc_partial',
					'post_status' => 'publish',
					'post_name'   => 'header',
					'post_title'  => 'Header',
				),
			)
		);
		WP_Mock::userFunction( 'wp_is_post_revision', array( 'return' => false ) );
		WP_Mock::userFunction( 'wp_is_post_autosave', array( 'return' => false ) );
		WP_Mock::userFunction( 'as_enqueue_async_action', array( 'times' => 0 ) );

		$this->jobs( true, false )->post_saved(
			17,
			PolylangDouble::post(
				17,
				array(
					'post_type'   => 'lc_partial',
					'post_status' => 'publish',
					'post_name'   => 'header',
				)
			)
		);

		$this->assertConditionsMet();
	}

		/**
		 * Saving the German twin does not queue its English source either.
		 * The twin's slug is kopfzeile; the exemption follows the Polylang pair,
		 * not a same-slug lookup.
		 */
	public function test_saving_the_german_header_twin_does_not_queue_its_english_source(): void {
		PolylangDouble::mock(
			array(
				17   => 'en',
				6919 => 'de',
			),
			array( 17 => 6919 ),
			array(),
			array(),
			'de',
			array( 'lc_partial' => true ),
			array(
				17   => array(
					'post_type'   => 'lc_partial',
					'post_status' => 'publish',
					'post_name'   => 'header',
				),
				6919 => array(
					'post_type'   => 'lc_partial',
					'post_status' => 'publish',
					'post_name'   => 'kopfzeile',
				),
			)
		);
		WP_Mock::userFunction( 'wp_is_post_revision', array( 'return' => false ) );
		WP_Mock::userFunction( 'wp_is_post_autosave', array( 'return' => false ) );
		WP_Mock::userFunction( 'as_enqueue_async_action', array( 'times' => 0 ) );

		$this->jobs( true, false )->post_saved(
			6919,
			PolylangDouble::post(
				6919,
				array(
					'post_type'   => 'lc_partial',
					'post_status' => 'publish',
					'post_name'   => 'kopfzeile',
				)
			)
		);

		$this->assertConditionsMet();
	}

		/**
		 * A failure for a lasting reason (no key, a rejected translation) is
		 * never scheduled again.
		 */
	public function test_a_lasting_failure_is_not_scheduled_again(): void {
		$this->english_post();
		$this->wordpress();
		WP_Mock::userFunction( 'as_schedule_single_action', array( 'times' => 0 ) );

		$this->jobs( false, false )->run( 'post', 5 );

		$this->assertConditionsMet();
	}
}
