<?php
/** Local screenshot instrumentation. Never deployed; remove after capture. */
if ( ! defined( 'ABSPATH' ) || wp_get_environment_type() !== 'local' ) {
    return;
}
add_action( 'wp_head', static function () {
    echo '<style>*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}</style>';
    echo '<script>window.setInterval=()=>0;document.addEventListener("DOMContentLoaded",()=>{document.querySelectorAll("img").forEach(i=>i.loading="eager");document.querySelectorAll("video").forEach(v=>{v.pause();v.currentTime=0;v.addEventListener("play",()=>v.pause());});});</script>';
}, 999 );
