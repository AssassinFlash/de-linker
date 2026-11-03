<?php
/**
 * Owner-scoped staged project briefs keep customer text private and conflict-safe.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Planner\Principal;
use Linker\Tools\Planner\ProjectBriefSource;
use WP_Error;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Staging, readback, revision conflicts and guest-to-account transfer.
 *
 * @covers \Linker\Tools\Planner\ProjectBriefSource
 */
final class ProjectBriefSourceTest extends TestCase {

	/** Replace the option store with an in-memory byte-exact double. */
	public function setUp(): void {
		parent::setUp();
		$options = new class() {
			/**
			 * Options by name, as the direct database readback sees them.
			 *
			 * @var array<string,string>
			 */
			public array $values = array();
		};
		// A byte-exact sidecar store: get_option is authoritative for the
		// fallback path, so a stale cache cannot fake a successful readback.
		WP_Mock::userFunction(
			'get_option',
			array(
				'return' => static function ( string $name, mixed $fallback = false ) use ( $options ): mixed {
					return $options->values[ $name ] ?? $fallback;
				},
			)
		);
		WP_Mock::userFunction(
			'add_option',
			array(
				'return' => static function ( string $name, mixed $value ) use ( $options ): bool {
					if ( isset( $options->values[ $name ] ) ) {
						return false;
					}
					$options->values[ $name ] = (string) $value;
					return true;
				},
			)
		);
		WP_Mock::userFunction(
			'update_option',
			array(
				'return' => static function ( string $name, mixed $value ) use ( $options ): bool {
					$options->values[ $name ] = (string) $value;
					return true;
				},
			)
		);
		WP_Mock::userFunction( 'wp_json_encode' )->andReturnUsing(
			static fn ( mixed $value, int $flags = 0 ): string|false => json_encode( $value, $flags ) // phpcs:ignore WordPress.WP.AlternativeFunctions.json_encode_json_encode -- Native encoder double.
		);
		WP_Mock::userFunction(
			'wp_cache_delete',
			array( 'return' => true )
		);
		WP_Mock::userFunction(
			'is_wp_error',
			array( 'return' => static fn ( mixed $value ): bool => $value instanceof WP_Error )
		);
		WP_Mock::userFunction(
			'__',
			array( 'return' => static fn ( string $message ): string => $message )
		);
		WP_Mock::userFunction( 'get_current_blog_id', array( 'return' => 1 ) );
	}

	/** Guest subject in the shape the native identity produces. */
	private function guest(): string {
		return 'wp:1:guest:' . hash( 'sha256', 'guest-key' );
	}

	/**
	 * Verified account principal.
	 *
	 * @param int $id Account ID.
	 */
	private function user( int $id = 7 ): Principal {
		return new Principal( 'user', 'wp:1:user:' . $id );
	}

	/**
	 * Stage the same note for one principal.
	 *
	 * @param Principal   $principal Verified native owner.
	 * @param string      $text      Customer plain text.
	 * @param string|null $id        Existing brief ID, if any.
	 * @param string|null $revision  Expected revision, if any.
	 * @return array<string,mixed>|WP_Error Authoritative readback or refusal.
	 */
	private function stage( Principal $principal, string $text, ?string $id = null, ?string $revision = null ): array|WP_Error {
		$command = array(
			'schema_version' => 1,
			'source_path'    => '/for-installer/',
			'text'           => $text,
		);
		if ( null !== $id ) {
			$command['brief_id'] = $id;
		}
		if ( null !== $revision ) {
			$command['expected_revision'] = $revision;
		}
		return ( new ProjectBriefSource() )->stage( $principal, $command );
	}

	/** An exact note reaches the account-owned readback and a replay is idempotent. */
	public function test_staged_note_is_read_back_exactly_and_survives_an_unchanged_restage(): void {
		$staged = $this->stage( $this->user(), "SAJ H2-10K, -40 °C, 6000 W\nsecond line" );
		$this->assertNotInstanceOf( WP_Error::class, $staged );
		$this->assertSame( "SAJ H2-10K, -40 °C, 6000 W\nsecond line", $staged['text'] );
		$this->assertSame( '/for-installer/', $staged['source_path'] );
		$this->assertMatchesRegularExpression( '/\A[a-f0-9]{32}\z/', $staged['brief_id'] );
		$this->assertMatchesRegularExpression( '/\A[a-f0-9]{64}\z/', $staged['revision'] );

		$read = ( new ProjectBriefSource() )->read(
			$this->user(),
			array(
				'schema_version' => 1,
				'brief_id'       => $staged['brief_id'],
			)
		);
		$this->assertNotInstanceOf( WP_Error::class, $read );
		$this->assertSame( $staged['text'], $read['text'] );
		$this->assertSame( $staged['revision'], $read['revision'] );

		// Replaying the identical accepted note is not a conflict.
		$again = $this->stage( $this->user(), $staged['text'], $staged['brief_id'], $staged['revision'] );
		$this->assertNotInstanceOf( WP_Error::class, $again );
		$this->assertSame( $staged['revision'], $again['revision'] );
	}

