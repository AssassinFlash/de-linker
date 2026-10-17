<?php
/**
 * The quality check's verdicts, stored on their conversations.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Genie;

/**
 * Keeps each turn's verdict from the VPS quality worker (#258,
 * docs/specs/33-judge-bakeoff.md "部署目标") as post meta of the conversation
 * it was given in — no custom table (docs/specs/13-genie.md) — so a finding
 * always leads to its conversation, and the conversation's deletion takes its
 * verdicts with it. Also keeps the worker's last status report, and answers
 * the daily digest's summary through the `linker_tools_genie_quality_summary`
 * filter (the digest lives in linker-commerce; the filter is the seam).
 */
class QualityStore {

	/**
	 * One meta row per judged turn (the record the worker sent, sanitized).
	 */
	public const META = 'linker_genie_quality';

	/**
	 * Unix time of the conversation's newest verdict: the admin list's order.
	 */
	public const AT_META = 'linker_genie_quality_at';

	/**
	 * How many of the conversation's verdicts are flagged, and how many failed:
	 * the admin list's filters.
	 */
	public const FLAGGED_META = 'linker_genie_quality_flagged';
	public const FAILED_META  = 'linker_genie_quality_failed';

	/**
	 * The worker's last status report and the time the site received it.
	 */
	public const STATUS_OPTION = 'linker_genie_quality_status';

	/**
	 * Seconds after which a silent worker counts as stopped: three of its
	 * heartbeats (services/genie/src/linker_genie/quality/worker.py,
	 * HEARTBEAT_SECONDS = 600).
	 */
	public const STALE_AFTER = 1800;

	/**
	 * The digest's window: one day, the digest's own period
	 * (docs/specs/74-daily-digest.md).
	 */
	public const SUMMARY_WINDOW = DAY_IN_SECONDS;

	/**
	 * Filter through which the daily digest reads the summary.
	 */
	public const SUMMARY_FILTER = 'linker_tools_genie_quality_summary';

	/**
	 * Labels the rubric questions may carry (services/genie/eval/judges,
	 * rubric.py): grounded 0-2, appropriate yes/no, better_pick A/B/equal.
	 *
	 * @var array<string, list<string>>
	 */
	private const LABELS = array(
		'grounded'    => array( '0', '1', '2' ),
		'appropriate' => array( 'yes', 'no' ),
		'better_pick' => array( 'A', 'B', 'equal' ),
	);

	/**
	 * The flags the worker raises (worker.py, flags_for).
	 *
	 * @var list<string>
	 */
	public const FLAGS = array( 'contradicted', 'unverifiable', 'out_of_remit', 'worse_pick', 'citation', 'unresolved' );

	/**
	 * Hooks the digest's summary filter.
	 */
	public function register(): void {
		add_filter( self::SUMMARY_FILTER, array( $this, 'filter_summary' ), 10, 2 );
	}

	/**
	 * Stores one verdict on its conversation; false when the record names no
	 * conversation of this site.
	 *
	 * A turn judged again (a retry after a failure) replaces its earlier row.
	 *
	 * @param array<string, mixed> $raw The record as the worker sent it.
	 */
	public function store( array $raw ): bool {
		$record       = self::sanitize( $raw );
		$conversation = $record['conversation_id'];
		if ( $record['turn_id'] < 1 || Conversations::POST_TYPE !== get_post_type( $conversation ) ) {
			return false;
		}
		foreach ( $this->judgments( $conversation ) as $old ) {
			if ( $old['turn_id'] === $record['turn_id'] ) {
				delete_post_meta( $conversation, self::META, $old );
			}
		}
		add_post_meta( $conversation, self::META, $record );

		$flagged = 0;
		$failed  = 0;
		foreach ( $this->judgments( $conversation ) as $row ) {
			$flagged += $row['flagged'] ? 1 : 0;
			$failed  += 'failed' === $row['status'] ? 1 : 0;
		}
		update_post_meta( $conversation, self::AT_META, time() );
		update_post_meta( $conversation, self::FLAGGED_META, $flagged );
		update_post_meta( $conversation, self::FAILED_META, $failed );
		return true;
	}

	/**
	 * The conversation's verdicts, oldest turn first.
	 *
	 * @param int $conversation Conversation post ID.
	 * @return list<array<string, mixed>>
	 */
	public function judgments( int $conversation ): array {
		$rows = get_post_meta( $conversation, self::META, false );
		$list = array();
		foreach ( is_array( $rows ) ? $rows : array() as $row ) {
			if ( is_array( $row ) && isset( $row['turn_id'] ) ) {
				$list[] = $row;
			}
		}
		usort( $list, static fn ( array $a, array $b ): int => (int) $a['turn_id'] <=> (int) $b['turn_id'] );
		return $list;
	}

