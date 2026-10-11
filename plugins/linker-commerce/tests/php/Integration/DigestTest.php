<?php
/**
 * The daily digest against a real WooCommerce.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use ActionScheduler_QueueRunner;
use ActionScheduler_Store;
use Linker\Commerce\Digest\Block;
use Linker\Commerce\Digest\Blocks;
use Linker\Commerce\Digest\FailedEmails;
use Linker\Commerce\Digest\InquiriesAwaitingProforma;
use Linker\Commerce\Digest\Module;
use Linker\Commerce\Digest\ProformasAwaitingReply;
use Linker\Commerce\Digest\Scheduler;
use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Mail\Outbox;
use Linker\Commerce\Mail\Throttle;
use Linker\Commerce\Proforma\Issuer;
use Linker\Commerce\Registration\PendingApprovals;
use Linker\Commerce\Settings\Options;
use WC_DateTime;
use WC_Order;

/**
 * Real inquiries at the window's edges, an empty digest that still goes out,
 * and the Outbox path the digest itself travels (docs/specs/74-daily-digest.md,
 * acceptance).
 *
 * Recipients are asserted as the settings hold them. The test-mail discipline
 * (AGENTS.md) puts ONE switch in the Mail layer (Mail\TestMode, ticket #73,
 * landed with the approval ticket) that rewrites a test send to
 * chester@de-linker.com; it is off unless a scenario turns it on, so these
 * assertions read the real recipients. A scenario that turns it on reads its
 * address in the assertions about a delivered message — the wp_mail_succeeded
 * capture and the .eml — while the queue assertions (the JobStore rows, which
 * keep the original recipients) do not change.
 *
 * @coversNothing
 */
final class DigestTest extends IntegrationTestCase {

	/**
	 * The team mailbox and blind copies the tests read back.
	 */
	public function setUp(): void {
		parent::setUp();
		delete_option( Throttle::OPTION );
	}

	/**
	 * The window boundaries: 25 hours in, 23 out, and exactly 24 hours out;
	 * 73 hours in, 71 and exactly 72 out. The edge fixtures cross midnight in
	 * Berlin: the 25-hour inquiry was created on the previous calendar day.
	 */
	public function test_window_boundaries(): void {
		$inquiry_in   = $this->backdated_inquiry( time() - 25 * 3600 );
		$inquiry_out  = $this->backdated_inquiry( time() - 23 * 3600 );
		$proforma_in  = $this->issued_proforma( time() - 73 * 3600 );
		$proforma_out = $this->issued_proforma( time() - 71 * 3600 );

		// The exact edge, against a fixed now so the moving clock cannot flip it.
		$created = $inquiry_out->get_date_created();
		$this->assertInstanceOf( WC_DateTime::class, $created );
		$created = (int) $created->getTimestamp();
		$this->assertSame(
			array(),
			$this->fixture_only( ( new InquiriesAwaitingProforma( $created + 24 * 3600 ) )->entries(), $inquiry_out ),
			'An inquiry exactly 24 hours old is not listed.'
		);
		$this->assertCount(
			1,
			$this->fixture_only( ( new InquiriesAwaitingProforma( $created + 24 * 3600 + 1 ) )->entries(), $inquiry_out ),
			'One second past 24 hours, it is.'
		);
		$issued = (int) $proforma_out->get_meta( Issuer::ISSUED_META );
		$this->assertSame(
			array(),
			$this->fixture_only( ( new ProformasAwaitingReply( $issued + 72 * 3600 ) )->entries(), $proforma_out ),
			'A Proforma exactly 72 hours out is not listed.'
		);
		$this->assertCount(
			1,
			$this->fixture_only( ( new ProformasAwaitingReply( $issued + 72 * 3600 + 1 ) )->entries(), $proforma_out ),
			'One second past 72 hours, it is.'
		);

		// The digest's own view, at the real clock: the 25-hour inquiry was
		// created the day before in Berlin, the 23-hour one inside the window.
		$inquiries = $this->fixture_only( ( new InquiriesAwaitingProforma() )->entries(), $inquiry_in, $inquiry_out );
		$this->assertCount( 1, $inquiries );
		$this->assertStringContainsString( '#' . $inquiry_in->get_order_number(), (string) $inquiries[0]['label'] );
		$this->assertStringContainsString( 'Linker Integration Test GmbH', (string) $inquiries[0]['label'] );
		$this->assertNotEmpty( $inquiries[0]['url'] );

		$proformas = $this->fixture_only( ( new ProformasAwaitingReply() )->entries(), $proforma_in, $proforma_out );
		$this->assertCount( 1, $proformas );
		$this->assertStringContainsString( 'PI-', (string) $proformas[0]['detail'] );
		$this->assertSame( '3 days ago', $this->age_of( $proformas[0]['detail'] ) );

		// The boundaries hold in the other direction: the 23-hour inquiry is
		// not among the entries even when the digest runs later in the hour.
		$this->assertCount( 0, $this->fixture_only( ( new InquiriesAwaitingProforma() )->entries(), $inquiry_out ) );
	}

