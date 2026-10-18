<?php
/** Local screenshot instrumentation. Never deployed; remove after capture. */
if ( ! defined( 'ABSPATH' ) || wp_get_environment_type() !== 'local' ) {
    return;
}
add_action( 'wp_head', static function () {
    echo '<style>html,body{scroll-behavior:auto!important}*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}</style>';
    echo '<script>window.setInterval=()=>0;window.addEventListener("load",async()=>{await document.fonts.ready;await Promise.all([...document.images].filter(i=>i.getAttribute("src")).map(i=>i.decode().catch(()=>null)));requestAnimationFrame(()=>requestAnimationFrame(()=>document.documentElement.dataset.i254ImagesReady="ready"));},{once:true});document.addEventListener("DOMContentLoaded",()=>{document.querySelectorAll("img").forEach(i=>i.loading="eager");document.querySelectorAll("video").forEach(v=>{v.removeAttribute("autoplay");v.removeAttribute("loop");v.preload="auto";v.addEventListener("play",()=>v.pause());v.addEventListener("loadeddata",()=>{v.pause();v.currentTime=0;},{once:true});v.pause();v.load();});});</script>';
}, 999 );
// Only the owned screenshot session opts into this seeded error state. The
// form consumes/clears it through its normal flash path; submission behavior is
// exercised separately by OpenInquiryTest. No email or inquiry is created here.
add_action( 'template_redirect', static function () {
    if ( ( $_GET['i254-visual-state'] ?? '' ) !== 'error' || ! function_exists( 'WC' ) || ! WC()->session ) {
        return;
    }
    WC()->session->set( 'linker_inquiry_error', __( 'Please check your entries and send the form again.', 'linker-commerce' ) );
    WC()->session->set( 'linker_inquiry_error_locale', get_locale() );
    WC()->session->set( 'linker_inquiry_fields', array( 'name' => 'Jan Muster', 'email' => 'i254-visual@example.test', 'company' => 'Beispielbetrieb GmbH', 'message' => '' ) );
}, 5 );
