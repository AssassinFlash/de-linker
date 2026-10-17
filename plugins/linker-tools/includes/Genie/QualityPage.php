<?php
/**
 * The admin page of the Genie quality check.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Genie;

use WP_Post;

/**
 * Admin → Genie quality: the conversations with verdicts, newest first,
 * filterable to the flagged and the failed; one conversation opens with its
 * verdicts turn by turn and its whole thread below them, so a finding is
 * read where it happened. The worker's state heads the list: a stopped
 * worker or a failing judge is the first thing on the page.
 *
 * Core admin markup and classes only (widefat tables, notices, subsubsub):
 * no plugin CSS, no script.
 */
class QualityPage {

	/**
	 * Menu slug.
	 */
	public const SLUG = 'linker-genie-quality';

	/**
	 * Who may read it: the shop's staff, who read the conversations' inquiries too.
	 */
	public const CAPABILITY = 'manage_woocommerce';

	/**
	 * Conversations per list page: WordPress's own list-table default.
	 */
	public const PER_PAGE = 20;

	/**
	 * Sets up the page.
	 *
	 * @param QualityStore $store  The verdicts.
	 * @param Thread       $thread The conversations' stored threads.
	 */
	public function __construct(
		private readonly QualityStore $store,
		private readonly Thread $thread
	) {}

	/**
	 * Adds the menu entry.
	 */
	public function register(): void {
		add_action( 'admin_menu', array( $this, 'menu' ) );
	}

	/**
	 * The menu entry, beside WooCommerce's.
	 */
	public function menu(): void {
		add_menu_page(
			__( 'Genie quality check', 'linker-tools' ),
			__( 'Genie quality', 'linker-tools' ),
			self::CAPABILITY,
			self::SLUG,
			array( $this, 'render' ),
			'dashicons-format-chat',
			58
		);
	}

	/**
	 * The page: one conversation when the URL names one, the list otherwise.
	 */
	public function render(): void {
		if ( ! current_user_can( self::CAPABILITY ) ) {
			return;
		}
		// phpcs:disable WordPress.Security.NonceVerification.Recommended -- read-only view parameters.
		$conversation = isset( $_GET['conversation'] ) ? absint( wp_unslash( $_GET['conversation'] ) ) : 0;
		$filter       = isset( $_GET['filter'] ) ? sanitize_key( wp_unslash( $_GET['filter'] ) ) : '';
		$paged        = isset( $_GET['paged'] ) ? max( 1, absint( wp_unslash( $_GET['paged'] ) ) ) : 1;
		// phpcs:enable
		echo '<div class="wrap">';
		if ( $conversation > 0 ) {
			$this->render_conversation( $conversation );
		} else {
			$this->render_list( $filter, $paged );
		}
		echo '</div>';
	}

	/**
	 * The worker's state, as a notice when something is wrong.
	 */
	private function render_status(): void {
		$status = $this->store->status();
		if ( $status['stale'] ) {
			$when = $status['received'] > 0 ? $this->time( $status['received'] ) : __( 'never', 'linker-tools' );
			printf(
				'<div class="notice notice-error inline"><p>%s</p></div>',
				esc_html(
					sprintf(
						/* translators: %s: date and time of the last report, or "never". */
						__( 'The quality check has stopped reporting. Last report: %s.', 'linker-tools' ),
						$when
					)
				)
			);
		}
		if ( '' !== $status['last_error'] ) {
			printf(
				'<div class="notice notice-warning inline"><p>%s</p></div>',
				esc_html(
					sprintf(
						/* translators: 1: date and time of the error, 2: the error. */
						__( 'Last judge error (%1$s): %2$s', 'linker-tools' ),
						$this->time( (int) strtotime( $status['last_error_at'] ) ),
						$status['last_error']
					)
				)
			);
		}
		if ( $status['received'] > 0 ) {
			printf(
				'<p>%s</p>',
				esc_html(
					sprintf(
						/* translators: 1: first judge, 2: escalation judge, 3: date and time of the last report, 4: answers waiting for a retry, 5: answers given up after every retry. */
						__( 'Judge: %1$s; when unsure: %2$s. Last report: %3$s. Waiting for a retry: %4$d. Given up: %5$d.', 'linker-tools' ),
						$status['judge'],
						$status['escalation'],
						$this->time( $status['received'] ),
						$status['retrying'],
						$status['gave_up']
					)
				)
			);
		}
	}