	/**
	 * An empty digest still goes out: one email to the team mailbox, with the
	 * blind copies in the headers and every block's empty sentence.
	 */
	public function test_empty_digest_still_sends(): void {
		$digests = array();
		$this->capture_digests( $digests );
		$this->with_team_recipients();

		$this->run_digest();

		$this->assertCount( 1, $digests, 'One digest, empty or not.' );
		[ $to, $subject, , $body ] = $digests[0];
		// The settings' To: unrewritten, as long as the Mail layer's test switch
		// is off (class docblock; the switch is the approval lane's).
		$this->assertSame( array( 'digest-team@example.test' ), $to );
		$this->assertStringStartsWith( 'Daily digest, ', $subject );
		$this->assertStringContainsString( 'No inquiry is waiting for more than 24 hours.', $body );
		$this->assertStringContainsString( 'No Proforma invoice has waited more than 3 days for a reply.', $body );
		$this->assertStringContainsString( 'No email failed to send.', $body );

		// The blind copies are in the message the host's mail() would receive.
		$raw = $this->latest_eml();
		// The wire copy carries the same unrewritten To (class docblock).
		$this->assertStringContainsString( 'To: digest-team@example.test', $raw );
		$this->assertStringContainsString( 'Bcc: bcc-one@example.test, bcc-two@example.test', $raw );
	}

	/**
	 * The digest rides the Outbox: a send that fails once is retried by Action
	 * Scheduler and delivered exactly once.
	 */
	public function test_outbox_retries_a_failed_digest(): void {
		$digests = array();
		$this->capture_digests( $digests );
		$failures = 1;
		$fail     = static function ( $mailer ) use ( &$failures ): void {
			if ( $failures > 0 ) {
				--$failures;
				$mailer->clearAllRecipients();
			}
		};
		add_action( 'phpmailer_init', $fail, PHP_INT_MAX );
		$this->later(
			static function () use ( $fail ): void {
				remove_action( 'phpmailer_init', $fail, PHP_INT_MAX );
			}
		);

		$this->run_digest();

		$this->assertCount( 0, $digests, 'The first attempt failed.' );
		$job_id = $this->pending_job_id();
		$this->assertGreaterThan( 0, $job_id, 'The digest waits in the queue.' );

		$this->run_pending_action( $job_id );

		$this->assertCount( 1, $digests, 'The retry delivers.' );
		// Delivered, so the unrewritten To once more (class docblock).
		$this->assertSame( array( 'sales@de-linker.com' ), $digests[0][0] );
		$this->assertCount( 0, ( new JobStore() )->failed(), 'Delivered, so not failed.' );
	}

