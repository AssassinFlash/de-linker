<?php
/** Explicit LOCAL synthetic CUA fixture. Never deployed. No real mail/model calls. */
add_filter('pre_http_request', static function($pre,$args,$url) {
 if (false !== $pre || 'local' !== wp_get_environment_type() || 'http://127.0.0.1:9285' !== untrailingslashit(home_url()) || ! defined('LINKER_TURNSTILE_SECRET_KEY') || LINKER_TURNSTILE_SECRET_KEY !== '1x0000000000000000000000000000000AA') return $pre;
 $mode=trim(file_get_contents('/tmp/de-linker-521-network-mode.txt'));
 if ('https://challenges.cloudflare.com/turnstile/v0/siteverify' === $url && ($args['body']['secret']??'')==='1x0000000000000000000000000000000AA') {
   if ('outage'===$mode) return new WP_Error('fixture_outage','Synthetic local verification outage');
   $input=json_decode(file_get_contents('php://input'),true);
   return array('response'=>array('code'=>200),'body'=>wp_json_encode(array('success'=>true,'hostname'=>'dummy-key-pass','action'=>$input['action']??'')));
 }
 if (str_starts_with($url,'http://127.0.0.1:') && str_ends_with($url,'/assistant/turn')) {
   if ('quota'===$mode) return array('response'=>array('code'=>429),'body'=>wp_json_encode(array('code'=>'provider_budget_quota')));
   $stream="event: meta\ndata: {\"turn_id\":521,\"grounded\":true,\"language\":\"en\"}\n\nevent: block\ndata: {\"type\":\"text\",\"text\":\"Synthetic local acceptance reply.\",\"refs\":[]}\n\nevent: done\ndata: {}\n\n";
   return array('response'=>array('code'=>200),'body'=>$stream);
 }
 if ('engine_quota' === $mode && str_starts_with($url, 'http://127.0.0.1:9286/design/')) return array('response'=>array('code'=>429),'body'=>'{"detail":"Synthetic private engine concurrency refusal"}');
 return $pre;
},PHP_INT_MAX-1,3);