	/** A late tab cannot replace a note another tab already published. */
	public function test_a_stale_revision_is_refused_instead_of_overwriting_a_newer_note(): void {
		$staged = $this->stage( $this->user(), 'first requirement' );
		$this->assertNotInstanceOf( WP_Error::class, $staged );

		$newer = $this->stage( $this->user(), 'second requirement', $staged['brief_id'], $staged['revision'] );
		$this->assertNotInstanceOf( WP_Error::class, $newer );
		$this->assertNotSame( $staged['revision'], $newer['revision'] );

		$stale = $this->stage( $this->user(), 'a late overwrite', $staged['brief_id'], $staged['revision'] );
		$this->assertInstanceOf( WP_Error::class, $stale );
		$this->assertSame( 'linker_planner_project_brief_conflict', $stale->get_error_code() );

		$kept = ( new ProjectBriefSource() )->read(
			$this->user(),
			array(
				'schema_version' => 1,
				'brief_id'       => $staged['brief_id'],
			)
		);
		$this->assertNotInstanceOf( WP_Error::class, $kept );
		$this->assertSame( 'second requirement', $kept['text'] );
	}

	/** A brief ID is not authority to read another principal's text. */
	public function test_another_principal_cannot_read_a_staged_note(): void {
		$staged = $this->stage( $this->user( 7 ), 'private requirement' );
		$this->assertNotInstanceOf( WP_Error::class, $staged );
		$other = ( new ProjectBriefSource() )->read(
			$this->user( 8 ),
			array(
				'schema_version' => 1,
				'brief_id'       => $staged['brief_id'],
			)
		);
		$this->assertInstanceOf( WP_Error::class, $other );
		$this->assertSame( 'linker_planner_project_brief_unavailable', $other->get_error_code() );
	}

	/** Blank, oversized, foreign and queried source paths never enter storage. */
	public function test_empty_oversized_and_foreign_source_notes_are_refused_before_storage(): void {
		$principal = $this->user();
		foreach (
			array(
				array(
					'text'        => '   ',
					'source_path' => '/for-installer/',
				),
				array(
					'text'        => str_repeat( 'x', ProjectBriefSource::MAX_TEXT_LENGTH + 1 ),
					'source_path' => '/for-installer/',
				),
				array(
					'text'        => 'note',
					'source_path' => 'https://evil.example/',
				),
				array(
					'text'        => 'note',
					'source_path' => '//evil.example/',
				),
				array(
					'text'        => 'note',
					'source_path' => '/for-installer/?raw=text',
				),
			) as $case
		) {
			$result = ( new ProjectBriefSource() )->stage(
				$principal,
				array(
					'schema_version' => 1,
					'source_path'    => $case['source_path'],
					'text'           => $case['text'],
				)
			);
			$this->assertInstanceOf( WP_Error::class, $result );
			$this->assertSame( 'linker_planner_project_brief_input', $result->get_error_code() );
		}
		// Unknown keys are refused rather than silently ignored.
		$extra = ( new ProjectBriefSource() )->stage(
			$principal,
			array(
				'schema_version' => 1,
				'source_path'    => '/for-installer/',
				'text'           => 'note',
				'raw_url'        => 'https://evil.example/',
			)
		);
		$this->assertInstanceOf( WP_Error::class, $extra );
	}

	/** Two projects coexist without one note replacing the other. */
	public function test_independent_projects_keep_separate_notes(): void {
		$first  = $this->stage( $this->user(), 'first project note' );
		$second = $this->stage( $this->user(), 'second project note' );
		$this->assertNotInstanceOf( WP_Error::class, $first );
		$this->assertNotInstanceOf( WP_Error::class, $second );
		$this->assertNotSame( $first['brief_id'], $second['brief_id'] );

		$read        = static function ( string $id ): array|WP_Error {
			return ( new ProjectBriefSource() )->read(
				new Principal( 'user', 'wp:1:user:7' ),
				array(
					'schema_version' => 1,
					'brief_id'       => $id,
				)
			);
		};
		$first_read  = $read( $first['brief_id'] );
		$second_read = $read( $second['brief_id'] );
		$this->assertIsArray( $first_read );
		$this->assertIsArray( $second_read );
		$this->assertSame( 'first project note', $first_read['text'] );
		$this->assertSame( 'second project note', $second_read['text'] );
	}

	/** A verified guest claim moves the note and clears the guest record. */
	public function test_a_verified_guest_claim_transfers_only_records_the_account_read_back(): void {
		$guest  = $this->guest();
		$source = new ProjectBriefSource();
		$staged = $source->stage(
			new Principal( 'guest', $guest ),
			array(
				'schema_version' => 1,
				'source_path'    => '/for-installer/',
				'text'           => 'guest typed this requirement',
			)
		);
		$this->assertNotInstanceOf( WP_Error::class, $staged );

		$this->assertTrue( $source->claim( $guest, 7 ) );
		$claimed = $source->read(
			$this->user( 7 ),
			array(
				'schema_version' => 1,
				'brief_id'       => $staged['brief_id'],
			)
		);
		$this->assertNotInstanceOf( WP_Error::class, $claimed );
		$this->assertSame( 'guest typed this requirement', $claimed['text'] );

		// The consumed guest record is gone, so the former guest cannot read it.
		$orphaned = $source->read(
			new Principal( 'guest', $guest ),
			array(
				'schema_version' => 1,
				'brief_id'       => $staged['brief_id'],
			)
		);
		$this->assertInstanceOf( WP_Error::class, $orphaned );
	}

	/** Claim refuses a subject that is not a verified native guest and a missing user. */
	public function test_claim_of_an_unknown_guest_subject_is_refused(): void {
		$source = new ProjectBriefSource();
		$this->assertFalse( $source->claim( 'not-a-native-subject', 7 ) );
		$this->assertFalse( $source->claim( $this->guest(), 0 ) );
	}
}