	/**
	 * A digest whose every retry fails is the next digest's fourth block:
	 * the pipe reports itself.
	 */
	public function test_exhausted_digest_is_reported_in_the_next_one(): void {
		$digests = array();
		$this->capture_digests( $digests );
		$fail = static function ( $mailer ): void {
			$mailer->clearAllRecipients();
		};
		add_action( 'phpmailer_init', $fail, PHP_INT_MAX );

		$this->run_digest();
		$job_id   = $this->pending_job_id();
		$attempts = count( Outbox::RETRY_DELAYS ) + 1;
		for ( $attempt = 2; $attempt <= $attempts; ++$attempt ) {
			$this->run_pending_action( $job_id );
		}

		$failed = ( new JobStore() )->failed();
		$this->assertCount( 1, $failed, 'The digest itself is the failed message.' );
		// Queue data: the original recipient, which a send-side rewrite never
		// touches (class docblock).
		$this->assertSame( array( 'sales@de-linker.com' ), $failed[0]['to'] );
		$this->assertStringStartsWith( 'Daily digest, ', $failed[0]['subject'] );

		remove_action( 'phpmailer_init', $fail, PHP_INT_MAX );
		$blocks = ( new Blocks( new JobStore() ) )->all();
		// The approval ticket's pending-accounts block leads the digest (issue
		// #73, the plug point of Blocks::all()); the digest's own three keep
		// their order behind it, the failed emails closing the list — the
		// fourth block here.
		$this->assertSame(
			array( PendingApprovals::ID, InquiriesAwaitingProforma::ID, ProformasAwaitingReply::ID, FailedEmails::ID ),
			array_map( static fn ( Block $block ): string => $block->id(), $blocks )
		);
		$fourth = $blocks[3];
		$this->assertSame( FailedEmails::ID, $fourth->id() );
		$this->assertCount( 1, $fourth->entries() );
		$this->assertStringContainsString( 'Daily digest', $fourth->entries()[0]['label'] );
		$this->assertStringContainsString( 'sales@de-linker.com', $fourth->entries()[0]['detail'] );

		// The queue is empty again for the other tests.
		wp_delete_post( $job_id, true );
		$this->assertCount( 0, ( new JobStore() )->failed() );
	}

	/**
	 * The schedule is on the cron: the first send sits in the future and the
	 * run re-arms the next 09:00 Berlin.
	 */
	public function test_the_schedule_is_armed(): void {
		$this->run_digest();
		$next = wp_next_scheduled( Scheduler::HOOK );
		$this->assertNotFalse( $next, 'The next send is scheduled.' );
		$this->assertGreaterThan( time(), $next, 'It is in the future.' );
		$this->assertEqualsWithDelta(
			Scheduler::next_send( new \DateTimeImmutable( 'now', new \DateTimeZone( Scheduler::TIMEZONE ) ) )->getTimestamp(),
			$next,
			60,
			'The next send is 09:00 Berlin.'
		);
		$this->later(
			static function (): void {
				wp_clear_scheduled_hook( Scheduler::HOOK );
			}
		);
	}

	/**
	 * Sends an inquiry and moves its creation back in time.
	 *
	 * @param int $created Unix time the inquiry was created.
	 */
	private function backdated_inquiry( int $created ): WC_Order {
		$order = $this->send_inquiry( $this->customer(), array( array( $this->product( '1200' ), 1 ) ) );
		$order->set_date_created( $created );
		$order->save();
		$this->as_user( 0 );
		$read_back = wc_get_order( $order->get_id() );
		$this->assertInstanceOf( WC_Order::class, $read_back );
		return $read_back;
	}

	/**
	 * Sends an inquiry, marks it proforma-issued with an issue time. The meta
	 * and status are what the Issuer leaves behind; the PDF pipeline of the
	 * issue button itself is ProformaTest's subject, not this one's.
	 *
	 * @param int $issued Unix time the Proforma was issued.
	 */
	private function issued_proforma( int $issued ): WC_Order {
		$order = $this->send_inquiry( $this->customer(), array( array( $this->product( '1200' ), 1 ) ) );
		$this->as_user( 0 );
		$order->set_status( 'proforma-issued' );
		$order->update_meta_data( Issuer::ISSUED_META, (string) $issued );
		$order->update_meta_data( Issuer::NUMBER_META, 'PI-' . gmdate( 'Y', $issued ) . '-9911' );
		$order->save();
		$read_back = wc_get_order( $order->get_id() );
		$this->assertInstanceOf( WC_Order::class, $read_back );
		return $read_back;
	}

	/**
	 * The entries about the given orders only, so a busy instance's other
	 * inquiries never break a count.
	 *
	 * @param list<array<string, mixed>> $entries Block entries.
	 * @param WC_Order                   ...$orders The fixtures to keep.
	 * @return list<array<string, mixed>>
	 */
	private function fixture_only( array $entries, WC_Order ...$orders ): array {
		$self    = $this;
		$numbers = array_map( static fn ( WC_Order $order ): string => '#' . $order->get_order_number(), $orders );
		return array_values(
			array_filter(
				$entries,
				static fn ( array $entry ): bool => in_array( $self->number_in( (string) $entry['label'] ), $numbers, true )
			)
		);
	}

