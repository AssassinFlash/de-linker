<?php
/**
 * The conversation summary an inquiry carries (#244).
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Genie\Conversations;
use Linker\Tools\Genie\InquirySummary;
use Linker\Tools\Genie\Thread;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * The service's checked answer, its cache, and the rule-based fallback.
 *
 * @covers \Linker\Tools\Genie\InquirySummary
 */
final class InquirySummaryTest extends TestCase {

	/**
	 * The site's language and the product titles.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::userFunction( 'determine_locale', array( 'return' => 'en_US' ) );
		WP_Mock::userFunction(
			'get_option',
			array(
				'args'   => array( 'linker_genie_url' ),
				'return' => 'http://genie.test',
			)
		);
		WP_Mock::userFunction( 'get_the_title', array( 'return' => 'SAJ H2-10K-T3' ) );
		WP_Mock::userFunction( 'wp_strip_all_tags', array( 'return_arg' => 0 ) );
		WP_Mock::userFunction( 'wp_json_encode', array( 'return' => '{}' ) );
	}

	/**
	 * A thread with the messages a transcript returns.
	 *
	 * @param list<array<string, mixed>> $messages The transcript.
	 */
	private static function thread( array $messages ): Thread {
		return new class( $messages ) extends Thread {
			/**
			 * The fixed transcript.
			 *
			 * @var list<array<string, mixed>>
			 */
			private array $fixed;

			/**
			 * Sets the transcript.
			 *
			 * @param list<array<string, mixed>> $messages Messages.
			 */
			public function __construct( array $messages ) {
				$this->fixed = $messages;
			}

			/**
			 * The fixed transcript.
			 *
			 * @param int $conversation Conversation id.
			 * @return list<array<string, mixed>>
			 */
			public function transcript( int $conversation ): array {
				return $this->fixed;
			}
		};
	}

	/**
	 * A conversation object that never reads the cookie.
	 */
	private static function conversations(): Conversations {
		return new class() extends Conversations {
			/**
			 * No cookie in these tests.
			 */
			public function current_id(): int {
				return 0;
			}
		};
	}

	/**
	 * The model's answer is stored as it arrives, with the service's bounds.
	 */
	public function test_the_checked_answer_is_used_and_cached(): void {
		$calls = 0;
		$fetch = static function ( string $url, array $body ) use ( &$calls ): array { // phpcs:ignore Generic.CodeAnalysis.UnusedFunctionParameter.FoundAfterLastUsed -- the seam's signature.
			unset( $url, $body );
			++$calls;
			return array(
				'summary'    => 'A 10 kW hybrid inverter with a 10 kWh battery.',
				'quantities' => array(
					array(
						'product_id' => 4107,
						'quantity'   => 2,
					),
					array(
						'product_id' => 0,
						'quantity'   => 1,
					),
				),
				'conditions' => array( 'Three-phase connection', '' ),
				'note'       => 'Roof is ready.',
			);
		};
		WP_Mock::userFunction( 'get_transient', array( 'return' => false ) );
		WP_Mock::userFunction(
			'set_transient',
			array(
				'times'  => 1,
				'return' => true,
			)
		);

		$summary = ( new InquirySummary(
			self::conversations(),
			self::thread(
				array(
					array(
						'role'     => 'user',
						'content'  => 'I need 2 inverters.',
						'products' => array(),
					),
				)
			),
			$fetch
		) )->answer( null, 5 ) ?? array();
		$this->assertSame( 'model', $summary['source'] );
		$this->assertNull( $summary['reason'] );
		$this->assertSame( 'A 10 kW hybrid inverter with a 10 kWh battery.', $summary['summary'] );
		$this->assertSame(
			array(
				array(
					'product_id' => 4107,
					'quantity'   => 2,
				),
			),
			$summary['quantities']
		);
		$this->assertSame( array( 'Three-phase connection' ), $summary['conditions'] );
		$this->assertSame( 'Roof is ready.', $summary['note'] );
		$this->assertSame( 1, $calls );
	}


	/**
	 * The model's empty note does not leave the form blank: A7 starts the
	 * message from the customer's last sentence.
	 */
	public function test_a_model_summary_without_a_note_uses_the_last_message(): void {
		WP_Mock::userFunction( 'get_transient', array( 'return' => false ) );
		WP_Mock::userFunction( 'set_transient', array( 'return' => true ) );
		$summary = ( new InquirySummary(
			self::conversations(),
			self::thread(
				array(
					array(
						'role'     => 'user',
						'content'  => 'Zwei Wechselrichter, Lieferung im Dezember.',
						'products' => array(),
					),
					array(
						'role'     => 'assistant',
						'content'  => 'Hier sind zwei Modelle.',
						'products' => array( 4107 ),
					),
				)
			),
			static fn (): array => array(
				'summary'    => 'Zwei Wechselrichter fuer Dezember.',
				'quantities' => array(),
				'conditions' => array( 'Lieferung im Dezember' ),
				'note'       => '',
			)
		) )->answer( null, 5 );

		$this->assertSame( 'model', $summary['source'] );
		$this->assertSame( 'Zwei Wechselrichter, Lieferung im Dezember.', $summary['note'] );
	}

	/**
	 * An unreachable service leaves the customer's own sentences, newest first.
	 */
	public function test_an_unreachable_service_falls_back_to_the_customers_words(): void {
		WP_Mock::userFunction( 'get_transient', array( 'return' => false ) );
		WP_Mock::userFunction( 'set_transient', array( 'return' => true ) );

		$summary = ( new InquirySummary(
			self::conversations(),
			self::thread(
				array(
					array(
						'role'     => 'user',
						'content'  => 'Ten panels, please.',
						'products' => array(),
					),
					array(
						'role'     => 'assistant',
						'content'  => 'Here are two inverters.',
						'products' => array( 4107 ),
					),
					array(
						'role'     => 'user',
						'content'  => 'The roof faces south.',
						'products' => array(),
					),
				)
			),
			static fn (): \WP_Error => new \WP_Error( 'down', 'timeout' )
		) )->answer( null, 5 ) ?? array();
		$this->assertSame( 'rule', $summary['source'] );
		$this->assertSame( 'timeout', $summary['reason'] );
		$this->assertSame( 'The roof faces south. · Ten panels, please.', $summary['summary'] );
		$this->assertSame( 'The roof faces south.', $summary['note'] );
	}

	/**
	 * No conversation, no summary: the inquiry is sent unchanged.
	 */
	public function test_a_missing_conversation_answers_null(): void {
		$summary = new InquirySummary( self::conversations(), self::thread( array() ) );
		$this->assertNull( $summary->answer( null, 0 ) );
	}

	/**
	 * A refused answer (422's empty body) falls back by rule.
	 */
	public function test_a_refused_answer_falls_back(): void {
		WP_Mock::userFunction( 'get_transient', array( 'return' => false ) );
		WP_Mock::userFunction( 'set_transient', array( 'return' => true ) );

		$summary = ( new InquirySummary(
			self::conversations(),
			self::thread(
				array(
					array(
						'role'     => 'user',
						'content'  => 'Two of them.',
						'products' => array(),
					),
				)
			),
			static fn (): \WP_Error => new \WP_Error( 'linker_genie_summary', 'HTTP 422' )
		) )->answer( null, 5 ) ?? array();
		$this->assertSame( 'rule', $summary['source'] );
		$this->assertSame( 'HTTP 422', $summary['reason'] );
		$this->assertSame( 'Two of them.', $summary['summary'] );
	}
}
