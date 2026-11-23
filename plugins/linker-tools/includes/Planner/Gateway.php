<?php
/**
 * Browser-facing project RPC, with native identity and CSRF protection.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Planner;

use WP_Error;
use WP_REST_Request;
use WP_REST_Response;

/** All commands use POST; no browser-controlled private identity is forwarded. */
final class Gateway {

	public const NAMESPACE = 'linker/v1';
	public const ROUTE     = '/planner';
	/** Deployment policy must match hosting configuration, not engineering scope. */
	public const MAX_BODY_BYTES = 16 * 1024 * 1024;
	public const MAX_JSON_DEPTH = 32;
	/** The account-claim and identity-status commands are deliberately private. */
	private const PATHS = 'inquiry/form|projects/(?:create|delete|list|read|revise|runs)|runs/(?:read|inputs|compare|cancel|energy|calculate|find-equipment|check-equipment|report|pv|direct-beam|geometric-pv|pvgis-reference|equipment(?:-search)?|weather(?:/status)?|trace)|assets/(?:read|content)|profiles/(?:csv|standard|inspect|preview)|weather/(?:assets|preview)|geometry/(?:review|import)|installation/review|battery/scenario|products/(?:current|cards)|equipment/(?:candidates|certificates)/read|recovery/scopes|sources/(?:saved-solution|project-brief(?:/stage)?)|draft/(?:apply|preview|read)|design/commercial|places/(?:lookup|outline)';
	/**
	 * A rejected request stays rejected if an installed integration returns null.
	 *
	 * @var \WeakMap<WP_REST_Request,WP_Error>
	 */
	private \WeakMap $refusals;

	/**
	 * Compose native identity, private transport, recovery and admission.
	 *
	 * @param NativeIdentity $identity Native ownership.
	 * @param Transport      $transport Private service.
	 * @param ClaimOutbox    $claims Durable native login transition.
	 * @param Admission      $admission Owned command dispatch and coordinated project deletion.
	 */
	public function __construct( private readonly NativeIdentity $identity = new NativeIdentity(), private readonly Transport $transport = new Transport(), private readonly ClaimOutbox $claims = new ClaimOutbox(), private readonly Admission $admission = new Admission() ) {
		$this->refusals = new \WeakMap();
	}

	/** Native REST declarations and private response lifecycle. */
	public function register(): void {
		register_rest_route(
			self::NAMESPACE,
			self::ROUTE . '/bootstrap',
			array(
				'methods'             => 'POST',
				'callback'            => array( $this, 'bootstrap' ),
				'permission_callback' => array( $this, 'bootstrap_permission' ),
			)
		);
		register_rest_route(
			self::NAMESPACE,
			self::ROUTE . '/scope',
			array(
				'methods'             => 'POST',
				'callback'            => array( $this, 'scope' ),
				'permission_callback' => array( $this, 'scope_permission' ),
			)
		);
		register_rest_route(
			self::NAMESPACE,
			self::ROUTE . '/rpc/(?P<path>' . self::PATHS . ')',
			array(
				'methods'             => 'POST',
				'callback'            => array( $this, 'forward' ),
				'permission_callback' => array( $this, 'permission' ),
			)
		);
	}

	/** Registered before any REST dispatch, so unknown routes/errors are private. */
	public function lifecycle(): void {
		add_filter( 'linker_tools_planning_inquiry_note', array( $this, 'inquiry_note' ), 10, 3 );
		add_filter( 'linker_tools_planning_inquiry_handoff', array( $this, 'inquiry_handoff' ), 10, 2 );
		add_filter( 'determine_current_user', array( $this->identity, 'rest_nonce_user' ), 25 );
		add_filter( 'rest_pre_dispatch', array( $this, 'before_parse' ), 0, 3 );
		// Installed ACF initialisation returns null even after an earlier error.
		// Native integrations are at priority 10; retain the refusal after them.
		add_filter( 'rest_pre_dispatch', array( $this, 'retain_refusal' ), 100, 3 );
		add_filter( 'rest_post_dispatch', array( $this, 'private_response' ), 20, 3 );
		// After core's rest_send_cors_headers, before bytes are served.
		add_filter( 'rest_pre_serve_request', array( $this, 'serve' ), 100, 4 );
	}

