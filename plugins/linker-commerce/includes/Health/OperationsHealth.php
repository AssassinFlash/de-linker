<?php
/**
 * Operational health in the daily digest: queue age, mail capacity, intake
 * backlog and publication readiness.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Health;

use Linker\Commerce\Digest\Block;
use Linker\Commerce\Mail\Throttle;
use Linker\Commerce\Protection\BusinessCapacity;
use WP_Error;

/**
 * One block, four independent limits, and an alert line only for the dimension
 * that is actually out of bounds. Every threshold below carries the incident
 * or specification that produced it; none is a guess.
 *
 * A quiet day prints one compact sentence instead of four green lines, so the
 * digest keeps its signal when something is wrong (AGENTS.md §0.1: added
 * verification must change a decision).
 */
final class OperationsHealth implements Block {

	/**
	 * Stable identifier of the block.
	 */
	public const ID = 'operations_health';

	/**
	 * Pending actions allowed to sit more than a day past their slot.
	 *
	 * Zero: Outbox::RETRY_DELAYS ends at 86 400 seconds, so a pending action a
	 * day late is not retrying any more — it is stuck. The 2026-11-11 host
	 * MySQL outage took the queue away for 90 minutes and nothing pushed a
	 * single alert (docs/acceptance/2026-11-10/goal-state-ledger.md, outage
	 * timeline); #535 left 38 real notifications held past the 2026-10-22 wave.
	 */
	public const OVERDUE_ALLOWED = 0;

	/**
	 * Share of a channel's day allocation that still leaves ordinary traffic room.
	 *
	 * #545 withholds the last 20 % of the PHP pool (16 of 80) and 10 % of the
	 * SMTP pool (40 of 400) for critical producers, so ordinary mail stops at
	 * 64 PHP / 360 SMTP attempts. Crossing that line means a genuine customer
	 * acknowledgement already cannot send, which is exactly what #535 recorded
	 * when the old single ledger filled 80/80 (docs/specs/545-mail-capacity/SPEC.md).
	 */
	public const MAIL_ORDINARY_PHP  = Throttle::PER_DAY - Throttle::PHP_RESERVE;
	public const MAIL_ORDINARY_SMTP = Throttle::SMTP_PER_DAY - Throttle::SMTP_RESERVE;

	/**
	 * Share of the ordinary inquiry envelope that raises the backlog line.
	 *
	 * Three quarters of BusinessCapacity::LIMITS['ordinary']['count'] (128).
	 * #568 measured the 2026-10-22 wave at 102 unhandled inquiries — 80 % of
	 * the envelope — and at 128 the site refuses a genuine new submission
	 * (docs/specs/568-global-business-intake.md, the occupancy table).
	 */
	public const BACKLOG_SHARE = 0.75;

	/**
	 * Share of the verification lane that raises the quarantine line.
	 *
	 * Quarantined inquiries are held in IntakeStore::CAPACITY['verification']
	 * (128 slots); a full lane refuses a genuine new submission. Nine tenths of
	 * it is 115, and #568 measured exactly 102 unhandled — 80 % of the lane —
	 * when the 2026-10-22 wave was live, which is why the line sits below that
	 * peak. Production held 90 on 2026-11-11: high, but the lane still accepts,
	 * and PendingReviews already reports the standing count daily, so this line
	 * must not restate a normal backlog every morning.
	 */
	public const QUARANTINE_SHARE = 0.9;

	/**
	 * The digest run this block reports on.
	 *
	 * @param int                  $now   Unix time of the digest; 0 reads the clock.
	 * @param OperationsProbe|null $probe Measurement source; null reads the live registry.
	 */
	public function __construct( private readonly int $now = 0, private readonly ?OperationsProbe $probe = null ) {}