	/**
	 * The conversations with verdicts.
	 *
	 * @param string $filter `flagged`, `failed` or empty.
	 * @param int    $paged  Page number.
	 */
	private function render_list( string $filter, int $paged ): void {
		printf( '<h1>%s</h1>', esc_html__( 'Genie quality check', 'linker-tools' ) );
		echo '<p>' . esc_html__( 'Every answer Genie gives is judged after it is sent: is it supported by what Genie looked up, does it stay within Genie\'s remit, and would a wrong product have been judged better. Answers flagged here need a look.', 'linker-tools' ) . '</p>';
		$this->render_status();

		$filters = array(
			''        => __( 'All', 'linker-tools' ),
			'flagged' => __( 'Flagged', 'linker-tools' ),
			'failed'  => __( 'Not judged', 'linker-tools' ),
		);
		if ( ! isset( $filters[ $filter ] ) ) {
			$filter = '';
		}
		$links = array();
		foreach ( $filters as $key => $label ) {
			$url     = add_query_arg( array( 'filter' => '' === $key ? false : $key ), $this->url() );
			$current = $key === $filter ? ' class="current" aria-current="page"' : '';
			$links[] = sprintf( '<li><a href="%s"%s>%s</a></li>', esc_url( $url ), $current, esc_html( $label ) );
		}
		echo '<ul class="subsubsub">' . implode( ' | ', $links ) . '</ul>'; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- each link escaped above.

		$query = array(
			'post_type'      => Conversations::POST_TYPE,
			'post_status'    => 'any',
			'posts_per_page' => self::PER_PAGE,
			'paged'          => $paged,
			'meta_key'       => QualityStore::AT_META, // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_key -- the list's order; staff page.
			'orderby'        => 'meta_value_num',
			'order'          => 'DESC',
		);
		if ( '' !== $filter ) {
			$query['meta_query'] = array( // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_query -- staff page.
				array(
					'key'     => 'flagged' === $filter ? QualityStore::FLAGGED_META : QualityStore::FAILED_META,
					'value'   => 0,
					'compare' => '>',
					'type'    => 'NUMERIC',
				),
			);
		}
		$result = new \WP_Query( $query );
		// WP_Query leaves `posts` null only before it ran; the constructor ran it.
		$posts = $result->posts ?? array();

		echo '<table class="wp-list-table widefat fixed striped"><thead><tr>';
		foreach ( array( __( 'Conversation', 'linker-tools' ), __( 'Last verdict', 'linker-tools' ), __( 'Answers judged', 'linker-tools' ), __( 'Flagged', 'linker-tools' ), __( 'Not judged', 'linker-tools' ) ) as $heading ) {
			printf( '<th scope="col">%s</th>', esc_html( $heading ) );
		}
		echo '</tr></thead><tbody>';
		if ( array() === $posts ) {
			printf( '<tr><td colspan="5">%s</td></tr>', esc_html__( 'No verdicts yet.', 'linker-tools' ) );
		}
		foreach ( $posts as $post ) {
			if ( ! $post instanceof WP_Post ) {
				continue;
			}
			$rows   = $this->store->judgments( $post->ID );
			$judged = count( array_filter( $rows, static fn ( array $row ): bool => 'judged' === $row['status'] ) );
			printf(
				'<tr><td><a href="%s"><strong>%s</strong></a></td><td>%s</td><td>%d</td><td>%d</td><td>%d</td></tr>',
				esc_url( add_query_arg( 'conversation', $post->ID, $this->url() ) ),
				esc_html( $this->title( $post ) ),
				esc_html( $this->time( (int) get_post_meta( $post->ID, QualityStore::AT_META, true ) ) ),
				(int) $judged,
				(int) get_post_meta( $post->ID, QualityStore::FLAGGED_META, true ),
				(int) get_post_meta( $post->ID, QualityStore::FAILED_META, true )
			);
		}
		echo '</tbody></table>';

		$pages = paginate_links(
			array(
				'base'    => add_query_arg( 'paged', '%#%', add_query_arg( array( 'filter' => '' === $filter ? false : $filter ), $this->url() ) ),
				'format'  => '',
				'current' => $paged,
				'total'   => max( 1, (int) $result->max_num_pages ),
			)
		);
		if ( is_string( $pages ) ) {
			echo '<div class="tablenav"><div class="tablenav-pages">' . wp_kses_post( $pages ) . '</div></div>';
		}
	}

