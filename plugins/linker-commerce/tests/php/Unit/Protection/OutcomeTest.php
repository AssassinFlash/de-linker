<?php
/**
 * The outcome table must cover every code the two browser form doors can return.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Protection;

use Linker\Commerce\Protection\Outcome;
use Linker\Commerce\Tests\TestCase;

/**
 * The codes are read from the emitting sources, never repeated here: a new
 * native refusal fails this test until someone decides what it proved.
 *
 * @covers \Linker\Commerce\Protection\Outcome
 */
final class OutcomeTest extends TestCase {
	/**
	 * The contact and inquiry doors, and only the members an inquiry passes on
	 * its way to a result: field validation, preflight, admission, the review
	 * store's write, and the journal. Each named member is asserted to exist, so
	 * a rename fails here instead of silently shrinking the proof. Members that
	 * answer the privacy tools and the staff dashboard are not on this path.
	 */
	private const DOOR_SOURCES = array(
		'includes/Contact/Handler.php'             => array(),
		'includes/Contact/Submission.php'          => array(),
		'includes/Inquiry/Handler.php'             => array(),
		'includes/Inquiry/Sender.php'              => array(),
		'includes/Planning/Context.php'            => array(),
		'includes/Protection/Admission.php'        => array(),
		'includes/Protection/Business.php'         => array(),
		'includes/Protection/BusinessCapacity.php' => array( 'preflight', 'prepare', 'finalize', 'verify', 'problem' ),
		'includes/Protection/Fingerprint.php'      => array(),
		'includes/Protection/Identity.php'         => array(),
		'includes/Protection/Intake.php'           => array( 'verified', 'run', 'begin', 'write', 'problem', 'full', 'grouped' ),
		'includes/Protection/IntakeStore.php'      => array( 'edit', 'edit_native', 'save', 'read' ),
		'includes/Protection/Ledger.php'           => array(),
	);

	/**
	 * Fixed reasons of the shared journal's own error helper. A reason that is
	 * composed at runtime (`'already_' . $status`) does not match; it is expanded
	 * from the receipt status vocabulary instead.
	 */
	private const LEDGER_ERROR = '/(?<!\w)self::error\(\s*\'([a-z_]+)\'\s*[,)]/';

	/** Fixed reasons of Admission's own refusal helper. */
	private const ADMISSION_FAILURE = '/(?<!\w)self::failure\(\s*\'([a-z_]+)\'\s*[,)]/';

	/**
	 * A native code the check actually builds. Claimed members are excluded:
	 * `new WP_Error( $code, … )` re-wraps one the scan already read at its origin.
	 */
	private const NATIVE_CODE = '/new WP_Error\(\s*\'([a-z0-9_]+)\'\s*[,)]/';

	/**
	 * The codes of the two doors, as their sources emit them.
	 *
	 * @return array<string, list<string>> Code to emitting files.
	 */
	private function door_codes(): array {
		$root  = dirname( __DIR__, 4 );
		$codes = array();
		foreach ( self::DOOR_SOURCES as $relative => $members ) {
			$path = $root . '/' . $relative;
			$this->assertFileExists( $path, 'The outcome scan lost an emitter it was written against.' );
			$source = (string) file_get_contents( $path );
			$source = array() === $members ? $source : $this->members( $source, $members, $relative );
			foreach ( $this->codes_matching( self::NATIVE_CODE, $source ) as $code ) {
				$codes[ $code ][] = $relative;
			}
			foreach ( array_merge( $this->codes_matching( self::LEDGER_ERROR, $source ), $this->codes_matching( self::ADMISSION_FAILURE, $source ) ) as $reason ) {
				$codes[ 'linker_admission_' . $reason ][] = $relative;
			}
		}
		foreach ( $this->ledger_already_codes( $root ) as $code ) {
			$codes[ $code ][] = 'includes/Protection/Ledger.php (already_<status>)';
		}
		return $codes;
	}