	/**
	 * Keeps the worker's status report, stamped with the time it arrived.
	 *
	 * @param array<string, mixed> $status The report.
	 */
	public function store_status( array $status ): void {
		$keep = array();
		foreach ( array( 'at', 'judge', 'escalation', 'last_error', 'last_error_at' ) as $key ) {
			$keep[ $key ] = isset( $status[ $key ] ) && is_scalar( $status[ $key ] ) ? self::text( (string) $status[ $key ], 500 ) : '';
		}
		foreach ( array( 'retrying', 'gave_up' ) as $key ) {
			$keep[ $key ] = isset( $status[ $key ] ) && is_numeric( $status[ $key ] ) ? (int) $status[ $key ] : 0;
		}
		$keep['received'] = time();
		update_option( self::STATUS_OPTION, $keep, false );
	}

	/**
	 * The worker's last report, with `stale` when it is older than STALE_AFTER
	 * or there is none.
	 *
	 * @return array{received: int, stale: bool, judge: string, escalation: string, retrying: int, gave_up: int, last_error: string, last_error_at: string}
	 */
	public function status(): array {
		$stored   = get_option( self::STATUS_OPTION, array() );
		$stored   = is_array( $stored ) ? $stored : array();
		$received = isset( $stored['received'] ) ? (int) $stored['received'] : 0;
		return array(
			'received'      => $received,
			'stale'         => $received < 1 || time() - $received > self::STALE_AFTER,
			'judge'         => (string) ( $stored['judge'] ?? '' ),
			'escalation'    => (string) ( $stored['escalation'] ?? '' ),
			'retrying'      => (int) ( $stored['retrying'] ?? 0 ),
			'gave_up'       => (int) ( $stored['gave_up'] ?? 0 ),
			'last_error'    => (string) ( $stored['last_error'] ?? '' ),
			'last_error_at' => (string) ( $stored['last_error_at'] ?? '' ),
		);
	}

	/**
	 * The verdicts given since `$since`, counted, with the worker's state.
	 *
	 * @param int $since Unix time.
	 * @return array{judged: int, flagged: int, escalated: int, failed: int, skipped: int, worker_seen_at: int, worker_stale: bool, last_error: string, url: string, line: string}
	 */
	public function summary( int $since ): array {
		$counts        = array(
			'judged'    => 0,
			'flagged'   => 0,
			'escalated' => 0,
			'failed'    => 0,
			'skipped'   => 0,
		);
		$conversations = get_posts(
			array(
				'post_type'      => Conversations::POST_TYPE,
				'post_status'    => 'any',
				'posts_per_page' => -1,
				'fields'         => 'ids',
				'meta_query'     => array( // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_query -- one day of conversations, once a day.
					array(
						'key'     => self::AT_META,
						'value'   => $since,
						'compare' => '>=',
						'type'    => 'NUMERIC',
					),
				),
			)
		);
		foreach ( $conversations as $conversation ) {
			foreach ( $this->judgments( (int) $conversation ) as $row ) {
				$judged_at = strtotime( (string) $row['judged_at'] );
				if ( false === $judged_at || $judged_at < $since ) {
					continue;
				}
				if ( 'judged' === $row['status'] ) {
					++$counts['judged'];
					$counts['flagged']   += $row['flagged'] ? 1 : 0;
					$counts['escalated'] += $row['escalated'] ? 1 : 0;
				} elseif ( 'failed' === $row['status'] ) {
					++$counts['failed'];
				} else {
					++$counts['skipped'];
				}
			}
		}
		$status = $this->status();
		$line   = sprintf(
			/* translators: 1: answers judged, 2: of them flagged, 3: of them decided by the second judge, 4: answers that could not be judged. */
			__( 'Genie quality check, last 24 hours: %1$d answers judged, %2$d flagged, %3$d decided by the second judge, %4$d could not be judged.', 'linker-tools' ),
			$counts['judged'],
			$counts['flagged'],
			$counts['escalated'],
			$counts['failed']
		);
		if ( $status['stale'] ) {
			$line .= ' ' . __( 'The quality check has stopped reporting.', 'linker-tools' );
		}
		return array_merge(
			$counts,
			array(
				'worker_seen_at' => $status['received'],
				'worker_stale'   => $status['stale'],
				'last_error'     => $status['last_error'],
				'url'            => admin_url( 'admin.php?page=' . QualityPage::SLUG ),
				'line'           => $line,
			)
		);
	}

	/**
	 * The summary filter: the last day's summary, or `$since`'s window when
	 * the caller passes one.
	 *
	 * @param mixed $summary What earlier listeners returned (ignored).
	 * @param mixed $since   Unix time the window starts at; one day ago when absent.
	 * @return array<string, mixed>
	 */
	public function filter_summary( $summary, $since = null ): array {
		unset( $summary );
		$start = is_numeric( $since ) ? (int) $since : time() - self::SUMMARY_WINDOW;
		return $this->summary( $start );
	}

