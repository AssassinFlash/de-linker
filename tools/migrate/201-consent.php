<?php
/**
 * Replays native CookieYes configuration. Invoked by 201-consent.py via WP-CLI.
 *
 * @package Linker\Migrate
 */

// WP-CLI eval-file evaluates this source inside its runner; strict_types cannot
// appear there (same transport as the engineering-data migration).

use Linker\I18n\Languages;
use Linker\I18n\LinkLocalizer;
use Linker\I18n\Twins;
use Linker\I18n\Translation\Aligner;
use Linker\I18n\Translation\DeepSeekClient;
use Linker\I18n\Translation\Fields;
use Linker\I18n\Translation\HtmlTokenizer;
use Linker\I18n\Translation\Planner;
use Linker\I18n\Translation\Rules;
use Linker\I18n\Translation\Segmenter;
use Linker\I18n\Translation\State;
use Linker\I18n\Translation\Translator;
use Linker\I18n\Translation\Validator;
use Linker\I18n\Woo\Projection;

if ( ! defined( 'WP_CLI' ) || ! WP_CLI ) {
	exit( 1 );
}

try {
	( static function ( string $encoded ): void {
	// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_decode -- JSON payload transported as one WP-CLI argument, never executable code.
		$decoded = base64_decode( $encoded, true );
		if ( false === $decoded ) {
			throw new RuntimeException( 'Invalid JSON transport.' );
		}
		$payload = json_decode( $decoded, true, 512, JSON_THROW_ON_ERROR );
		$plan    = $payload['plan'];
		$write   = $payload['write'];

		if ( ! class_exists( 'CookieYes\\Lite\\Admin\\Modules\\Settings\\Includes\\Settings' ) || ! function_exists( 'wp_has_consent' ) ) {
			WP_CLI::error( 'CookieYes and WP Consent API must be active.' );
		}
		if ( $write && ! current_user_can( 'manage_options' ) ) {
			WP_CLI::error( 'Use --user with an administrator.' );
		}
		if ( $write && 'de-linker.com' === wp_parse_url( home_url(), PHP_URL_HOST ) && ! $payload['production'] ) {
			WP_CLI::error( 'Production writes require --production.' );
		}
		$drift                            = array();
		$settings                         = new \CookieYes\Lite\Admin\Modules\Settings\Includes\Settings();
		$desired                          = $settings->get();
		$desired['languages']['default']  = 'en';
		$desired['languages']['selected'] = array( 'en', 'de' );
		// Standalone plugin: no CookieYes SaaS account or external consent logs.
		$desired['consent_logs']['status'] = false;
		if ( $settings->get() !== $desired ) {
			$drift[] = 'CookieYes languages and local consent storage';
			if ( $write ) {
				$settings->update( $desired ); }
		}
		$controller = \CookieYes\Lite\Admin\Modules\Banners\Includes\Controller::get_instance();
		$categories = \CookieYes\Lite\Admin\Modules\Cookies\Includes\Category_Controller::get_instance();
		$cookies    = \CookieYes\Lite\Admin\Modules\Cookies\Includes\Cookie_Controller::get_instance();
		if ( $write ) {
			$categories->install_tables();
			$cookies->install_tables();
			$controller->install_tables();
		}
		$banner = $controller->get_active_banner();
		if ( ! $banner ) {
			throw new RuntimeException( 'Native CookieYes banner has not been initialized.' ); }
		$config                          = $banner->get_settings();
		$config['settings']['type']      = 'banner';
		$config['settings']['position']  = 'bottom';
		$config['settings']['languages'] = $desired['languages'];
		// Owner ruling 2026-10-19: these colours stay in CookieYes's own
		// settings. AGENTS.md §5 styles site pages, not this CMP surface.
		// Do not move the colours to WindPress and do not change them.
		foreach ( array( 'notice', 'preferenceCenter' ) as $panel ) {
			foreach ( array( 'accept', 'reject', 'save' ) as $button ) {
				if ( isset( $config['config'][ $panel ]['elements']['buttons']['elements'][ $button ] ) ) {
					$config['config'][ $panel ]['elements']['buttons']['elements'][ $button ]['styles'] = array(
						'color'            => '#ffffff',
						'background-color' => '#1f625a',
						'border-color'     => '#1f625a',
					);
				}
			}
		}
		$config['config']['notice']['elements']['buttons']['elements']['settings']['styles'] = array(
			'color'            => '#1f625a',
			'background-color' => 'transparent',
			'border-color'     => '#d7dde4',
		);
		$config['config']['notice']['elements']['title']['styles']['color']                  = '#183d36';
		$config['config']['notice']['elements']['description']['styles']['color']            = '#596e67';
		$config['config']['revisitConsent']['status']                                        = false;
		$config['config']['revisitConsent']['styles']['background-color']                    = '#1f625a';
		$contents = $banner->get_contents();
		foreach ( $plan['copy'] as $lang => $copy ) {
			$entry                                      = $contents[ $lang ] ?? $banner->get_translations( $lang );
			$entry['notice']['elements']['title']       = $copy['header'];
			$entry['notice']['elements']['description'] = '<p>' . $copy['message_optin'] . '</p>';
			$entry['notice']['elements']['buttons']['elements']['accept']           = $copy['accept'];
			$entry['notice']['elements']['buttons']['elements']['reject']           = $copy['dismiss'];
			$entry['notice']['elements']['buttons']['elements']['settings']         = $copy['view_preferences'];
			$entry['preferenceCenter']['elements']['title']                         = $copy['header'];
			$entry['preferenceCenter']['elements']['description']                   = '<p>' . $copy['message_optin'] . '</p>';
			$entry['preferenceCenter']['elements']['buttons']['elements']['accept'] = $copy['accept'];
			$entry['preferenceCenter']['elements']['buttons']['elements']['reject'] = $copy['dismiss'];
			$entry['preferenceCenter']['elements']['buttons']['elements']['save']   = $copy['save_preferences'];
			$entry['revisitConsent']['elements']['title']                           = $copy['revoke'];
			if ( 'de' === $lang ) {
				$entry['notice']['elements']['closeButton']                               = 'Schließen';
				$entry['preferenceCenter']['elements']['closeButton']                     = 'Schließen';
				$entry['preferenceCenter']['elements']['category']['elements']['enable']  = 'Aktivieren';
				$entry['preferenceCenter']['elements']['category']['elements']['disable'] = 'Deaktivieren';
			}
			$contents[ $lang ] = $entry;
		}
		// phpcs:ignore Universal.Operators.StrictComparisons.LooseNotEqual -- Native sanitizers preserve values but reorder associative language keys.
		if ( $banner->get_settings() != $config || $banner->get_contents() != $contents ) {
			$drift[] = 'CookieYes banner settings and independent EN/DE copy';
			if ( $write ) {
				$banner->set_settings( $config );
				$banner->set_contents( $contents );
				$banner->save(); }
		}
		$category_ids = array();
		foreach ( $categories->get_items() as $row ) {
			$category              = new \CookieYes\Lite\Admin\Modules\Cookies\Includes\Cookie_Categories( $row );
			$slug                  = $category->get_slug();
			$category_ids[ $slug ] = $category->get_id();
			$labels                = array();
			$descriptions          = array();
			$keys                  = array(
				'necessary'     => array( 'category_functional', 'functional_text' ),
				'analytics'     => array( 'category_stats', 'statistics_text' ),
				'advertisement' => array( 'category_all', 'marketing_text' ),
			);
			if ( ! isset( $keys[ $slug ] ) ) {
				if ( $category->get_visibility() ) {
					$drift[] = 'hide unused category: ' . $slug;
					if ( $write ) {
						$category->set_visibility( false );
						$category->save(); }
				}
				continue;
			}
			foreach ( $plan['copy'] as $lang => $copy ) {
				$labels[ $lang ]       = $copy[ $keys[ $slug ][0] ];
				$descriptions[ $lang ] = '<p>' . $copy[ $keys[ $slug ][1] ] . '</p>';
			}
			if ( $category->get_name() !== $labels || $category->get_description() !== $descriptions ) {
				$drift[] = 'category: ' . $slug;
				if ( $write ) {
					$category->set_name( $labels );
					$category->set_description( $descriptions );
					$category->save(); }
			}
		}
		$existing = array();
		foreach ( $cookies->get_items() as $row ) {
			$existing[ $row->name ] = $row; }
		foreach ( array( array( '_ga', 'analytics', 'googletagmanager.com' ), array( '_ga_*', 'analytics', 'google-analytics.com' ), array( 'sbjs_*', 'advertisement', '' ) ) as $definition ) {
			if ( isset( $existing[ $definition[0] ] ) ) {
				$registered = new \CookieYes\Lite\Admin\Modules\Cookies\Includes\Cookie( (int) $existing[ $definition[0] ]->cookie_id );
				if ( $registered->get_url_pattern() !== $definition[2] || $registered->get_category() !== $category_ids[ $definition[1] ] ) {
					$drift[] = 'cookie provider/category: ' . $definition[0];
					if ( $write ) {
						$registered->set_url_pattern( $definition[2] );
						$registered->set_category( $category_ids[ $definition[1] ] );
						$registered->save(); }
				}
				continue;
			}
			$drift[] = 'cookie: ' . $definition[0];
			if ( $write ) {
				$cookie = new \CookieYes\Lite\Admin\Modules\Cookies\Includes\Cookie();
				$cookie->set_name( $definition[0] );
				$cookie->set_category( $category_ids[ $definition[1] ] );
				$cookie->set_domain( '' );
				$cookie->set_url_pattern( $definition[2] );
				$cookie->set_duration(
					array(
						'en' => 'See privacy policy',
						'de' => 'Siehe Datenschutzerklärung',
					)
				);
				$cookie->set_description(
					array(
						'en' => $plan['copy']['en'][ 'analytics' === $definition[1] ? 'statistics_text' : 'marketing_text' ],
						'de' => $plan['copy']['de'][ 'analytics' === $definition[1] ? 'statistics_text' : 'marketing_text' ],
					)
				);
				$cookie->save();
			}
		}

		// Change only the two GA4-related sections. Keep the surrounding LC
		// document, other processors, page language and Polylang pair intact.
		$english = get_page_by_path( 'privacy-policy' );
		$german  = $english instanceof WP_Post ? get_post( pll_get_post( $english->ID, 'de' ) ) : null;
		if ( ! $english instanceof WP_Post || ! $german instanceof WP_Post ) {
			throw new RuntimeException( 'Both privacy-policy pages must exist.' );
		}
		$patch           = static function ( string $html, array $copy ): string {
			$count  = 0;
			$result = preg_replace_callback(
				'~(<section id="section-3">\s*<h2[^>]*>.*?</h2>).*?(</section>)~s',
				static fn( array $parts ): string => $parts[1] . "\n        " . $copy['cookies'] . "\n      " . $parts[2],
				$html,
				1,
				$count
			);
			if ( null === $result || 1 !== $count ) {
				throw new RuntimeException( 'Privacy cookie section structure differs; refusing to replace it.' );
			}
			$result = preg_replace( '~\s*<p data-linker-ga4-privacy="1">.*?</p>~s', '', $result );
			if ( null === $result || 1 !== substr_count( $result, '<section id="section-4">' ) ) {
				throw new RuntimeException( 'Privacy recipients section structure differs.' );
			}
			$patched = preg_replace_callback( '~(<section id="section-4">\s*<h2[^>]*>.*?</h2>)~s', static fn( array $parts ): string => $parts[1] . "\n        " . $copy['recipient'], $result );
			if ( null === $patched ) {
				throw new RuntimeException( 'Invalid privacy recipient replacement.' ); }
			return $patched;
		};
		$english_content = $patch( $english->post_content, $plan['privacy']['en'] );
		$german_content  = $patch( $german->post_content, $plan['privacy']['de'] );
		if ( $english_content !== $english->post_content || $german_content !== $german->post_content ) {
			$drift[] = 'privacy: cookies and Google recipient, EN/DE';
			if ( $write ) {
				// Captured before either language is written. A failure restores both.
				$previous_en     = $english->post_content;
				$previous_de     = $german->post_content;
				$restore         = static function () use ( $english, $german, $previous_en, $previous_de ): void {
					foreach ( array( array( $english->ID, $previous_en ), array( $german->ID, $previous_de ) ) as $pair ) {
						$restored = wp_update_post(
							array(
								'ID'           => $pair[0],
								'post_content' => wp_slash( $pair[1] ),
							),
							true,
							false
						);
						if ( is_wp_error( $restored ) ) {
							// phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- CLI exception text goes to stderr, never an HTML response.
							throw new RuntimeException( 'Could not restore privacy page ' . $pair[0] . ': ' . $restored->get_error_message() );
						}
					}
				};
				$privacy_failure = null;
				try {
					// The pair is supplied together. Do not enqueue an automatic
					// translation between the English write and native adoption.
					$updated = wp_update_post(
						array(
							'ID'           => $english->ID,
							'post_content' => wp_slash( $english_content ),
						),
						true,
						false
					);
					if ( is_wp_error( $updated ) ) {
						throw new RuntimeException( $updated->get_error_message() );
					}
					$languages  = new Languages();
					$tokenizer  = new HtmlTokenizer();
					$links      = new LinkLocalizer( $languages, $tokenizer );
					$rules      = Rules::load( WP_PLUGIN_DIR . '/linker-i18n/data' );
					$translator = new Translator( $languages, new Planner( new Segmenter( $tokenizer ), new Aligner() ), new Fields(), new State(), DeepSeekClient::from_environment( $rules ), new Validator( $rules ), new Twins( $languages, $links, new Projection( $languages ) ), $links );
					$fields     = array();
					foreach ( ( new Fields() )->of_post( $english ) as $field => $definition ) {
						$fields[ $field ] = str_starts_with( $field, Fields::META ) ? (string) get_post_meta( $german->ID, substr( $field, strlen( Fields::META ) ), true ) : $german->$field;
					}
					$fields['post_content'] = $german_content;
					$translator->adopt( State::POST, $english->ID, $fields );
					clean_post_cache( $english->ID );
					clean_post_cache( $german->ID );
					$read_en = get_post( $english->ID );
					$read_de = get_post( $german->ID );
					if ( ! $read_en instanceof WP_Post || $read_en->post_content !== $english_content || ! $read_de instanceof WP_Post || $read_de->post_content !== $german_content ) {
						throw new RuntimeException( 'Privacy pages did not read back.' );
					}
				} catch ( Throwable $failure ) {
					$privacy_failure = $failure;
				}
				if ( $privacy_failure instanceof Throwable ) {
					try {
						$restore();
					} catch ( Throwable $restore_failure ) {
						// phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- CLI exception text goes to stderr, never an HTML response.
						throw new RuntimeException( $privacy_failure->getMessage() . ' Restore also failed: ' . $restore_failure->getMessage(), 0, $privacy_failure );
					}
					// phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- CLI exception text goes to stderr, never an HTML response.
					throw new RuntimeException( $privacy_failure->getMessage() . ' Previous privacy sections were restored.', 0, $privacy_failure );
				}
			}
		}
		$consent_settings = get_option( 'googlesitekit_consent_mode', array() );
		if ( true !== ( $consent_settings['enabled'] ?? null ) ) {
			$drift[] = 'Site Kit Consent Mode';
			if ( $write ) {
				$consent_settings['enabled'] = true;
				update_option( 'googlesitekit_consent_mode', $consent_settings );
			}
		}
		if ( $write ) {
			delete_option( 'cky_banner_template' );
			\CookieYes\Lite\Includes\Cache::delete( 'banner_template' );
		}
		if ( ! empty( $payload['export'] ?? null ) ) {
			$cookie_rows = array();
			foreach ( $cookies->get_items() as $row ) {
				$registered    = new \CookieYes\Lite\Admin\Modules\Cookies\Includes\Cookie( (int) $row->cookie_id );
				$cookie_rows[] = array(
					'name'        => (string) $row->name,
					'category'    => $registered->get_category(),
					'url_pattern' => $registered->get_url_pattern(),
				);
			}
			$category_rows = array();
			foreach ( $categories->get_items() as $row ) {
				$category        = new \CookieYes\Lite\Admin\Modules\Cookies\Includes\Cookie_Categories( $row );
				$category_rows[] = array(
					'slug'        => $category->get_slug(),
					'name'        => $category->get_name(),
					'description' => $category->get_description(),
					'visibility'  => $category->get_visibility(),
				);
			}
			$encoded_snapshot = wp_json_encode(
				array(
					'home'                       => home_url(),
					'settings'                   => $settings->get(),
					'banner'                     => array(
						'settings' => $banner->get_settings(),
						'contents' => $banner->get_contents(),
					),
					'categories'                 => $category_rows,
					'cookies'                    => $cookie_rows,
					'privacy'                    => array(
						'en_id' => $english->ID,
						'de_id' => $german->ID,
						'en'    => $english->post_content,
						'de'    => $german->post_content,
					),
					'googlesitekit_consent_mode' => get_option( 'googlesitekit_consent_mode', array() ),
					'cky_banner_template'        => get_option( 'cky_banner_template', null ),
				)
			);
			if ( false === $encoded_snapshot ) {
				throw new RuntimeException( 'Could not encode the consent backup.' );
			}
			WP_CLI::log( '@@201-consent@@' . $encoded_snapshot );
			return;
		}
		$output = wp_json_encode(
			array(
				'write' => $write,
				'drift' => $drift,
			),
			JSON_UNESCAPED_SLASHES
		);
		if ( false === $output ) {
			throw new RuntimeException( 'Could not encode verification result.' );
		}
		WP_CLI::log( $output );
		if ( ! $write && count( $drift ) > 0 ) {
			WP_CLI::error( 'Consent configuration differs from its plan.' );
		}
	} )( '__LINKER_CONSENT_PAYLOAD__' );

} catch ( Throwable $linker_error ) {
	WP_CLI::error( $linker_error->getMessage() . ' at ' . $linker_error->getLine() );
}