	/**
	 * Guard raw requests before core calls has_valid_params/parse_json_params.
	 *
	 * @param mixed           $result Earlier dispatch decision.
	 * @param mixed           $server Native REST server.
	 * @param WP_REST_Request $request Unparsed native request.
	 * @return mixed Earlier decision or pre-parser refusal.
	 */
	public function before_parse( mixed $result, mixed $server, WP_REST_Request $request ): mixed {
		unset( $server );
		unset( $this->refusals[ $request ] );
		if ( ! self::in_scope( $request ) ) {
			return $result;
		}
		// Native pre-dispatch integrations can parse even unsupported methods
		// before route matching. Every planner body needs the same bound.
		if ( 'POST' !== $request->get_method() && '' === (string) $request->get_body() ) {
			return $result;
		}
		$checked = ( new BodyGate() )->check( $request );
		if ( is_wp_error( $checked ) ) {
			// WP filters all continue after a returned error. Installed native
			// integrations can call get_param() and trigger JSON parsing anyway.
			// The rejected body must not remain available to those parsers.
			$request->set_body( '' );
			$this->refusals[ $request ] = $checked;
			return $checked;
		}
		return $result;
	}

	/**
	 * Reassert this request's bounded-input refusal after native integrations.
	 *
	 * @param mixed           $result Earlier native result.
	 * @param mixed           $server Native REST server.
	 * @param WP_REST_Request $request Current native request.
	 * @return mixed Original refusal or the untouched native result.
	 */
	public function retain_refusal( mixed $result, mixed $server, WP_REST_Request $request ): mixed {
		unset( $server );
		return self::in_scope( $request ) ? ( $this->refusals[ $request ] ?? $result ) : $result;
	}

	/**
	 * Admit only a same-origin bounded bootstrap command.
	 *
	 * @param WP_REST_Request $request Native request.
	 * @return true|WP_Error Allowed bootstrap or bounded same-origin refusal.
	 */
	public function bootstrap_permission( WP_REST_Request $request ): bool|WP_Error {
		if ( ! Origin::allows( $request ) ) {
			return Failure::make( 'origin', 403 );
		}
		$command = $this->bootstrap_command( $request );
		return is_wp_error( $command ) ? $command : true;
	}

	/**
	 * Require a native principal before forwarding project commands.
	 *
	 * @param WP_REST_Request $request Native request.
	 * @return true|WP_Error Native session admission.
	 */
	public function permission( WP_REST_Request $request ): bool|WP_Error {
		if ( ! Origin::allows( $request ) ) {
			return Failure::make( 'origin', 403 );
		}
		$principal = $this->identity->resolve( $request );
		return is_wp_error( $principal ) ? $principal : true;
	}

