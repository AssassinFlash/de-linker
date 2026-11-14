<?php
/**
 * Copy the listed page bodies to a directory before a rewrite.
 *
 * Run: wp eval-file backup-pages.php <dir> <id>[,<id>...]
 *
 * @package Linker\Commerce
 */

$dir = $args[0] ?? '/tmp/linker-backup';
$ids = array_map( 'intval', explode( ',', $args[1] ?? '' ) );
if ( ! wp_mkdir_p( $dir ) ) {
	echo "cannot create {$dir}\n";
	exit( 1 );
}
foreach ( $ids as $id ) {
	if ( $id <= 0 ) {
		continue;
	}
	$content = get_post_field( 'post_content', $id );
	file_put_contents( $dir . '/' . $id . '.html', $content );
	printf( "%d %s %d %s\n", $id, get_post_field( 'post_name', $id ), strlen( $content ), md5( $content ) );
}