	/**
	 * One conversation: its verdicts turn by turn, then the whole thread.
	 *
	 * @param int $conversation Conversation post ID.
	 */
	private function render_conversation( int $conversation ): void {
		$post = get_post( $conversation );
		printf( '<p><a href="%s">&larr; %s</a></p>', esc_url( $this->url() ), esc_html__( 'All conversations', 'linker-tools' ) );
		if ( ! $post instanceof WP_Post || Conversations::POST_TYPE !== $post->post_type ) {
			printf( '<h1>%s</h1>', esc_html__( 'This conversation no longer exists.', 'linker-tools' ) );
			return;
		}
		printf( '<h1>%s</h1>', esc_html( $this->title( $post ) ) );
		$author = (int) $post->post_author;
		$user   = $author > 0 ? get_userdata( $author ) : false;
		printf(
			'<p>%s</p>',
			esc_html(
				sprintf(
					/* translators: 1: customer name or "Guest", 2: date and time the conversation started, 3: conversation ID. */
					__( 'Customer: %1$s · Started: %2$s · Conversation %3$d', 'linker-tools' ),
					false !== $user ? $user->display_name : __( 'Guest', 'linker-tools' ),
					$this->time( (int) get_post_time( 'U', true, $post ) ),
					$post->ID
				)
			)
		);

		printf( '<h2>%s</h2>', esc_html__( 'Verdicts', 'linker-tools' ) );
		// `fixed`: core's fixed table layout, so long URLs in an answer or an
		// error wrap (core's `.widefat *` word-wrap) instead of widening the
		// page past a phone's width.
		echo '<table class="widefat fixed striped"><thead><tr>';
		foreach ( array( __( 'Asked', 'linker-tools' ), __( 'Question and answer', 'linker-tools' ), __( 'Verdict', 'linker-tools' ) ) as $heading ) {
			printf( '<th scope="col">%s</th>', esc_html( $heading ) );
		}
		echo '</tr></thead><tbody>';
		foreach ( $this->store->judgments( $conversation ) as $row ) {
			printf(
				'<tr id="turn-%1$d"><td>%2$s<br><small>%3$s</small></td><td><p><strong>%4$s</strong></p><p>%5$s</p></td><td>%6$s</td></tr>',
				(int) $row['turn_id'],
				// The service logs SQLite's datetime('now'), which is UTC.
				esc_html( $this->time( (int) strtotime( (string) $row['turn_at'] . ' UTC' ) ) ),
				esc_html(
					sprintf(
						/* translators: %d: the service's turn number. */
						__( 'Turn %d', 'linker-tools' ),
						(int) $row['turn_id']
					)
				),
				esc_html( (string) $row['question'] ),
				nl2br( esc_html( (string) $row['answer'] ) ),
				$this->verdict( $row ) // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- built from escaped parts in verdict().
			);
		}
		echo '</tbody></table>';

		printf( '<h2>%s</h2>', esc_html__( 'Conversation', 'linker-tools' ) );
		$thread = $this->thread->read( $conversation );
		echo '<table class="widefat fixed striped"><tbody>';
		foreach ( $thread['messages'] as $message ) {
			printf(
				'<tr><th scope="row">%s</th><td>%s</td></tr>',
				esc_html( 'assistant' === $message['role'] ? 'Genie' : __( 'Customer', 'linker-tools' ) ),
				nl2br( esc_html( (string) $message['content'] ) )
			);
		}
		echo '</tbody></table>';
	}