	/**
	 * Probes are read at most once per block instance; the template asks for
	 * entries() and empty_text() separately.
	 *
	 * @var array{
	 *   queue: array{pending: int, capped: bool, lateness: int, overdue: int}|WP_Error,
	 *   mail: array{php: int, smtp: int}|WP_Error,
	 *   intake: array{unhandled: int, bytes: int, quarantined: int}|WP_Error,
	 *   publication: array{engineering: int, knowledge: int, total: int}|WP_Error
	 * }|null
	 */
	private ?array $measured = null;

	/**
	 * Stable identifier of the block.
	 */
	public function id(): string {
		return self::ID;
	}

	/**
	 * Heading of the block.
	 */
	public function title(): string {
		return __( 'Operations health', 'linker-commerce' );
	}

	/**
	 * One line per dimension that is out of bounds; nothing when all four hold.
	 *
	 * @return list<array{label: string, url: string, link_text: string, detail: string}>
	 */
	public function entries(): array {
		$measured = $this->measure();
		$entries  = array();

		$queue = $measured['queue'];
		if ( $queue instanceof WP_Error ) {
			$entries[] = $this->unreadable( __( 'The delivery queue could not be read.', 'linker-commerce' ) );
		} elseif ( $queue['overdue'] > self::OVERDUE_ALLOWED ) {
			$entries[] = array(
				/* translators: %d: pending actions past their slot by more than a day. */
				'label'     => sprintf( __( '%d queued delivery action(s) are more than a day overdue.', 'linker-commerce' ), $queue['overdue'] ),
				'url'       => '',
				'link_text' => '',
				'detail'    => sprintf(
					/* translators: 1: pending action count, 2: how long ago the latest action was due. */
					__( 'Queue: %1$s pending in total. The latest action was due %2$s. Retries end after 24 hours, so an action this late is stuck rather than retrying.', 'linker-commerce' ),
					self::pending_text( $queue ),
					\Linker\Commerce\Digest\Format::age( $this->timestamp() - $queue['lateness'], $this->timestamp() )
				),
			);
		}

		$mail = $measured['mail'];
		if ( $mail instanceof WP_Error ) {
			$entries[] = $this->unreadable( __( 'The mail budget could not be read.', 'linker-commerce' ) );
		} else {
			foreach ( $this->mail_overruns( $mail ) as $overrun ) {
				$entries[] = $overrun;
			}
		}

		$intake = $measured['intake'];
		if ( $intake instanceof WP_Error ) {
			$entries[] = $this->unreadable(
				'operations_quarantine_unreadable' === $intake->get_error_code()
					? __( 'The pending-review queue could not be read.', 'linker-commerce' )
					: __( 'The unhandled inquiry envelope could not be read.', 'linker-commerce' )
			);
		} else {
			$limit = (int) floor( BusinessCapacity::LIMITS['ordinary']['count'] * self::BACKLOG_SHARE );
			if ( $intake['unhandled'] >= $limit ) {
				$entries[] = array(
					/* translators: 1: unhandled inquiries, 2: the site envelope. */
					'label'     => sprintf( __( '%1$d unhandled inquiries are near the site envelope of %2$d.', 'linker-commerce' ), $intake['unhandled'], BusinessCapacity::LIMITS['ordinary']['count'] ),
					'url'       => '',
					'link_text' => '',
					'detail'    => sprintf(
						/* translators: 1: logical megabytes, 2: the byte envelope. */
						__( 'Occupied logical data: %1$s of %2$s. At the envelope the site refuses a genuine new submission.', 'linker-commerce' ),
						size_format( $intake['bytes'] ),
						size_format( BusinessCapacity::LIMITS['ordinary']['bytes'] )
					),
				);
			}
			$lane = \Linker\Commerce\Protection\IntakeStore::CAPACITY['verification'];
			if ( $intake['quarantined'] >= (int) floor( $lane * self::QUARANTINE_SHARE ) ) {
				$entries[] = array(
					/* translators: 1: quarantined inquiries, 2: verification lane capacity. */
					'label'     => sprintf( __( '%1$d inquiries are quarantined against a review lane of %2$d.', 'linker-commerce' ), $intake['quarantined'], $lane ),
					'url'       => '',
					'link_text' => '',
					'detail'    => __( 'A full lane refuses a genuine new submission. #568 measured 102 unhandled when the 2026-10-22 wave was live; dispose the backlog or confirm the wave is expected before the lane fills.', 'linker-commerce' ),
				);
			}
		}

		$publication = $measured['publication'];
		if ( $publication instanceof WP_Error ) {
			$entries[] = $this->unreadable( __( 'The publication manifest could not be read.', 'linker-commerce' ) );
		} elseif ( $publication['total'] > 0 && $publication['engineering'] < $publication['total'] ) {
			$entries[] = array(
				/* translators: 1: prepared products, 2: published products. */
				'label'     => sprintf( __( 'Engineering feed prepared %1$d of %2$d products.', 'linker-commerce' ), $publication['engineering'], $publication['total'] ),
				'url'       => '',
				'link_text' => '',
				'detail'    => __( 'The planner builds from this feed. An all-zero reading was the 2026-11-11 signature after a pull changed every product revision; run the publication repair and confirm the dry run reports no backlog.', 'linker-commerce' ),
			);
		}

		return $entries;
	}