	/**
	 * Confirm native session ownership and return safe runtime metadata.
	 *
	 * @param WP_REST_Request $request Native bootstrap.
	 * @return WP_REST_Response|WP_Error Confirmed context or a cookie confirmation step.
	 */
	public function bootstrap( WP_REST_Request $request ): WP_REST_Response|WP_Error {
		$command = $this->bootstrap_command( $request );
		if ( is_wp_error( $command ) ) {
			return $command;
		}
		$existing_only = true === ( $command['existing_owner_only'] ?? false );
		$context       = $this->identity->bootstrap( $request, $existing_only );
		if ( is_wp_error( $context ) ) {
			return $context;
		}
		if ( $existing_only ) {
			$recovered = array() === ( new TransitionTicket() )->read_all();
		} else {
			$recovered = $this->claims->recover();
			$this->claims->settle( get_current_user_id() );
		}
		$principal = $context['principal'];
		if ( $context['confirmed'] ) {
			$status = $this->transport->object( $principal, 'identity/status', array( 'schema_version' => 1 ) );
			if ( is_wp_error( $status ) ) {
				return $status;
			}
			if ( 1 !== ( $status['schema_version'] ?? null ) || ! in_array( $status['status'] ?? null, array( 'active', 'retired' ), true ) ) {
				return Failure::make( 'invalid_reply', 502 );
			}
			if ( 'retired' === $status['status'] ) {
				if ( $existing_only || 'guest' !== $principal->kind ) {
					return Failure::make( 'identity', 403 );
				}
				$session = $this->identity->session();
				if ( is_wp_error( $session ) ) {
					return $session;
				}
				$session->destroy_session();
				$context = $this->identity->bootstrap( $request );
				if ( is_wp_error( $context ) ) {
					return $context;
				}
				$principal = $context['principal'];
			}
		}
		$version = $this->transport->object( $principal, 'version', array( 'schema_version' => 1 ) );
		if ( is_wp_error( $version ) ) {
			return $version;
		}
		if ( 1 !== ( $version['schema_version'] ?? null ) || ! is_string( $version['runtime_sha256'] ?? null ) || 1 !== preg_match( '/\A[a-f0-9]{64}\z/', $version['runtime_sha256'] ) || ! is_array( $version['limits'] ?? null ) || ! is_array( $version['models'] ?? null ) ) {
			return Failure::make( 'invalid_reply', 502 );
		}
		foreach ( array( 'max_body_bytes', 'max_csv_bytes', 'max_page_size', 'max_json_depth' ) as $limit ) {
			if ( ! is_int( $version['limits'][ $limit ] ?? null ) || $version['limits'][ $limit ] < 1 ) {
				return Failure::make( 'invalid_reply', 502 );
			}
		}
		$has_visibility = array_key_exists( 'direct_beam_visibility', $version['models'] ) || array_key_exists( 'direct_beam_visibility', $version['limits'] );
		if ( $has_visibility ) {
			$visibility_limits = $version['limits']['direct_beam_visibility'] ?? null;
			$names             = array( 'index_leaf_size', 'max_bounds_checks', 'max_ray_face_checks', 'max_samples', 'max_selected_rows' );
			if ( 'prepare_direct_beam_visibility_v1' !== ( $version['models']['direct_beam_visibility'] ?? null ) || ! is_array( $visibility_limits ) ) {
				return Failure::make( 'invalid_reply', 502 );
			}
			$keys = array_keys( $visibility_limits );
			sort( $keys );
			if ( $names !== $keys ) {
				return Failure::make( 'invalid_reply', 502 );
			}
			foreach ( $names as $name ) {
				if ( ! is_int( $visibility_limits[ $name ] ) || $visibility_limits[ $name ] < 1 ) {
					return Failure::make( 'invalid_reply', 502 );
				}
			}
		}
		$has_geometric = array_key_exists( 'geometric_pv_generation', $version['models'] ) || array_key_exists( 'geometric_pv_generation', $version['limits'] );
		if ( $has_geometric ) {
			$geometric_limits = $version['limits']['geometric_pv_generation'] ?? null;
			$names            = array( 'index_leaf_size', 'max_bounds_checks', 'max_module_steps', 'max_ray_face_checks', 'max_samples' );
			if ( 'prepare_geometric_pv_reference_v1' !== ( $version['models']['geometric_pv_generation'] ?? null ) || ! is_array( $geometric_limits ) ) {
				return Failure::make( 'invalid_reply', 502 );
			}
			$keys = array_keys( $geometric_limits );
			sort( $keys );
			if ( $names !== $keys ) {
				return Failure::make( 'invalid_reply', 502 );
			}
			foreach ( $names as $name ) {
				if ( ! is_int( $geometric_limits[ $name ] ) || $geometric_limits[ $name ] < 1 ) {
					return Failure::make( 'invalid_reply', 502 );
				}
			}
		}
		foreach ( array( 'geometric_pv_clear_flat_roof', 'geometric_pv_clear_pitched_roof' ) as $profile ) {
			if ( ! array_key_exists( $profile, $version['limits'] ) ) {
				continue;
			}
			// Measured deployment ceilings: 96 modules over a complete 8,760
			// interval year, the sampling upper bound that implies, and the
			// isolated cgroup envelope's string/row bounds.
			$expanded = $version['limits'][ $profile ];
			$bounds   = array(
				'max_module_steps' => 841000,
				'max_modules'      => 96,
				'max_samples'      => 4300000,
				'max_strings'      => 6,
				'max_weather_rows' => 8760,
			);
			if ( ! $has_geometric || ! is_array( $expanded ) ) {
				return Failure::make( 'invalid_reply', 502 );
			}
			$keys = array_keys( $expanded );
			sort( $keys );
			if ( array_keys( $bounds ) !== $keys ) {
				return Failure::make( 'invalid_reply', 502 );
			}
			foreach ( $bounds as $key => $maximum ) {
				if ( ! is_int( $expanded[ $key ] ) || $expanded[ $key ] < 1 || $expanded[ $key ] > $maximum ) {
					return Failure::make( 'invalid_reply', 502 );
				}
			}
		}
		$version['limits']['max_body_bytes'] = min( self::MAX_BODY_BYTES, $version['limits']['max_body_bytes'] );
		$version['limits']['max_json_depth'] = min( self::MAX_JSON_DEPTH, $version['limits']['max_json_depth'] );
		// Keep operator process/storage identities on the private protocol; the
		// browser uses its stable, strict runtime view during normal bootstrap.
		$version           = array_intersect_key( $version, array_flip( array( 'schema_version', 'runtime_sha256', 'models', 'limits' ) ) );
		$version['limits'] = array_intersect_key( $version['limits'], array_flip( array( 'max_body_bytes', 'max_csv_bytes', 'max_page_size', 'max_json_depth', 'direct_beam_visibility', 'geometric_pv_generation', 'geometric_pv_clear_flat_roof', 'geometric_pv_clear_pitched_roof' ) ) );
		return new WP_REST_Response(
			array(
				'schema_version'   => 1,
				'kind'             => $principal->kind,
				'cookie_confirmed' => $context['confirmed'],
				'expires_at'       => $context['expires'],
				'query_scope'      => $context['query_scope'],
				'nonce'            => $context['nonce'],
				'claim_pending'    => ! $recovered || $this->claims->pending( get_current_user_id() ),
				'runtime'          => $version,
			)
		);
	}

