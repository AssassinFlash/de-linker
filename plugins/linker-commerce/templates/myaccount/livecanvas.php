<?php
/**
 * Woo's authorised account arguments pass to LiveCanvas, without PHP layout.
 *
 * @package Linker\Commerce
 * @var array{template_name: string, args: array<string, mixed>} $action_args Woo include context.
 */

defined( 'ABSPATH' ) || exit;

Linker\Commerce\Presentation\AccountTemplates::output( $action_args );
