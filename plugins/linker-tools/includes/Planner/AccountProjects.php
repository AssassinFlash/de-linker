<?php
/**
 * Current account projects from the workbench's existing private index.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Planner;

use WP_Error;

/** No second project store or browser-supplied owner is involved. */
final class AccountProjects {

	/** Account preview policy; the workbench retains the complete paged index. */
	private const PAGE_SIZE = 10;
	/** Mirrors ProjectCreate.title and the application's readProtocol schema. */
	private const MAX_TITLE_LENGTH = 256;

	/**
	 * Reuse the existing bounded private transport.
	 *
	 * @param Transport $transport Native engine transport.
	 */
	public function __construct( private readonly Transport $transport = new Transport() ) {}

	/** Register the server-only account data seam. */
	public function register(): void {
		add_filter( 'linker_commerce_planning_projects', array( $this, 'read' ) );
	}

	/**
	 * Project summaries for the current native account only.
	 *
	 * @param mixed $previous Previous adapter result.
	 * @return list<array{id:string,title:string,updated_at:float|int}>|WP_Error
	 * @phpstan-impure Reads the current native account and project service on every call.
	 */
	public function read( mixed $previous ): array|WP_Error {
		unset( $previous );
		$user = get_current_user_id();
		if ( $user <= 0 ) {
			return Failure::make( 'identity', 403 );
		}
		$page = $this->transport->object(
			new Principal( 'user', NativeIdentity::user_subject( $user ) ),
			'projects/list',
			array(
				'schema_version' => 1,
				'page_size'      => self::PAGE_SIZE,
				'after'          => null,
			)
		);
		if ( is_wp_error( $page ) ) {
			return $page;
		}
		$items = $page['items'] ?? null;
		if ( ! is_array( $items ) || ! array_is_list( $items ) || count( $items ) > self::PAGE_SIZE ) {
			return Failure::make( 'invalid_reply', 502 );
		}
		$projects = array();
		foreach ( $items as $item ) {
			if ( ! is_array( $item ) || ! is_string( $item['id'] ?? null ) || 1 !== preg_match( '/\A[a-f0-9]{32}\z/', $item['id'] ) || ! is_string( $item['title'] ?? null ) || '' === trim( $item['title'] ) || mb_strlen( $item['title'], 'UTF-8' ) > self::MAX_TITLE_LENGTH || ! ( is_int( $item['updated_at'] ?? null ) || is_float( $item['updated_at'] ?? null ) ) || ! is_finite( (float) $item['updated_at'] ) || $item['updated_at'] < 0 ) {
				return Failure::make( 'invalid_reply', 502 );
			}
			$projects[] = array(
				'id'         => $item['id'],
				'title'      => $item['title'],
				'updated_at' => $item['updated_at'],
			);
		}
		return $projects;
	}
}