	/**
	 * Admit only the same-origin probe; identity is resolved once in scope().
	 *
	 * @param WP_REST_Request $request Native scope probe.
	 * @return true|WP_Error Allowed same-origin probe or refusal.
	 */
	public function scope_permission( WP_REST_Request $request ): bool|WP_Error {
		if ( ! Origin::allows( $request ) ) {
			return Failure::make( 'origin', 403 );
		}
		return true;
	}

	/**
	 * Lightest session revalidation: only the scope the browser compares.
	 *
	 * Unlike bootstrap this neither recovers claims nor contacts the private
	 * service, so a tab refocus costs one native identity resolution.
	 *
	 * @param WP_REST_Request $request Verified native scope probe.
	 * @return WP_REST_Response|WP_Error Current query_scope or explicit refusal.
	 */
	public function scope( WP_REST_Request $request ): WP_REST_Response|WP_Error {
		$scope = $this->identity->scope( $request );
		if ( is_wp_error( $scope ) ) {
			return $scope;
		}
		return new WP_REST_Response(
			array(
				'schema_version' => 1,
				'query_scope'    => $scope,
			)
		);
	}

	/**
	 * Forward an allowlisted command under the verified native owner.
	 *
	 * @param WP_REST_Request $request Verified native RPC.
	 * @return WP_REST_Response|WP_Error Actual owned protocol result.
	 */
	public function forward( WP_REST_Request $request ): WP_REST_Response|WP_Error {
		$principal = $this->identity->resolve( $request );
		if ( is_wp_error( $principal ) ) {
			return $principal;
		}
		$path = strtolower( (string) ( $request->get_url_params()['path'] ?? '' ) );
		if ( 'recovery/scopes' === $path ) {
			$command = $this->command( $request );
			if ( is_wp_error( $command ) ) {
				return $command;
			}
			$keys = array_keys( $command );
			sort( $keys );
			if ( array( 'after', 'schema_version' ) !== $keys || 1 !== $command['schema_version'] || ( null !== $command['after'] && ! is_string( $command['after'] ) ) ) {
				return Failure::make( 'recovery_input', 422 );
			}
			$registry = new RecoveryScopes();
			$user     = get_current_user_id();
			if ( $user > 0 && ! $registry->remember( $user, NativeIdentity::query_scope( $principal, wp_get_session_token() ) ) ) {
				return Failure::make( 'recovery_unavailable', 503 );
			}
			$page = $registry->page( $user, $command['after'] );
			return is_wp_error( $page ) ? $page : new WP_REST_Response( $page );
		}
		if ( 1 !== preg_match( '~\A(?:' . self::PATHS . ')\z~', $path ) ) {
			return Failure::make( 'path', 404 );
		}
		$command = $this->command( $request );
		if ( is_wp_error( $command ) ) {
			return $command;
		}
		if ( 'assets/content' === $path && array_key_exists( 'series_csv', $command ) ) {
			$download = SeriesDownload::fetch( $principal, $command, $this->transport );
			return is_wp_error( $download ) ? $download : new WP_REST_Response(
				$download,
				200,
				array(
					'Content-Type'        => 'application/octet-stream',
					'Content-Disposition' => 'attachment; filename="project-asset.csv"',
					'Content-Length'      => (string) $download->size,
				)
			);
		}
		if ( 'sources/saved-solution' === $path ) {
			$source = ( new SavedSolutionSource() )->read( $principal, $command );
			return is_wp_error( $source ) ? $source : new WP_REST_Response( $source );
		}
		if ( 'sources/project-brief' === $path ) {
			$source = ( new ProjectBriefSource() )->read( $principal, $command );
			return is_wp_error( $source ) ? $source : new WP_REST_Response( $source );
		}
		if ( 'sources/project-brief/stage' === $path ) {
			$staged = ( new ProjectBriefSource() )->stage( $principal, $command );
			return is_wp_error( $staged ) ? $staged : new WP_REST_Response( $staged );
		}
		if ( 'inquiry/form' === $path ) {
			return $this->inquiry_form( $principal, $command );
		}
		if ( 'products/cards' === $path ) {
			$ids = $command['product_ids'] ?? null;
			if ( 1 !== ( $command['schema_version'] ?? null ) || ! in_array( $command['lang'] ?? null, array( 'en', 'de' ), true ) || ! is_array( $ids ) || ! array_is_list( $ids ) || array_filter( $ids, static fn ( $id ) => ! is_int( $id ) || $id < 1 ) ) {
				return Failure::make( 'input', 422 );
			}
			$cards = array();
			foreach ( \Linker\Commerce\Planning\Module::product_cards( $ids, $command['lang'] ) as $id => $card ) {
				$cards[] = array( 'id' => $id ) + $card;
			}
			return new WP_REST_Response( array( 'cards' => $cards ) );
		}
		if ( 'equipment/certificates/read' === $path ) {
			return ( new CertificateEvidence() )->read( $principal, $command, $this->transport );
		}
		if ( 'design/commercial' === $path ) {
			$sized = ( new CommercialDesign() )->forward( $principal, $command );
			if ( is_wp_error( $sized ) ) {
				return $sized;
			}
			$value = json_decode( $sized['body'], false, 64 );
			if ( ! $value instanceof \stdClass || ! JsonNumbers::supported( $value ) ) {
				return Failure::make( 'invalid_reply', 502 );
			}
			return new WP_REST_Response( $value, $sized['status'] );
		}
		if ( str_starts_with( $path, 'draft/' ) ) {
			return ( new DraftTransfer() )->apply( $principal, $command, $this->admission, $this->transport, substr( $path, 6 ) );
		}
		$reply = $this->admission->send( $principal, $path, $command, (string) $request->get_body(), $this->transport );
		if ( is_wp_error( $reply ) ) {
			return $reply;
		}
		if ( 'assets/content' === $path && $reply['status'] < 400 && str_starts_with( $reply['type'], 'application/octet-stream' ) ) {
			return new WP_REST_Response(
				$reply['body'],
				$reply['status'],
				array(
					'Content-Type'        => 'application/octet-stream',
					'Content-Disposition' => 'attachment; filename="project-asset.bin"',
				)
			);
		}
		$data = json_decode( $reply['body'], false, 64 );
		if ( ! $data instanceof \stdClass || ! JsonNumbers::supported( $data ) || ! str_starts_with( $reply['type'], 'application/json' ) ) {
			return Failure::make( 'invalid_reply', 502 );
		}
		return new WP_REST_Response( $data, $reply['status'] );
	}