	/**
	 * The compact sentence a healthy day prints.
	 */
	public function empty_text(): string {
		$measured = $this->measure();
		$parts    = array();

		$queue   = $measured['queue'];
		$parts[] = $queue instanceof WP_Error
			? __( 'queue unreadable', 'linker-commerce' )
			: sprintf(
				/* translators: 1: pending actions, 2: nothing late, or how late the latest action is. */
				__( 'queue %1$s (%2$s)', 'linker-commerce' ),
				self::pending_text( $queue ),
				0 === $queue['lateness']
					? __( 'nothing late', 'linker-commerce' )
					: self::late_text( $queue['lateness'] )
			);

		$mail    = $measured['mail'];
		$parts[] = $mail instanceof WP_Error
			? __( 'mail unreadable', 'linker-commerce' )
			: sprintf(
				/* translators: 1: PHP attempts used, 2: PHP day allocation, 3: SMTP attempts used, 4: SMTP day allocation. */
				__( 'mail %1$d/%2$d PHP, %3$d/%4$d SMTP', 'linker-commerce' ),
				$mail['php'],
				Throttle::PER_DAY,
				$mail['smtp'],
				Throttle::SMTP_PER_DAY
			);

		$intake  = $measured['intake'];
		$parts[] = $intake instanceof WP_Error
			? __( 'intake unreadable', 'linker-commerce' )
			: sprintf(
				/* translators: 1: unhandled inquiries, 2: the site envelope, 3: quarantined inquiries. */
				__( 'intake %1$d/%2$d unhandled, %3$d quarantined', 'linker-commerce' ),
				$intake['unhandled'],
				BusinessCapacity::LIMITS['ordinary']['count'],
				$intake['quarantined']
			);

		$publication = $measured['publication'];
		$parts[]     = $publication instanceof WP_Error
			? __( 'publication unreadable', 'linker-commerce' )
			: sprintf(
				/* translators: 1: prepared engineering products, 2: published products, 3: prepared knowledge products. */
				__( 'publication %1$d/%2$d engineering, %3$d knowledge', 'linker-commerce' ),
				$publication['engineering'],
				$publication['total'],
				$publication['knowledge']
			);

		return sprintf(
			/* translators: %s: the four measured dimensions, comma separated. */
			__( 'All within bounds — %s.', 'linker-commerce' ),
			implode( ', ', $parts )
		);
	}

