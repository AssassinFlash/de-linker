<?php

if (!defined('ABSPATH')) {
    exit;
}

$candidates = array();
if (defined('WPMU_PLUGIN_DIR')) {
    $candidates = array(
        WPMU_PLUGIN_DIR . '/../plugins/linker-i18n/includes/class-linker-i18n-lang.php',
        WPMU_PLUGIN_DIR . '/../plugins/linker-i18n/linker-i18n/includes/class-linker-i18n-lang.php',
    );
}

foreach ($candidates as $candidate) {
    if (file_exists($candidate)) {
        require_once $candidate;
        break;
    }
}

if (class_exists('Linker_I18n_Lang')) {
    // Read GET and POST independently. $_REQUEST is intentionally forbidden here
    // because its contents/order can include cookies and vary by PHP configuration.
    $query = isset($_GET) && is_array($_GET) ? $_GET : array();
    $body = isset($_POST) && is_array($_POST) ? $_POST : array();

    // REST JSON bodies are not populated into $_POST. Reading php://input is
    // non-destructive on supported PHP versions and lets the early contract detect
    // a header/body mismatch before an endpoint executes.
    $content_type = isset($_SERVER['CONTENT_TYPE']) ? (string) $_SERVER['CONTENT_TYPE'] : '';
    if (stripos($content_type, 'application/json') !== false) {
        $raw_body = file_get_contents('php://input');
        if (is_string($raw_body) && $raw_body !== '') {
            $decoded = json_decode($raw_body, true);
            if (is_array($decoded)) {
                $body = array_merge($body, $decoded);
            }
        }
    }

    $resolution = Linker_I18n_Lang::apply_request(
        isset($_SERVER) && is_array($_SERVER) ? $_SERVER : array(),
        $query,
        $body
    );

    // The normal plugin entrypoint uses this state to reject ambiguous endpoint
    // requests. Keeping the full resolution also makes early-load diagnostics
    // possible without re-inferring locale from later ambient state.
    $GLOBALS['linker_i18n_locale_resolution'] = $resolution;
}
