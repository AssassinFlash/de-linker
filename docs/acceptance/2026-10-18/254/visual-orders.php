<?php
/** Owned screenshot data. Run only through wp-c254.sh; never deployed. */
if ( wp_get_environment_type() !== 'local' || (int) wp_parse_url( (string) get_option( 'home' ), PHP_URL_PORT ) !== 9129 ) {
    throw new RuntimeException( 'Only the c254 local instance is allowed.' );
}
$user=get_user_by('login','i254-visual');
if (!$user || !get_user_meta($user->ID,'_linker_254_visual_fixture',true)) { throw new RuntimeException('Owned visual customer missing'); }
$products=get_posts(["post_type"=>"product","post_status"=>"publish","lang"=>"en","post_name__in"=>["saj-b2-10-0-hv1"],"numberposts"=>2]); if(count($products)!==1){throw new RuntimeException("Visual model missing");}
$proof=[];
foreach (['en_US','de_DE_formal'] as $locale) {
 $order=new WC_Order(); $order->set_customer_id($user->ID); $order->set_billing_first_name('Jan'); $order->set_billing_last_name('Muster'); $order->set_billing_email('i254-visual@example.test'); $order->set_billing_company('Beispielbetrieb GmbH'); $order->set_payment_method('linker_proforma'); $order->set_status('inquiry-received'); $order->update_meta_data('_linker_locale',$locale); $order->update_meta_data('_linker_254_visual_fixture',true); $order->add_product(wc_get_product($products[0]->ID),1); $order->calculate_totals(); $order->save();
 $lang=new Linker\I18n\Languages();$scope=$lang->enter(str_starts_with($locale,'de')?'de':'en');try {$url=$order->get_checkout_order_received_url();}finally{$lang->leave($scope);}
 $proof[]=['id'=>$order->get_id(),'locale'=>$locale,'url'=>$url];
}
echo wp_json_encode($proof,JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES),"\n";