	/**
	 * Only the named members of one file, so a member that answers another caller
	 * cannot contribute a code the doors never return. Every name must exist.
	 *
	 * @param string             $source  File contents.
	 * @param array<int, string> $members Member names on the door's path.
	 * @param string             $relative File name, for the failure message.
	 */
	private function members( string $source, array $members, string $relative ): string {
		$kept = '';
		foreach ( $members as $member ) {
			$this->assertSame(
				1,
				preg_match_all( '/\n\t(?:public|private|protected)(?: static)? function ' . preg_quote( $member, '/' ) . '\(/', $source, $starts, PREG_OFFSET_CAPTURE ),
				$relative . ' no longer declares ' . $member . '(); the door scan would silently skip its codes.'
			);
			$start = $starts[0][0][1];
			$end   = preg_match( '/\n\t(?:public|private|protected)(?: static)? function /', $source, $next, PREG_OFFSET_CAPTURE, $start + 1 )
				? $next[0][1]
				: strlen( $source );
			$kept .= substr( $source, $start, $end - $start );
		}
		return $kept;
	}

	/**
	 * Ledger refuses a repeated transition with `already_<current status>`. The
	 * vocabulary is read from its own state validator, so a new receipt status
	 * requires a partition row.
	 *
	 * @param string $root Plugin root.
	 * @return list<string>
	 */
	private function ledger_already_codes( string $root ): array {
		$source = (string) file_get_contents( $root . '/includes/Protection/Ledger.php' );
		$this->assertMatchesRegularExpression(
			'/\'already_\' \. \$status/',
			$source,
			'Ledger no longer composes repeated-transition refusals; this scan needs revisiting.'
		);
		$this->assertSame(
			1,
			preg_match( '/\$receipt\[\'status\'\] \?\? \'\', array\(([^)]+)\)/', $source, $vocabulary ),
			'The receipt status vocabulary moved; the already_<status> expansion cannot be proven.'
		);
		$vocabulary = $vocabulary[1] ?? '';
		preg_match_all( '/\'([a-z_]+)\'/', $vocabulary, $statuses );
		$this->assertNotEmpty( $statuses[1], 'The receipt status vocabulary is empty.' );
		return array_map( static fn ( string $status ): string => 'linker_admission_already_' . $status, $statuses[1] );
	}

	/**
	 * Every literal `linker_*` code emitted anywhere in the plugin, for the
	 * dead-row half of the check.
	 *
	 * @return list<string>
	 */
	private function all_emitted_codes(): array {
		$root  = dirname( __DIR__, 4 );
		$files = new \RecursiveIteratorIterator(
			new \RecursiveDirectoryIterator( $root . '/includes', \FilesystemIterator::SKIP_DOTS )
		);
		$codes = array();
		foreach ( $files as $file ) {
			if ( $file instanceof \SplFileInfo && 'php' === $file->getExtension() ) {
				array_push( $codes, ...$this->codes_matching( self::NATIVE_CODE, (string) file_get_contents( $file->getPathname() ) ) );
			}
		}
		foreach ( array_keys( $this->door_codes() ) as $code ) {
			$codes[] = $code;
		}
		return array_values( array_unique( $codes ) );
	}

	/**
	 * The contact form's own states; a partition may only name one of them or
	 * the refusal would render no sentence at all. The `default` arm renders
	 * nothing, so a partition that named it would be silent.
	 *
	 * @return list<string>
	 */
	private function rendered_states(): array {
		$source = (string) file_get_contents( dirname( __DIR__, 4 ) . '/includes/Contact/Form.php' );
		$this->assertNotSame(
			0,
			preg_match_all( '/\n\t\t\t\'([a-z_]+)\'\s+=> \$this->notice\(/', $source, $states ),
			'The contact form\'s state arms moved; the partition-to-sentence link cannot be proven.'
		);
		return $states[1];
	}

	/**
	 * Every distinct capture of one pattern.
	 *
	 * @param string $pattern Regular expression.
	 * @param string $source  File contents.
	 * @return list<string>
	 */
	private function codes_matching( string $pattern, string $source ): array {
		preg_match_all( $pattern, $source, $found );
		return array_values( array_unique( $found[1] ) );
	}

	/** A refusal the doors can return without a partition would be guessed. */
	public function test_every_door_code_has_a_partition(): void {
		$missing = array_diff( array_keys( $this->door_codes() ), array_keys( Outcome::table() ) );
		$this->assertSame( array(), array_values( $missing ), 'Unclassified door codes: ' . implode( ', ', $missing ) );
	}

