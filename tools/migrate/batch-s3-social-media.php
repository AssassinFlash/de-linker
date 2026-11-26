<?php
/**
 * Register S3 preview artwork and set the SEOPress social options.
 * WP-CLI: eval-file <file> snapshot | apply | restore <snapshot.json>.
 *
 * @package Linker\Migrate
 */

( static function ( array $args ): void {
	if ( ! defined( 'WP_CLI' ) || ! WP_CLI ) {
		return;
	}
	$mode    = $args[0] ?? 'apply';
	$uploads = wp_get_upload_dir();
	$folder  = 'linker-social';
	$assets  = WP_PLUGIN_DIR . '/linker-commerce/assets/social/';
	$social  = (array) get_option( 'seopress_social_option_name', array() );
	$values  = array(
		'seopress_social_facebook_img'               => '',
		'seopress_social_facebook_img_attachment_id' => 0,
		'seopress_social_facebook_img_width'         => 1200,
		'seopress_social_facebook_img_height'        => 630,
		'seopress_social_facebook_img_default'       => '1',
		'seopress_social_twitter_card'               => '1',
		'seopress_social_twitter_card_og'            => '1',
		'seopress_social_twitter_card_img_size'      => 'large',
		'seopress_social_twitter_card_img'           => '',
		'seopress_social_accounts_facebook'          => '',
		'seopress_social_accounts_youtube'           => '',
		'seopress_social_accounts_twitter'           => '@chester_linker',
		'seopress_social_accounts_linkedin'          => '',
	);
	$state   = array(
		'site'   => get_option( 'home' ),
		'social' => array_intersect_key( $social, $values ),
		'images' => array(),
	);
	$before  = null;
	if ( 'restore' === $mode ) {
		// phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- Local WP-CLI recovery file.
		$json = empty( $args[1] ) ? false : file_get_contents( $args[1] );
		if ( false === $json ) {
			WP_CLI::error( 'Pass the snapshot file captured before apply.' );
		}
		$before = json_decode( $json, true, 512, JSON_THROW_ON_ERROR );
		if ( $state['site'] !== $before['site'] ) {
			WP_CLI::error( 'The snapshot belongs to a different site.' );
		}
	} elseif ( ! in_array( $mode, array( 'snapshot', 'apply' ), true ) ) {
		WP_CLI::error( 'Use snapshot, apply or restore.' );
	}

	foreach ( array( 'default', 'blog' ) as $kind ) {
		$file                     = 'og-linker-' . $kind . '-1200x630.jpg';
		$path                     = $uploads['basedir'] . '/' . $folder . '/' . $file;
		$url                      = $uploads['baseurl'] . '/' . $folder . '/' . $file;
		$key                      = 'linker_social_' . $kind . '_og_attachment_id';
		$id                       = attachment_url_to_postid( $url );
		$state['images'][ $kind ] = array(
			'id'     => $id,
			'option' => get_option( $key, null ),
			'file'   => is_file( $path ),
			'alt'    => $id ? get_post_meta( $id, '_wp_attachment_image_alt', false ) : array(),
		);
		if ( 'snapshot' === $mode ) {
			continue;
		}
		if ( 'restore' === $mode ) {
			$old = $before['images'][ $kind ];
			if ( ! $old['id'] && $id ) {
				wp_delete_attachment( $id, true );
			} elseif ( $old['id'] && $id === $old['id'] ) {
				if ( $old['alt'] ) {
					update_post_meta( $id, '_wp_attachment_image_alt', $old['alt'][0] );
				} else {
					delete_post_meta( $id, '_wp_attachment_image_alt' );
				}
			} elseif ( $old['id'] ) {
				WP_CLI::error( "Attachment changed for $file." );
			}
			if ( $old['file'] && ! is_file( $path ) && ! copy( $assets . $file, $path ) ) {
				WP_CLI::error( "Cannot restore $file." );
			}
			if ( ! $old['file'] && is_file( $path ) ) {
				wp_delete_file( $path );
			}
			if ( null === $old['option'] ) {
				delete_option( $key );
			} else {
				update_option( $key, $old['option'] );
			}
			continue;
		}

		require_once ABSPATH . 'wp-admin/includes/image.php';
		if ( ! wp_mkdir_p( dirname( $path ) ) || ( ! is_file( $path ) && ! copy( $assets . $file, $path ) ) ) {
			WP_CLI::error( "Cannot install $file." );
		}
		if ( ! $id ) {
			$id = wp_insert_attachment(
				array(
					'post_mime_type' => 'image/jpeg',
					'post_title'     => 'blog' === $kind ? 'Linker Journal' : 'Linker Technology GmbH',
					'guid'           => $url,
				),
				$path,
				0,
				true
			);
			if ( is_wp_error( $id ) ) {
				WP_CLI::error( $id->get_error_message() );
			}
		}
		$metadata = wp_get_attachment_metadata( $id );
		if ( ! $metadata ) {
			$metadata = wp_generate_attachment_metadata( $id, $path );
			wp_update_attachment_metadata( $id, $metadata );
		}
		if ( 1200 !== (int) ( $metadata['width'] ?? 0 ) || 630 !== (int) ( $metadata['height'] ?? 0 ) || wp_get_attachment_url( $id ) !== $url ) {
			WP_CLI::error( "Unexpected registered artwork for $file." );
		}
		update_post_meta( $id, '_wp_attachment_image_alt', \Linker\Commerce\Storefront\SocialCards::ARTWORK[ $kind ] );
		update_option( $key, $id );
		$state['images'][ $kind ] = array(
			'id'  => $id,
			'url' => $url,
		);
		if ( 'default' === $kind ) {
			$values['seopress_social_facebook_img']               = $url;
			$values['seopress_social_facebook_img_attachment_id'] = $id;
			$values['seopress_social_twitter_card_img']           = $url;
		}
	}
	if ( 'apply' === $mode ) {
		$values['seopress_social_accounts_facebook'] = \Linker\Commerce\Presentation\ContactChannels::OFFICIAL_FACEBOOK;
		$values['seopress_social_accounts_youtube']  = \Linker\Commerce\Presentation\ContactChannels::OFFICIAL_YOUTUBE;
		update_option( 'seopress_social_option_name', array_replace( $social, $values ) );
		$state['social'] = $values;
	} elseif ( 'restore' === $mode ) {
		update_option( 'seopress_social_option_name', array_replace( array_diff_key( $social, $values ), $before['social'] ) );
		$state = $before;
	}
	echo wp_json_encode( $state, JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT ) . "\n";
} )( $args ?? array() );