	/** Render the Woo form only after reading the selected revision under its owner.
	 *
	 * @param Principal           $principal Verified native owner.
	 * @param array<string,mixed> $command    Reviewed project and language.
	 */
	private function inquiry_form( Principal $principal, array $command ): WP_REST_Response|WP_Error {
		$keys = array_keys( $command );
		sort( $keys );
		$report = $command['report_run_id'] ?? null;
		$replay = $command['report_transfer'] ?? null;
		$retry  = $command['retry'] ?? null;
		$base   = array( 'lang', 'project_id', 'revision', 'schema_version' );
		if ( 1 !== ( $command['schema_version'] ?? null ) || ! in_array( $command['lang'] ?? null, array( 'en', 'de' ), true ) || ! is_string( $command['project_id'] ?? null ) || ! is_int( $command['revision'] ?? null ) || $command['revision'] < 1 ) {
			return Failure::make( 'input', 422 );
		}
		if ( null === $report ) {
			if ( $base !== $keys ) {
				return Failure::make( 'input', 422 );
			}
		} elseif ( ! is_string( $report ) || ! self::planning_identifier( $report ) || ! in_array(
			$keys,
			array(
				array( 'lang', 'project_id', 'report_run_id', 'revision', 'schema_version' ),
				array( 'lang', 'project_id', 'report_run_id', 'report_transfer', 'revision', 'schema_version' ),
				array( 'lang', 'project_id', 'report_run_id', 'retry', 'revision', 'schema_version' ),
			),
			true
		) || ( array_key_exists( 'report_transfer', $command ) && ! is_string( $replay ) ) || ( array_key_exists( 'retry', $command ) && ( ! is_string( $retry ) || ! wp_is_uuid( $retry, 4 ) ) ) ) {
			return Failure::make( 'input', 422 );
		}
		$note = $this->read_inquiry_note( $principal, $command['project_id'], $command['revision'] );
		if ( ! is_array( $note ) ) {
			return $note ?? Failure::make( 'invalid_reply', 502 );
		}
		$proposal = null;
		if ( is_string( $report ) ) {
			$binding  = $note['project_id'] . ':' . $note['revision'];
			$retained = null;
			if ( is_string( $retry ) ) {
				/**
				 * The handle belongs to this Woo session and project and only
				 * contains validated fields retained by the native handler.
				 *
				 * @since 0.3.0
				 * @param array|null $retained Prior matching retry state.
				 * @param string     $retry Opaque native handle.
				 * @param string     $binding Exact project revision.
				 * @param string     $report Exact report being retried.
				 */
				$retained = apply_filters( 'linker_commerce_planning_inquiry_retry', null, $retry, $binding, $report ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- Native Commerce retry reader.
				if ( ! is_array( $retained ) ) {
					return Failure::make( 'identity', 403 );
				}
				$replay = $retained['fields']['linker_report_transfer'] ?? null;
			}
			$intent = array(
				'schema_version'    => 1,
				'project_id'        => $note['project_id'],
				'report_run_id'     => $report,
				'expected_revision' => $note['revision'],
				'key'               => wp_generate_uuid4(),
			);
			if ( is_string( $replay ) ) {
				$handoff = explode( ':', $replay, 4 )[1] ?? '';
				if ( ! self::planning_identifier( $handoff ) ) {
					return Failure::make( 'input', 422 );
				}
				$frozen = $this->read_inquiry_handoff( $principal, $handoff );
			} else {
				$encoded = wp_json_encode( $intent );
				if ( ! is_string( $encoded ) ) {
					return Failure::make( 'input', 422 );
				}
				$reply = $this->admission->send( $principal, 'handoffs/prepare', $intent, $encoded, $this->transport );
				if ( is_wp_error( $reply ) ) {
					return $reply;
				}
				$frozen = json_decode( $reply['body'], true );
				if ( ! is_array( $frozen ) || ! str_starts_with( $reply['type'], 'application/json' ) ) {
					return Failure::make( 'invalid_reply', 502 );
				}
				if ( $reply['status'] >= 400 ) {
					return new WP_REST_Response( $frozen, $reply['status'] );
				}
			}
			if ( is_wp_error( $frozen ) ) {
				return $frozen;
			}
			$proposal = array(
				'command'  => $intent,
				'handoff'  => $frozen,
				'replay'   => $replay,
				'retained' => $retained,
			);
		}
		/**
		 * Return the native inquiry form for the visitor's current Woo session.
		 *
		 * @since 0.3.0
		 * @param array|WP_Error|null $form Form response supplied by Commerce.
		 * @param string     $lang Requested form language.
		 * @param array      $note Owner-verified revision and project note.
		 * @param array|null $proposal Owner-verified report and retry state.
		 */
		$form = apply_filters( 'linker_commerce_planning_inquiry_form', null, $command['lang'], $note, $proposal ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- Hook owned by Commerce.
		return is_wp_error( $form ) ? $form : ( is_array( $form ) ? new WP_REST_Response( $form ) : Failure::make( 'configuration', 503 ) );
	}

	/** A native inquiry uses the same account or signed Woo guest as the preview.
	 *
	 * @param mixed  $previous Prior adapter.
	 * @param string $handoff_id Prepared report handoff.
	 * @return array<string,mixed>|WP_Error
	 */
	public function inquiry_handoff( mixed $previous, string $handoff_id ): array|WP_Error {
		unset( $previous );
		$principal = $this->identity->inquiry_submitter();
		return $principal instanceof WP_Error ? $principal : $this->read_inquiry_handoff( $principal, $handoff_id );
	}

	/** Read exactly the owned report handoff, without starting another preparation.
	 *
	 * @param Principal $principal Current native owner.
	 * @param string    $id Prepared report handoff.
	 * @return array<string,mixed>|WP_Error
	 */
	private function read_inquiry_handoff( Principal $principal, string $id ): array|WP_Error {
		if ( ! self::planning_identifier( $id ) ) {
			return Failure::make( 'input', 422 );
		}
		$handoff = $this->transport->object(
			$principal,
			'handoffs/read',
			array(
				'schema_version' => 1,
				'handoff_id'     => $id,
			)
		);
		if ( is_wp_error( $handoff ) ) {
			return $handoff;
		}
		return ( $handoff['id'] ?? null ) === $id ? $handoff : Failure::make( 'invalid_reply', 502 );
	}

	/** Check the exact Planner identifier form before dispatching the private RPC.
	 *
	 * @param string $id Planner project/run/handoff reference.
	 */
	private static function planning_identifier( string $id ): bool {
		return 1 === preg_match( '/\A[a-f0-9]{32}\z/', $id );
	}

	/** Read the selected note again under the native inquiry submitter's identity.
	 *
	 * @param mixed    $previous Earlier filter result.
	 * @param string   $id Selected planner project.
	 * @param int|null $revision Reviewed revision; omitted for legacy note-only reads.
	 * @return array<string,mixed>|WP_Error|null
	 */
	public function inquiry_note( mixed $previous, string $id, ?int $revision = null ): array|WP_Error|null {
		$principal = $this->identity->inquiry_submitter();
		return $principal instanceof WP_Error ? $principal : $this->read_inquiry_note( $principal, $id, $revision );
	}

	/** Resolve the current project, with no handoff or product list.
	 *
	 * @param Principal $principal Verified native owner.
	 * @param string    $id Selected planner project.
	 * @param int|null  $revision Reviewed revision; omitted for legacy note-only reads.
	 * @return array<string,mixed>|WP_Error|null
	 */
	private function read_inquiry_note( Principal $principal, string $id, ?int $revision ): array|WP_Error|null {
		if ( 1 !== preg_match( '/\A[a-f0-9]{32}\z/', $id ) ) {
			return Failure::make( 'input', 422 );
		}
		$project = $this->transport->object(
			$principal,
			'projects/read',
			array(
				'schema_version' => 1,
				'project_id'     => $id,
				'revision'       => $revision,
			)
		);
		if ( $project instanceof WP_Error ) {
			return $project;
		}
		$text = $project['inputs']['brief']['project_note'] ?? '';
		if ( ( $project['id'] ?? null ) !== $id || ! is_int( $project['revision'] ?? null ) || 1 > $project['revision'] || ! is_string( $project['title'] ?? null ) || ! is_string( $text ) ) {
			return Failure::make( 'invalid_reply', 502 );
		}
		if ( null !== $revision && ( $project['revision'] !== $revision || ! is_array( $project['inputs'] ?? null ) || ! in_array( $project['inputs']['brief']['system_scope'] ?? null, array( null, 'new_pv_storage', 'storage_addition', 'pv_only', 'storage_only' ), true ) ) ) {
			return Failure::make( 'invalid_reply', 502 );
		}
		return null === $revision && '' === trim( $text ) ? null : array(
			...( null === $revision ? array() : array( 'inputs' => $project['inputs'] ) ),
			'project_id'    => $id,
			'title'         => $project['title'],
			'revision'      => $project['revision'],
			'note_revision' => (string) $project['revision'],
			'text'          => $text,
		);
	}

	/**
	 * Apply private cache headers to every planner response.
	 *
	 * @param mixed           $response Native response, including core REST errors.
	 * @param mixed           $server Native server.
	 * @param WP_REST_Request $request Native route.
	 * @return mixed Original response with private headers.
	 */
	public function private_response( mixed $response, mixed $server, WP_REST_Request $request ): mixed {
		unset( $server );
		if ( self::in_scope( $request ) && $response instanceof WP_REST_Response ) {
			$response->header( 'Cache-Control', 'no-store, private' );
			$response->header( 'Pragma', 'no-cache' );
			$response->header( 'X-Content-Type-Options', 'nosniff' );
			$response->header( 'X-Robots-Tag', 'noindex, nofollow, nosnippet' );
		}
		return $response;
	}

	/**
	 * Remove public CORS and serve owned asset bytes without JSON encoding.
	 *
	 * @param mixed           $served Previous native serve result.
	 * @param mixed           $response Native response.
	 * @param WP_REST_Request $request Native request.
	 * @param mixed           $server Native server.
	 * @return bool Whether native JSON output was replaced by verified asset bytes.
	 */
	public function serve( mixed $served, mixed $response, WP_REST_Request $request, mixed $server ): bool {
		unset( $server );
		if ( ! self::in_scope( $request ) ) {
			return (bool) $served;
		}
		header_remove( 'Access-Control-Allow-Origin' );
		header_remove( 'Access-Control-Allow-Credentials' );
		header_remove( 'Access-Control-Allow-Headers' );
		header_remove( 'Access-Control-Expose-Headers' );
		if ( ! $served && $response instanceof WP_REST_Response && 'application/octet-stream' === ( $response->get_headers()['Content-Type'] ?? '' ) && $response->get_data() instanceof SeriesDownload ) {
			$response->get_data()->output();
			return true;
		}
		if ( ! $served && $response instanceof WP_REST_Response && 'application/octet-stream' === ( $response->get_headers()['Content-Type'] ?? '' ) && is_string( $response->get_data() ) ) {
			// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- exact owned asset bytes from the verified private RPC, served as attachment with nosniff.
			echo $response->get_data();
			return true;
		}
		return (bool) $served;
	}

	/**
	 * Match the planner namespace including unknown routes.
	 *
	 * @param WP_REST_Request $request Native request.
	 */
	private static function in_scope( WP_REST_Request $request ): bool {
		$route = strtolower( $request->get_route() );
		return '/linker/v1/planner' === $route || str_starts_with( $route, '/linker/v1/planner/' );
	}

	/**
	 * Parse one bounded UTF-8 JSON object without coercing its fields.
	 *
	 * @param WP_REST_Request $request Bounded raw JSON command.
	 * @return array<string,mixed>|WP_Error Parsed object or explicit refusal.
	 */
	private function command( WP_REST_Request $request ): array|WP_Error {
		$checked = ( new BodyGate() )->check( $request );
		if ( is_wp_error( $checked ) ) {
			return $checked;
		}
		$data = json_decode( (string) $request->get_body(), false, self::MAX_JSON_DEPTH + 1 );
		return $data instanceof \stdClass && JsonNumbers::supported( $data ) ? get_object_vars( $data ) : Failure::make( 'input', 400 );
	}

	/**
	 * Accept the legacy command or a strict, order-independent read-only mode.
	 *
	 * @param WP_REST_Request $request Bounded bootstrap command.
	 * @return array<string,mixed>|WP_Error Valid command or explicit refusal.
	 */
	private function bootstrap_command( WP_REST_Request $request ): array|WP_Error {
		$command = $this->command( $request );
		if ( is_wp_error( $command ) ) {
			return $command;
		}
		$keys = array_keys( $command );
		sort( $keys );
		if ( 1 !== ( $command['schema_version'] ?? null ) || ( array( 'schema_version' ) !== $keys && ( array( 'existing_owner_only', 'schema_version' ) !== $keys || true !== $command['existing_owner_only'] ) ) ) {
			return Failure::make( 'input', 400 );
		}
		return $command;
	}
}