	/**
	 * One verdict as escaped HTML: the outcome, then why.
	 *
	 * @param array<string, mixed> $row A stored verdict (QualityStore::sanitize()).
	 */
	private function verdict( array $row ): string {
		$lines = array();
		if ( 'failed' === $row['status'] ) {
			$lines[] = '<strong>' . esc_html__( 'Not judged', 'linker-tools' ) . '</strong>';
			$lines[] = esc_html( (string) $row['error'] );
			return implode( '<br>', $lines );
		}
		if ( 'skipped' === $row['status'] ) {
			$lines[] = '<strong>' . esc_html__( 'Skipped', 'linker-tools' ) . '</strong>';
			$lines[] = esc_html( (string) $row['skip_reason'] );
			return implode( '<br>', $lines );
		}
		$flags   = is_array( $row['flags'] ) ? $row['flags'] : array();
		$lines[] = '<strong>' . esc_html( array() === $flags ? __( 'Fine', 'linker-tools' ) : __( 'Flagged', 'linker-tools' ) ) . '</strong>';
		foreach ( $flags as $flag ) {
			$lines[] = esc_html( $this->flag( (string) $flag ) );
		}
		$labels  = is_array( $row['labels'] ) ? $row['labels'] : array();
		$sources = is_array( $row['sources'] ) ? $row['sources'] : array();
		foreach ( array( 'grounded', 'appropriate', 'better_pick' ) as $question ) {
			if ( ! isset( $labels[ $question ] ) ) {
				continue;
			}
			$lines[] = esc_html(
				sprintf(
					/* translators: 1: the question, 2: the answer, 3: the judge that gave it. */
					__( '%1$s: %2$s (%3$s)', 'linker-tools' ),
					$this->question( $question ),
					$this->label( $question, (string) $labels[ $question ] ),
					'deepseek' === ( $sources[ $question ] ?? '' ) ? __( 'second judge', 'linker-tools' ) : 'Jev'
				)
			);
		}
		if ( $row['escalated'] ) {
			$lines[] = esc_html(
				sprintf(
					/* translators: %s: the confidences that fell short, e.g. "grounded 0.42 < 0.6". */
					__( 'Sent to the second judge: %s', 'linker-tools' ),
					implode( '; ', (array) $row['escalation'] )
				)
			);
		}
		foreach ( (array) $row['citations'] as $failure ) {
			$lines[] = esc_html(
				sprintf(
					/* translators: %s: what the citation check found. */
					__( 'Citation: %s', 'linker-tools' ),
					(string) $failure
				)
			);
		}
		foreach ( (array) $row['reasons'] as $judge => $reason ) {
			$lines[] = '<small>' . esc_html( ( 'deepseek' === $judge ? __( 'Second judge', 'linker-tools' ) : 'Jev' ) . ': ' . (string) $reason ) . '</small>';
		}
		return implode( '<br>', $lines );
	}

	/**
	 * A rubric question in words.
	 *
	 * @param string $question Question name.
	 */
	private function question( string $question ): string {
		return match ( $question ) {
			'grounded'    => __( 'Supported by its sources', 'linker-tools' ),
			'appropriate' => __( 'Within Genie\'s remit', 'linker-tools' ),
			default       => __( 'Answer against a wrong pick', 'linker-tools' ),
		};
	}

	/**
	 * A rubric answer in words.
	 *
	 * @param string $question Question name.
	 * @param string $label    The label.
	 */
	private function label( string $question, string $label ): string {
		return match ( $question . ':' . $label ) {
			'grounded:2'      => __( 'yes', 'linker-tools' ),
			'grounded:1'      => __( 'not verifiable', 'linker-tools' ),
			'grounded:0'      => __( 'contradicted', 'linker-tools' ),
			'appropriate:yes' => __( 'yes', 'linker-tools' ),
			'appropriate:no'  => __( 'no', 'linker-tools' ),
			'better_pick:A'   => __( 'the answer is better', 'linker-tools' ),
			'better_pick:B'   => __( 'the wrong pick is better', 'linker-tools' ),
			default           => __( 'no difference', 'linker-tools' ),
		};
	}

	/**
	 * A flag in words.
	 *
	 * @param string $flag Flag name (QualityStore::FLAGS).
	 */
	private function flag( string $flag ): string {
		return match ( $flag ) {
			'contradicted' => __( 'Contradicts what Genie looked up.', 'linker-tools' ),
			'unverifiable' => __( 'States facts Genie did not look up.', 'linker-tools' ),
			'out_of_remit' => __( 'Goes beyond Genie\'s remit.', 'linker-tools' ),
			'worse_pick'   => __( 'A wrong product was judged the better answer.', 'linker-tools' ),
			'citation'     => __( 'States or cites something no lookup returned.', 'linker-tools' ),
			default        => __( 'The judges could not decide.', 'linker-tools' ),
		};
	}

	/**
	 * The conversation's title: its first message, or its number.
	 *
	 * @param WP_Post $post Conversation post.
	 */
	private function title( WP_Post $post ): string {
		$title = trim( $post->post_title );
		if ( '' === $title || Conversations::UNTITLED === $title ) {
			return sprintf(
				/* translators: %d: conversation ID. */
				__( 'Conversation %d', 'linker-tools' ),
				$post->ID
			);
		}
		return $title;
	}

	/**
	 * A Unix time in the site's date and time format.
	 *
	 * @param int $time Unix time.
	 */
	private function time( int $time ): string {
		if ( $time < 1 ) {
			return '—';
		}
		return (string) wp_date( get_option( 'date_format' ) . ' ' . get_option( 'time_format' ), $time );
	}

	/**
	 * The page's URL.
	 */
	private function url(): string {
		return admin_url( 'admin.php?page=' . self::SLUG );
	}
}