	/**
	 * The order number an entry label opens with, "Inquiry #123 – …".
	 *
	 * @param string $label Entry label.
	 */
	private function number_in( string $label ): string {
		return 1 === preg_match( '/^Inquiry (#\S+)/', $label, $parts ) ? $parts[1] : $label;
	}

	/**
	 * The age sentence of an entry detail.
	 *
	 * @param string $detail Entry detail.
	 */
	private function age_of( string $detail ): string {
		preg_match( '/\(([^)]+)\)$/', $detail, $parts );
		return $parts[1] ?? '';
	}

	/**
	 * Collects the digest emails that go out, through wp_mail itself, into the
	 * caller's array (so the collection survives until the hook comes off).
	 *
	 * @param list<array{0: list<string>, 1: string, 2: string, 3: string}> $digests The collector.
	 */
	private function capture_digests( array &$digests ): void {
		$collect = static function ( array $mail ) use ( &$digests ): void {
			if ( isset( $mail['subject'] ) && str_starts_with( (string) $mail['subject'], 'Daily digest' ) ) {
				$headers   = $mail['headers'] ?? '';
				$digests[] = array(
					(array) $mail['to'],
					(string) $mail['subject'],
					is_array( $headers ) ? implode( "\n", $headers ) : (string) $headers,
					(string) $mail['message'],
				);
			}
		};
		add_action( 'wp_mail_succeeded', $collect );
		$this->later(
			static function () use ( $collect ): void {
				remove_action( 'wp_mail_succeeded', $collect );
			}
		);
	}

	/**
	 * Team mailbox and blind copies for the run, restored afterwards.
	 */
	private function with_team_recipients(): void {
		$team_to  = get_option( Options::TEAM_TO );
		$team_bcc = get_option( Options::TEAM_BCC );
		update_option( Options::TEAM_TO, 'digest-team@example.test' );
		update_option( Options::TEAM_BCC, "bcc-one@example.test\nbcc-two@example.test" );
		$this->later(
			static function () use ( $team_to, $team_bcc ): void {
				if ( false === $team_to ) {
					delete_option( Options::TEAM_TO );
				} else {
					update_option( Options::TEAM_TO, $team_to );
				}
				if ( false === $team_bcc ) {
					delete_option( Options::TEAM_BCC );
				} else {
					update_option( Options::TEAM_BCC, $team_bcc );
				}
			}
		);
	}

	/**
	 * The scheduled task, as the cron hook would run it.
	 */
	private function run_digest(): void {
		( new Module( WP_PLUGIN_DIR . '/linker-commerce/linker-commerce.php', new JobStore() ) )->run();
		$this->later(
			static function (): void {
				wp_clear_scheduled_hook( Scheduler::HOOK );
			}
		);
	}

	/**
	 * The id of the queue's newest waiting message.
	 */
	private function pending_job_id(): int {
		$jobs = get_posts(
			array(
				'post_type'      => JobStore::POST_TYPE,
				'post_status'    => 'any',
				'posts_per_page' => 1,
				'orderby'        => 'ID',
				'order'          => 'DESC',
			)
		);
		return (int) ( $jobs[0]->ID ?? 0 );
	}

	/**
	 * Processes the pending retry of a job, wherever the clock put it.
	 *
	 * @param int $job_id Job id.
	 */
	private function run_pending_action( int $job_id ): void {
		$pending = as_get_scheduled_actions(
			array(
				'hook'     => Outbox::HOOK,
				'status'   => ActionScheduler_Store::STATUS_PENDING,
				'search'   => (string) $job_id,
				'orderby'  => 'date',
				'order'    => 'DESC',
				'per_page' => 1,
			)
		);
		$this->assertCount( 1, $pending, 'A retry is scheduled.' );
		ActionScheduler_QueueRunner::instance()->process_action( (int) array_key_first( $pending ), 'linker integration test' );
	}

	/**
	 * The captured email of this instance, as the host's mail() would have
	 * received it (the isolation's mail directory).
	 */
	private function latest_eml(): string {
		$files = glob( dirname( (string) getenv( 'LINKER_WP_ROOT' ) ) . '/mail/*.eml' );
		if ( false === $files || array() === $files ) {
			$files = array();
		}
		$this->assertNotEmpty( $files, 'The isolation wrote an email.' );
		$mtimes = array_map( 'filemtime', $files );
		return (string) file_get_contents( $files[ array_search( max( $mtimes ), $mtimes, true ) ] );
	}
}