	/** A partition row for a code nothing emits is a stale rule. */
	public function test_no_partition_row_is_unreachable(): void {
		$stale = array_diff( array_keys( Outcome::table() ), $this->all_emitted_codes() );
		$this->assertSame( array(), array_values( $stale ), 'Partitions for unemitted codes: ' . implode( ', ', $stale ) );
	}

	/** Each partition names a state the contact form renders. */
	public function test_each_partition_names_a_rendered_contact_state(): void {
		$rendered = $this->rendered_states();
		foreach ( Outcome::table() as $code => $row ) {
			$this->assertContains( $row[1], $rendered, $code . ' names a state the form cannot render.' );
		}
	}

	/** Both partitions exist, so a table of one kind cannot pass as complete. */
	public function test_both_partitions_are_used(): void {
		$partitions = array_column( Outcome::table(), 0 );
		$this->assertContains( Outcome::REFUSED, $partitions );
		$this->assertContains( Outcome::UNCONFIRMED, $partitions );
	}

	/**
	 * The bounded review store and the native capacity fence refuse before they
	 * write, and each keeps its own sentence instead of a generic verdict.
	 *
	 * @dataProvider review_refusals
	 * @param string $code  Native refusal.
	 * @param string $state Contact form state.
	 */
	public function test_review_refusals_are_definite_and_keep_their_own_sentence( string $code, string $state ): void {
		$this->assertSame( Outcome::REFUSED, Outcome::of( $code ) );
		$this->assertSame( $state, Outcome::contact_state( $code ) );
	}

	/**
	 * The bounded store's and the capacity fence's refusals.
	 *
	 * @return array<string, array{string,string}>
	 */
	public function review_refusals(): array {
		return array(
			'full queue'  => array( 'linker_intake_full', 'review_full' ),
			'oversized'   => array( 'linker_intake_size', 'review_size' ),
			'grouped'     => array( 'linker_intake_grouped', 'grouped' ),
			'no capacity' => array( 'linker_business_capacity', 'reception_full' ),
			'no journal'  => array( 'linker_admission_capacity', 'reception_full' ),
		);
	}

	/**
	 * Native checkout created its order before it could prove it: the request may
	 * exist, so it is neither a refusal nor a verification verdict.
	 */
	public function test_an_unproven_native_create_is_unconfirmed(): void {
		$this->assertSame( Outcome::UNCONFIRMED, Outcome::of( 'linker_inquiry_create' ) );
		$this->assertSame( 'pending', Outcome::contact_state( 'linker_inquiry_create' ) );
	}

	/**
	 * Verification refusals stay verification verdicts rather than a generic
	 * outage sentence.
	 *
	 * @dataProvider verification_refusals
	 * @param string $code  Native refusal.
	 * @param string $state Contact form state.
	 */
	public function test_verification_refusals_keep_their_own_sentence( string $code, string $state ): void {
		$this->assertSame( Outcome::REFUSED, Outcome::of( $code ) );
		$this->assertSame( $state, Outcome::contact_state( $code ) );
	}

	/**
	 * The verification refusals and the sentence each one produces.
	 *
	 * @return array<string, array{string,string}>
	 */
	public function verification_refusals(): array {
		return array(
			'no site key' => array( 'linker_admission_configuration', 'verification_unavailable' ),
			'no proof'    => array( 'linker_admission_proof', 'verification_failed' ),
			'used proof'  => array( 'linker_admission_proof_reused', 'verification_failed' ),
			'new input'   => array( 'linker_admission_payload_changed', 'verification_failed' ),
			'oversized'   => array( 'linker_admission_input', 'verification_failed' ),
		);
	}

	/**
	 * An outcome this table has never seen keeps recovery and asks the customer
	 * to check the earlier request, never to verify again.
	 */
	public function test_an_unrecognized_code_is_unconfirmed(): void {
		$this->assertSame( Outcome::UNCONFIRMED, Outcome::of( 'linker_unrecognized_fixture' ) );
		$this->assertSame( 'pending', Outcome::contact_state( 'linker_unrecognized_fixture' ) );
	}
}
