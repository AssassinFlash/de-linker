<?php
/**
 * Read the currently viewed saved project through its native owner/session.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Planner;

use Linker\Commerce\Presentation\PageUrls;
use WP_REST_Request;

/** Browser data selects a reference; it never supplies project facts. */
final class GenieContext {

	/**
	 * Existing private owner verification and transport.
	 *
	 * @param NativeIdentity $identity Native cookie and nonce verification.
	 * @param Transport      $transport Private project transport.
	 */
	public function __construct( private readonly NativeIdentity $identity = new NativeIdentity(), private readonly Transport $transport = new Transport() ) {}

	/**
	 * Validate only the public reference fields shared by the two React roots.
	 *
	 * @param mixed $raw Browser page context.
	 * @return array<string,mixed>
	 */
	public static function reference( mixed $raw ): array {
		if ( ! is_array( $raw ) || ! is_string( $raw['planning_project_id'] ?? null ) || 1 !== preg_match( '/\A[a-f0-9]{32}\z/', $raw['planning_project_id'] ) || ! is_int( $raw['planning_revision'] ?? null ) || $raw['planning_revision'] < 1 ) {
			return array();
		}
		$runs = $raw['planning_run_ids'] ?? array();
		if ( ! is_array( $runs ) || ! array_is_list( $runs ) || count( $runs ) > 2 || ! is_bool( $raw['planning_unsaved'] ?? false ) ) {
			return array();
		}
		foreach ( $runs as $run ) {
			if ( ! is_string( $run ) || 1 !== preg_match( '/\A[a-f0-9]{32}\z/', $run ) ) {
				return array();
			}
		}
		if ( count( array_unique( $runs ) ) !== count( $runs ) ) {
			return array();
		}
		return array(
			'planning_project_id' => $raw['planning_project_id'],
			'planning_revision'   => $raw['planning_revision'],
			'planning_run_ids'    => $runs,
			'planning_unsaved'    => true === ( $raw['planning_unsaved'] ?? false ),
		);
	}

	/**
	 * Attach server-read facts; a browser-supplied snapshot is never forwarded.
	 *
	 * @param WP_REST_Request     $request Native Genie turn with existing nonce headers.
	 * @param array<string,mixed> $page Sanitized page reference.
	 * @param string              $locale Native turn language.
	 * @return array<string,mixed>|null Verified snapshot or a private unavailable state.
	 */
	public function read( WP_REST_Request $request, array $page, string $locale ): ?array {
		$reference = self::reference( $page );
		if ( array() === $reference ) {
			return null;
		}
		$unavailable = array(
			'schema_version' => 1,
			'status'         => 'unavailable',
		);
		$principal   = $this->identity->resolve( $request );
		if ( is_wp_error( $principal ) ) {
			return $unavailable;
		}
		$reply = $this->transport->object(
			$principal,
			'projects/assistant',
			array(
				'schema_version'  => 1,
				'project_id'      => $reference['planning_project_id'],
				'revision'        => $reference['planning_revision'],
				'run_ids'         => $reference['planning_run_ids'],
				'locale'          => $locale,
				'unsaved_changes' => $reference['planning_unsaved'],
			)
		);
		if ( is_wp_error( $reply ) || 1 !== ( $reply['schema_version'] ?? null ) || ! in_array( $reply['status'] ?? '', array( 'available', 'unsaved_changes' ), true ) || ! is_array( $reply['project'] ?? null ) || ( $reply['project']['id'] ?? null ) !== $reference['planning_project_id'] || ( $reply['project']['revision'] ?? null ) !== $reference['planning_revision'] || ! is_array( $reply['rows'] ?? null ) || ! is_array( $reply['runs'] ?? null ) ) {
			return $unavailable;
		}
		if ( 'available' === $reply['status'] && array_column( $reply['runs'], 'id' ) !== $reference['planning_run_ids'] ) {
			return $unavailable;
		}
		$url = class_exists( PageUrls::class ) ? PageUrls::translated( 'solution-configurator', $locale ) : '';
		if ( '' === $url ) {
			return $unavailable;
		}
		$query = array( 'project' => $reference['planning_project_id'] );
		if ( 1 === count( $reference['planning_run_ids'] ) ) {
			$query['run'] = $reference['planning_run_ids'][0];
		} elseif ( 2 === count( $reference['planning_run_ids'] ) ) {
			$query['compare'] = implode( ',', $reference['planning_run_ids'] );
		}
		$reply['workspace_url'] = add_query_arg( $query, $url ) . ( array() === $reference['planning_run_ids'] ? '#lp-overview' : '#lp-calculations' );
		return $reply;
	}
}