	/**
	 * The record with known keys and types only; strings are bounded.
	 *
	 * @param array<string, mixed> $raw The worker's record.
	 * @return array{turn_id: int, conversation_id: int, turn_at: string, judged_at: string, locale: string, status: string, question: string, answer: string, cards: list<int>, page_product: int, labels: array<string, string>, sources: array<string, string>, confidence: array<string, float>, escalated: bool, escalation: list<string>, reasons: array<string, string>, citations: list<string>, flags: list<string>, flagged: bool, error: string, skip_reason: string, attempts: int, cost_usd: float, fallback: bool}
	 */
	public static function sanitize( array $raw ): array {
		$status = isset( $raw['status'] ) && in_array( $raw['status'], array( 'judged', 'failed', 'skipped' ), true ) ? (string) $raw['status'] : 'failed';
		$labels = array();
		foreach ( self::LABELS as $question => $allowed ) {
			$value = $raw['labels'][ $question ] ?? null;
			if ( is_string( $value ) && in_array( $value, $allowed, true ) ) {
				$labels[ $question ] = $value;
			}
		}
		$flags = array();
		foreach ( is_array( $raw['flags'] ?? null ) ? $raw['flags'] : array() as $flag ) {
			if ( is_string( $flag ) && in_array( $flag, self::FLAGS, true ) ) {
				$flags[] = $flag;
			}
		}
		return array(
			'turn_id'         => self::int( $raw['turn_id'] ?? 0 ),
			'conversation_id' => self::int( $raw['conversation_id'] ?? 0 ),
			'turn_at'         => self::text( $raw['turn_at'] ?? '', 32 ),
			'judged_at'       => self::text( $raw['judged_at'] ?? '', 32 ),
			'locale'          => 'de' === ( $raw['locale'] ?? '' ) ? 'de' : 'en',
			'status'          => $status,
			'question'        => self::text( $raw['question'] ?? '', 1000 ),
			'answer'          => self::text( $raw['answer'] ?? '', 4000 ),
			'cards'           => self::ints( $raw['cards'] ?? array() ),
			'page_product'    => self::int( $raw['page_product'] ?? 0 ),
			'labels'          => $labels,
			'sources'         => self::texts( $raw['sources'] ?? array(), array_keys( self::LABELS ), 32 ),
			'confidence'      => self::floats( $raw['confidence'] ?? array(), array_keys( self::LABELS ) ),
			'escalated'       => true === ( $raw['escalated'] ?? false ),
			'escalation'      => array_values( self::texts( $raw['escalation'] ?? array(), null, 120 ) ),
			'reasons'         => self::texts( $raw['reasons'] ?? array(), array( 'jev', 'deepseek' ), 1000 ),
			'citations'       => array_values( self::texts( $raw['citations'] ?? array(), null, 200 ) ),
			'flags'           => $flags,
			'flagged'         => 'judged' === $status && array() !== $flags,
			'error'           => self::text( $raw['error'] ?? '', 500 ),
			'skip_reason'     => self::text( $raw['skip_reason'] ?? '', 200 ),
			'attempts'        => self::int( $raw['attempts'] ?? 0 ),
			'cost_usd'        => is_numeric( $raw['cost_usd'] ?? null ) ? (float) $raw['cost_usd'] : 0.0,
			'fallback'        => true === ( $raw['fallback'] ?? false ),
		);
	}

	/**
	 * A non-negative integer.
	 *
	 * @param mixed $value Value.
	 */
	private static function int( $value ): int {
		return is_numeric( $value ) ? max( 0, (int) $value ) : 0;
	}

	/**
	 * Positive integers, in order.
	 *
	 * @param mixed $values Values.
	 * @return list<int>
	 */
	private static function ints( $values ): array {
		$list = array();
		foreach ( is_array( $values ) ? $values : array() as $value ) {
			if ( is_numeric( $value ) && (int) $value > 0 ) {
				$list[] = (int) $value;
			}
		}
		return $list;
	}

	/**
	 * Plain text, valid UTF-8, at most `$length` characters.
	 *
	 * @param mixed $value  Value.
	 * @param int   $length Character limit.
	 */
	private static function text( $value, int $length ): string {
		if ( ! is_scalar( $value ) ) {
			return '';
		}
		return mb_substr( wp_check_invalid_utf8( (string) $value, true ), 0, $length );
	}

	/**
	 * A map (or list) of bounded strings, keys limited to `$keys` when given.
	 *
	 * @param mixed             $values Values.
	 * @param list<string>|null $keys   Allowed keys; null keeps every key.
	 * @param int               $length Character limit per value.
	 * @return array<string, string>
	 */
	private static function texts( $values, ?array $keys, int $length ): array {
		$map = array();
		foreach ( is_array( $values ) ? $values : array() as $key => $value ) {
			if ( null !== $keys && ! in_array( $key, $keys, true ) ) {
				continue;
			}
			if ( is_scalar( $value ) && '' !== (string) $value ) {
				$map[ (string) $key ] = self::text( $value, $length );
			}
		}
		return $map;
	}

	/**
	 * A map of numbers, keys limited to `$keys`.
	 *
	 * @param mixed    $values Values.
	 * @param string[] $keys   Allowed keys.
	 * @return array<string, float>
	 */
	private static function floats( $values, array $keys ): array {
		$map = array();
		foreach ( is_array( $values ) ? $values : array() as $key => $value ) {
			if ( in_array( $key, $keys, true ) && is_numeric( $value ) ) {
				$map[ (string) $key ] = (float) $value;
			}
		}
		return $map;
	}
}