	/**
	 * The four probes, read once.
	 *
	 * @return array{
	 *   queue: array{pending: int, capped: bool, lateness: int, overdue: int}|WP_Error,
	 *   mail: array{php: int, smtp: int}|WP_Error,
	 *   intake: array{unhandled: int, bytes: int, quarantined: int}|WP_Error,
	 *   publication: array{engineering: int, knowledge: int, total: int}|WP_Error
	 * }
	 */
	private function measure(): array {
		if ( null !== $this->measured ) {
			return $this->measured;
		}
		$probe          = $this->probe ?? new OperationsProbe();
		$now            = $this->timestamp();
		$this->measured = array(
			'queue'       => $probe->queue( $now ),
			'mail'        => $probe->mail( $now ),
			'intake'      => $probe->intake(),
			'publication' => $probe->publication(),
		);
		return $this->measured;
	}

	/**
	 * One alert line per mail channel that has crossed its ordinary share.
	 *
	 * @param array{php: int, smtp: int} $mail Charged attempts of both channels.
	 * @return list<array{label: string, url: string, link_text: string, detail: string}>
	 */
	private function mail_overruns( array $mail ): array {
		$limits  = array(
			Throttle::PHP  => array( self::MAIL_ORDINARY_PHP, Throttle::PER_DAY, __( 'PHP mail()', 'linker-commerce' ) ),
			Throttle::SMTP => array( self::MAIL_ORDINARY_SMTP, Throttle::SMTP_PER_DAY, __( 'SMTP', 'linker-commerce' ) ),
		);
		$entries = array();
		foreach ( $limits as $channel => $limit ) {
			$used = $mail[ $channel ];
			if ( $used < $limit[0] ) {
				continue;
			}
			$entries[] = array(
				/* translators: 1: mail channel, 2: attempts charged, 3: the day allocation. */
				'label'     => sprintf( __( '%1$s has used %2$d of %3$d daily attempts.', 'linker-commerce' ), $limit[2], $used, $limit[1] ),
				'url'       => '',
				'link_text' => '',
				'detail'    => sprintf(
					/* translators: 1: the ordinary share, 2: the attempts still reserved for critical mail. */
					__( 'Ordinary mail stops at %1$d; the last %2$d attempts are held for password resets, approvals and staff alerts. Customer acknowledgements wait for the rolling window to move on.', 'linker-commerce' ),
					$limit[0],
					$limit[1] - $limit[0]
				),
			);
		}
		return $entries;
	}

	/**
	 * A dimension that could not be read is reported, never shown as zero.
	 *
	 * @param string $label What could not be read.
	 * @return array{label: string, url: string, link_text: string, detail: string}
	 */
	private function unreadable( string $label ): array {
		return array(
			'label'     => $label,
			'url'       => '',
			'link_text' => '',
			'detail'    => __( 'This is not a zero reading: the measurement itself failed, so nothing about this dimension is known today.', 'linker-commerce' ),
		);
	}

	/**
	 * Pending count as a number, or as a floor when the sample page filled.
	 *
	 * @param array{pending: int, capped: bool, lateness: int, overdue: int} $queue Queue measurement.
	 */
	private static function pending_text( array $queue ): string {
		return $queue['capped']
			? sprintf(
				/* translators: %d: actions read in one page. */
				__( 'at least %d', 'linker-commerce' ),
				$queue['pending']
			)
			: (string) $queue['pending'];
	}

	/**
	 * How late the latest action is, in the compact sentence: hours below two
	 * days, whole days after that, the same scale Format::age() uses.
	 *
	 * @param int $seconds Lateness.
	 */
	private static function late_text( int $seconds ): string {
		$hours = (int) floor( $seconds / HOUR_IN_SECONDS );
		if ( $hours < 48 ) {
			$hours = max( 1, $hours );
			/* translators: %d: number of hours. */
			return sprintf( _n( '%d hour late', '%d hours late', $hours, 'linker-commerce' ), $hours );
		}
		$days = (int) floor( $seconds / DAY_IN_SECONDS );
		/* translators: %d: number of days. */
		return sprintf( _n( '%d day late', '%d days late', $days, 'linker-commerce' ), $days );
	}

	/**
	 * Unix time of the digest.
	 */
	private function timestamp(): int {
		return $this->now > 0 ? $this->now : time();
	}
}
